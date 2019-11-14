import os
import time
import datetime
import math
import csv
import shutil

from queue import Queue
from threading import Thread

import meshlabxml as mlx
import trimesh

trimesh.util.attach_to_log()

import tiler.config as config
from tiler.utils import timeit, check_call


class Worker(Thread):
    """ Thread executing tasks from a given tasks queue """

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception as e:
                # An exception happened in this thread
                print(e)
            finally:
                # Mark this task as done, whether an exception happened or not
                self.tasks.task_done()


class ThreadPool:
    """ Pool of threads consuming tasks from a queue """

    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        """ Add a task to the queue """
        self.tasks.put((func, args, kargs))

    def map(self, func, args_list):
        """ Add a list of tasks to the queue """
        for args in args_list:
            self.add_task(func, args)

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue """
        self.tasks.join()


@timeit
def run_tiler():
    pool = ThreadPool(config.NUM_THREADS)

    input_path = os.path.join(config.DATA_PATH, 'in', 'model')
    input_file_path = os.path.join(input_path, 'better_model.obj')
    model_name = os.path.basename(input_file_path).split('.')[0]
    output_path = os.path.join(config.DATA_PATH, 'out', model_name)
    os.makedirs(output_path, exist_ok=True)

    # get world bounds and extents
    world_file_path = input_file_path
    world = trimesh.load(world_file_path)
    world_size = max(world.extents)

    # so unsure if this does anything, but i'm paranoid about precision becoming a problem if we don't do this
    def move_to_origin(target_script):
        min_bounds = world.bounds[0]
        min_x = min_bounds[0]
        min_y = min_bounds[1]
        min_z = min_bounds[2]
        mlx.transform.translate(target_script, value=(-min_x, -min_y, -min_z))

    def clean_mesh(target_script):

        # remove nonmanifold edges and verts
        mlx.select.nonmanifold_edge(target_script)
        mlx.delete.selected(target_script, face=True, vert=False)
        mlx.select.nonmanifold_vert(target_script)
        mlx.delete.selected(target_script, face=False, vert=True)

        # dupe faces and verts
        mlx.delete.duplicate_faces(target_script)
        # mlx.delete.duplicate_verts(target_script)

        # unreferenced verts
        mlx.delete.unreferenced_vert(target_script)

        # close holes
        mlx.clean.close_holes(target_script, hole_max_edge=10000)

        # fix normals
        mlx.normals.reorient(target_script)

    # this function is useful for final cropping
    def selection_crop_to_mesh_bounds(target_script, mesh=world):
        buffer = config.TILE_CROPPING_BUFFER if mesh != world else 0
        min_bounds = mesh.bounds[0]
        max_bounds = mesh.bounds[1]
        min_x = min_bounds[0] - buffer
        max_x = max_bounds[0] + buffer
        min_y = min_bounds[1] - buffer
        max_y = max_bounds[1] + buffer
        min_z = min_bounds[2] - buffer
        max_z = max_bounds[2] + buffer
        sel_func = f'(x < {min_x}) || (x > {max_x}) || (y < {min_y}) || (y > {max_y}) || (z < {min_z}) || (z > {max_z})'
        mlx.select.vert_function(target_script, function=sel_func)
        mlx.delete.selected(target_script, face=False, vert=True)
        mlx.select.none(target_script)




    # copy over textures
    def copy_textures():
        os.chdir(input_path)
        texture_files, texture_files_unique, material_file = mlx.find_texture_files(
            input_file_path)
        for texture_file in texture_files_unique:
            src = os.path.join(input_path, texture_file)
            dst = os.path.join(output_path, texture_file)

            # skip if cached
            if config.USE_CACHED_FILES and os.path.exists(dst):
                continue

            shutil.copy(src, dst)

    pool.add_task(copy_textures)

    # full simplification mesh... nice for debugging and whatnot
    debug_simple_mesh_file_path = os.path.join(
        output_path, 'simple_full_mesh.obj')

    def create_debug_simple_mesh():

        # skip if cached
        if config.USE_CACHED_FILES and os.path.exists(debug_simple_mesh_file_path):

            # replace world with this new mesh (comment this out for prod)
            world_file_path = debug_simple_mesh_file_path
            world = trimesh.load(world_file_path)
            world_size = max(world.extents)
            return

        debug_simple_mesh_script = mlx.FilterScript(
            file_in=input_file_path, file_out=debug_simple_mesh_file_path)

        # clean / simplify mesh
        clean_mesh(debug_simple_mesh_script)
        mlx.remesh.simplify(debug_simple_mesh_script, texture=True, target_perc=0.5,
                            quality_thr=config.SIMPLIFICATION_MESH_QUALITY, preserve_boundary=True, boundary_weight=config.SIMPLIFICATION_EDGE_WEIGHT,
                            optimal_placement=True, preserve_normal=False,
                            planar_quadric=True, selected=False, extra_tex_coord_weight=config.SIMPLIFICATION_TEXTURE_WEIGHT,
                            preserve_topology=True, quality_weight=False, autoclean=True)
        selection_crop_to_mesh_bounds(debug_simple_mesh_script)
        clean_mesh(debug_simple_mesh_script)

        debug_simple_mesh_script.run_script()

        # replace world with this new mesh (comment this out for prod)
        world_file_path = debug_simple_mesh_file_path
        world = trimesh.load(world_file_path)
        world_size = max(world.extents)

    pool.add_task(create_debug_simple_mesh)

    # block until initial simplification is done
    pool.wait_completion()

    # for each layer
    layers = []
    for layer_index in range(config.NUM_LAYERS):

        # calculate quality
        k = math.log(config.SIMPLIFICATION_MAX /
                     config.SIMPLIFICATION_MIN) / config.NUM_LAYERS
        percentage = config.SIMPLIFICATION_MIN * \
            math.exp(k * (layer_index + 1))
        layer_file_path = os.path.join(
            output_path, f'layer_{layer_index}.obj')

        def create_layer(layer_file_path, percentage):

            # skip if cached
            if config.USE_CACHED_FILES and os.path.exists(layer_file_path):
                return

            layer_mesh_script = mlx.FilterScript(
                file_in=world_file_path, file_out=layer_file_path)

            # clean / simplify mesh
            clean_mesh(layer_mesh_script)
            mlx.remesh.simplify(layer_mesh_script, texture=True, target_perc=percentage,
                                quality_thr=config.SIMPLIFICATION_MESH_QUALITY, preserve_boundary=True, boundary_weight=config.SIMPLIFICATION_EDGE_WEIGHT,
                                optimal_placement=True, preserve_normal=False,
                                planar_quadric=True, selected=False, extra_tex_coord_weight=config.SIMPLIFICATION_TEXTURE_WEIGHT,
                                preserve_topology=True, quality_weight=False, autoclean=True)
            selection_crop_to_mesh_bounds(layer_mesh_script)
            clean_mesh(layer_mesh_script)

            layer_mesh_script.run_script()

            layer_gltf_file_path = layer_file_path.replace('.obj', '.gltf')
            check_call([config.OBJ2GLTF_PATH, '-i',
                        tile_file_path, '-o', layer_gltf_file_path], cwd=output_path)

        layers.append((layer_file_path, layer_index))
        pool.add_task(create_layer, layer_file_path, percentage)

    # block until layers are generated
    pool.wait_completion()

    for layer_file_path, layer_index in layers:

        # voxelize the world at that quality
        voxel_pitch = world_size / 2
        for _ in range(layer_index):
            voxel_pitch = voxel_pitch / 2
        world_voxels = world.voxelized(voxel_pitch)
        voxel_origin = world_voxels.origin

        def create_tile(tile_file_path, tile_mesh):

            # build the tile in meshlab
            tile_mesh_script = mlx.FilterScript(
                file_in=layer_file_path, file_out=tile_file_path)
            selection_crop_to_mesh_bounds(tile_mesh_script, mesh=tile_mesh)
            # mlx.remesh.simplify(tile_mesh_script, texture=True, target_perc=percentage,
            #                     quality_thr=config.SIMPLIFICATION_MESH_QUALITY, preserve_boundary=True, boundary_weight=config.SIMPLIFICATION_EDGE_WEIGHT,
            #                     optimal_placement=True, preserve_normal=True,
            #                     planar_quadric=True, selected=False, extra_tex_coord_weight=config.SIMPLIFICATION_TEXTURE_WEIGHT,
            #                     preserve_topology=True, quality_weight=False, autoclean=True)

            # sanity check
            selection_crop_to_mesh_bounds(tile_mesh_script)

            tile_mesh_script.run_script()

            # convert to gltf
            # gltf_raw_file_path = tile_file_path.replace('.obj', '_unprocessed.gltf')
            gltf_final_file_path = tile_file_path.replace('.obj', '.gltf')
            check_call([config.OBJ2GLTF_PATH, '-i',
                        tile_file_path, '-o', gltf_final_file_path], cwd=output_path)
            # check_call([config.GLTF_OPTIMIZE_PATH, '-i',
            # gltf_raw_file_path, '-o', gltf_final_file_path, '--binary', '--removeNormals', '--smoothNormals', '--cesium'], cwd=output_path)

            # cleanup residual files
            os.unlink(tile_file_path)
            os.unlink(tile_file_path + '.mtl')
            # os.unlink(gltf_raw_file_path)

        # for each voxel
        for tile_coords in world_voxels.sparse_surface:

            # this is the most ass-backwards way of coming up with the single tile mesh...
            dense_bool_matrix = trimesh.voxel.sparse_to_matrix([tile_coords])
            coords_matrix = trimesh.voxel.matrix_to_points(
                dense_bool_matrix, voxel_pitch, voxel_origin)
            tile_mesh = trimesh.voxel.multibox(
                coords_matrix, voxel_pitch)

            (x, y, z) = tile_coords
            tile_file_path = os.path.join(
                output_path, f'tile_{layer_index}_{x}_{y}_{z}.obj')

            pool.add_task(create_tile, tile_file_path, tile_mesh)

    # wait for all tiles to be generated
    pool.wait_completion()

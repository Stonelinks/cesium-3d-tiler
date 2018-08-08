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
from tiler.utils import timeit


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
    world = trimesh.load(input_file_path)

    world_size = max(world.extents)

    # this function is useful for final cropping
    def crop_to_mesh_extents(target_script, mesh=world):
        min_bounds = mesh.bounds[0]
        max_bounds = mesh.bounds[1]
        min_x = min_bounds[0]
        max_x = max_bounds[0]
        min_y = min_bounds[1]
        max_y = max_bounds[1]
        min_z = min_bounds[2]
        max_z = max_bounds[2]
        sel_func = f'(x < {min_x}) || (x > {max_x}) || (y < {min_y}) || (y > {max_y}) || (z < {min_z}) || (z > {max_z})'
        mlx.select.vert_function(target_script, function=sel_func)
        mlx.delete.selected(target_script, face=False, vert=True)

    # copy over textures
    def copy_textures():
        os.chdir(input_path)
        texture_files, texture_files_unique, material_file = mlx.find_texture_files(
            input_file_path)
        for texture_file in texture_files_unique:
            src = os.path.join(input_path, texture_file)
            dst = os.path.join(output_path, texture_file)
            shutil.copy(src, dst)
    pool.add_task(copy_textures)

    # full simplification mesh... nice for debugging and whatnot
    debug_simple_mesh_file_path = os.path.join(
        output_path, 'simple_full_mesh.obj')

    def create_debug_simple_mesh():
        debug_simple_mesh_script = mlx.FilterScript(
            file_in=input_file_path, file_out=debug_simple_mesh_file_path)
        mlx.remesh.simplify(debug_simple_mesh_script, texture=True, target_perc=0.5,
                            quality_thr=config.SIMPLIFICATION_MESH_QUALITY, preserve_boundary=True, boundary_weight=config.SIMPLIFICATION_EDGE_WEIGHT,
                            optimal_placement=True, preserve_normal=False,
                            planar_quadric=True, selected=False, extra_tex_coord_weight=config.SIMPLIFICATION_TEXTURE_WEIGHT,
                            preserve_topology=True, quality_weight=False, autoclean=True)
        crop_to_mesh_extents(debug_simple_mesh_script)
        debug_simple_mesh_script.run_script()
    # pool.add_task(create_debug_simple_mesh)

    # block until initial simplification is done
    pool.wait_completion()

    # whole layers, where tiles get cropped from
    layers = []

    def create_full_layer_mesh(layer_index):
        k = math.log(config.SIMPLIFICATION_MAX /
                     config.SIMPLIFICATION_MIN) / config.NUM_LAYERS
        percentage = config.SIMPLIFICATION_MIN * \
            math.exp(k * (layer_index + 1))

        layer_mesh_file_path = os.path.join(
            output_path, f'layer_full_{layer_index}.obj')
        # layer_mesh_script = mlx.FilterScript(
        #     file_in=debug_simple_mesh_file_path, file_out=layer_mesh_file_path)
        # mlx.remesh.simplify(layer_mesh_script, texture=True, target_perc=percentage,
        #                     quality_thr=config.SIMPLIFICATION_MESH_QUALITY, preserve_boundary=True, boundary_weight=config.SIMPLIFICATION_EDGE_WEIGHT,
        #                     optimal_placement=True, preserve_normal=False,
        #                     planar_quadric=True, selected=False, extra_tex_coord_weight=config.SIMPLIFICATION_TEXTURE_WEIGHT,
        #                     preserve_topology=True, quality_weight=False, autoclean=True)
        # crop_to_mesh_extents(layer_mesh_script)
        # layer_mesh_script.run_script()

        layers.append((layer_index, layer_mesh_file_path))

    for layer_index in range(config.NUM_LAYERS):
        pool.add_task(create_full_layer_mesh, layer_index)
    pool.wait_completion()

    for (layer_index, layer_mesh_file_path) in layers:
        layer_mesh = trimesh.load(layer_mesh_file_path)
        voxel_pitch = world_size / 2
        for _ in range(layer_index):
            voxel_pitch = voxel_pitch / 2
        layer_mesh_voxels = layer_mesh.voxelized(voxel_pitch)
        voxel_origin = layer_mesh_voxels.origin

        def create_tile(tile_file_path, tile_mesh):
            tile_mesh_script = mlx.FilterScript(
                file_in=layer_mesh_file_path, file_out=tile_file_path)
            crop_to_mesh_extents(tile_mesh_script, mesh=tile_mesh)
            tile_mesh_script.run_script()

        for tile_coords in layer_mesh_voxels.sparse_surface:

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

    pool.wait_completion()

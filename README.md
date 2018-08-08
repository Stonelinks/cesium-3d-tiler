# cesium-3d-tiler
experimental map tiler to convert large meshes into cesium 3d tilesets

## setup

make sure you have meshlab installed. OSX freaks out if you don't do this:

```
MESHLAB_PATH=/Applications/meshlab.app/Contents/MacOS/
cd $MESHLAB_PATH
install_name_tool -add_rpath "@executable_path/../Frameworks" meshlabserver
```

```
python3 -m venv venv
. devenv.sh
pip install -r requirements.txt
cd viewer-app/ && npm i
```


## development

generate tiles
```
python -m tiler
```

frontend
```
cd viewer-app/ && npm start
```

## license
MIT

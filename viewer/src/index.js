import React from "react";
import { render } from "react-dom";
import registerServiceWorker from "./registerServiceWorker";

import Cesium from "cesium/Cesium";

const styles = {
  rendererRoot: {}
};

// function createModel(url, height) {
//   viewer.entities.removeAll();

//   var position = Cesium.Cartesian3.fromDegrees(
//     -123.0744619,
//     44.0503706,
//     height
//   );
//   var heading = Cesium.Math.toRadians(135);
//   var pitch = 0;
//   var roll = 0;
//   var hpr = new Cesium.HeadingPitchRoll(heading, pitch, roll);
//   var orientation = Cesium.Transforms.headingPitchRollQuaternion(position, hpr);

//   var entity = viewer.entities.add({
//     name: url,
//     position: position,
//     orientation: orientation,
//     model: {
//       uri: url,
//       minimumPixelSize: 128,
//       maximumScale: 20000
//     }
//   });
//   viewer.trackedEntity = entity;
// }

// var options = [
//   {
//     text: "Aircraft",
//     onselect: function() {
//       createModel(
//         "../../../../Apps/SampleData/models/CesiumAir/Cesium_Air.glb",
//         5000.0
//       );
//     }
//   },
//   {
//     text: "Ground Vehicle",
//     onselect: function() {
//       createModel(
//         "../../../../Apps/SampleData/models/GroundVehicle/GroundVehicle.glb",
//         0
//       );
//     }
//   },
//   {
//     text: "Hot Air Balloon",
//     onselect: function() {
//       createModel(
//         "../../../../Apps/SampleData/models/CesiumBalloon/CesiumBalloon.glb",
//         1000.0
//       );
//     }
//   },
//   {
//     text: "Milk Truck",
//     onselect: function() {
//       createModel(
//         "../../../../Apps/SampleData/models/CesiumMilkTruck/CesiumMilkTruck-kmc.glb",
//         0
//       );
//     }
//   },
//   {
//     text: "Skinned Character",
//     onselect: function() {
//       createModel(
//         "../../../../Apps/SampleData/models/CesiumMan/Cesium_Man.glb",
//         0
//       );
//     }
//   },
//   {
//     text: "Draco Compressed Model",
//     onselect: function() {
//       createModel(
//         "../../../../Apps/SampleData/models/DracoCompressed/CesiumMilkTruck.gltf",
//         0
//       );
//     }
//   }
// ];

export class App extends React.Component {
  constructor(props) {
    super(props);

    this.setupRenderer = this.setupRenderer.bind(this);
  }

  componentDidMount() {}

  componentWillUnmount() {}

  shouldComponentUpdate() {
    return false;
  }

  setupRenderer(ref) {
    this.renderer = new Cesium.Viewer(ref, {
      infoBox: false,
      selectionIndicator: false,
      shadows: true,
      shouldAnimate: true
    });
  }

  render() {
    return <div style={styles.rendererRoot} ref={this.onRendererRef} />;
  }
}

render(<App />, document.getElementById("root"));

registerServiceWorker();

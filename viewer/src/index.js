import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import registerServiceWorker from './registerServiceWorker';

import { Cartesian3 } from "cesium";

import { Viewer, Entity } from "cesium-react";

class App extends Component {
  render() {
    return (
      <Viewer full />
    );
  }
}

ReactDOM.render(<App />, document.getElementById('root'));
registerServiceWorker();

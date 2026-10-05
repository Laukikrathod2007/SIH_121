import React from 'react';
import { SpatialVisualization } from '../components/SpatialVisualizationHost';
import { nwisLiveProvider } from '../../../nwis-spatial-visualization/src/nwisLiveProvider';

/** Host the spatial package in the main app with its NWIS Module 02 adapter. */
export const SpatialVisualizationPage: React.FC = () => (
  <SpatialVisualization provider={nwisLiveProvider} />
);

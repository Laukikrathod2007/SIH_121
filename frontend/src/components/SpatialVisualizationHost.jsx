// Keep the visualization package as an independent React source module. Its
// own TypeScript project pins newer Three.js type definitions than this app.
// Vite bundles both against the shared React runtime (see resolve.dedupe).
import { SpatialVisualization as Visualization } from '../../../nwis-spatial-visualization/src';

export const SpatialVisualization = Visualization;

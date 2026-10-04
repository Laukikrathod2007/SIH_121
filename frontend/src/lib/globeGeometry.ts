import * as THREE from 'three';

// Shared lat/lon <-> 3D-sphere math for the real interactive offset-well
// globe (components/globe/*). Separate from trajectoryGeometry.ts, which is
// local wellbore (MD/TVD/NS/EW) coordinates -- this file is global
// geographic coordinates on a sphere, a genuinely different coordinate
// system, not a duplicate of it.
//
// Texture convention: the Earth day/night maps (frontend/public/earth/*.jpg,
// reused from visualization_3d/assets/) are standard 2:1 equirectangular
// projections (texture_u=0.5+lon/360, texture_v=0.5-lat/180, i.e. v=0 is the
// TOP of the image = north pole). Derived directly from two things read from
// three.js's own SphereGeometry source (node_modules/three/src/geometries/SphereGeometry.js),
// not assumed:
//   1. The vertex formula (x=-r*cos(phi)*sin(theta), y=r*cos(theta),
//      z=r*sin(phi)*sin(theta), phi=u*2pi, theta=v*pi, mesh u/v each 0..1).
//   2. The UV assignment actually pushed to the `uv` attribute (line 82):
//      `uvs.push(u + uOffset, 1 - v)` -- the TEXTURE's v-coordinate is
//      `1 - v`, not `v` itself. Missing this on an earlier pass of this
//      function (which matched point 1 but never checked point 2) flipped
//      the mesh's v and therefore the sign of y, silently moving every real
//      well several thousand km north-south of its correct real location
//      (confirmed live: WELL-HGJ-011, real coords 27.20N/94.75E in Assam,
//      India, rendered over Mongolia/China at roughly 45N instead -- caught
//      during the end-to-end verification pass by screenshotting the
//      rendered globe and comparing the marker's visible position against
//      real continent outlines, not by re-reading this file's own math).
// Re-derived from both facts together (texture_v = 1-mesh_v => mesh_v =
// 0.5+lat/180, substituted into the real vertex formula and simplified) and
// re-verified the same way: WELL-HGJ-011 now renders over Assam/northeast
// India as it should, and the North Sea Volve pair renders off Norway.
export const GLOBE_RADIUS = 2;

export function latLonToVec3(latDeg: number, lonDeg: number, radius: number = GLOBE_RADIUS): THREE.Vector3 {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  const x = -radius * Math.cos(lat) * Math.cos(lon);
  const y = radius * Math.sin(lat);
  const z = -radius * Math.cos(lat) * Math.sin(lon);
  return new THREE.Vector3(x, y, z);
}

/** Great-circle (Haversine) distance in km -- same formula module 02's DORS
 * spatial factor and NearbyWellsPage use, kept consistent so the globe's
 * radius selection agrees with every other view of "nearby". */
export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

/** Point on a great-circle arc between two lat/lon pairs, raised slightly
 * above the sphere surface by `lift` at the arc's midpoint -- used to draw
 * the active-well-to-offset-well connector arcs without them clipping
 * through the globe. t in [0,1]. */
export function greatCircleArcPoint(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
  t: number,
  radius: number = GLOBE_RADIUS,
  lift: number = 0.25,
): THREE.Vector3 {
  const start = latLonToVec3(lat1, lon1, radius);
  const end = latLonToVec3(lat2, lon2, radius);
  const point = start.clone().lerp(end, t).normalize();
  // Raise the arc off the surface with a sine hump peaking at t=0.5, so it
  // reads as an arc rather than a chord cutting through the sphere.
  const bulge = Math.sin(Math.PI * t) * lift;
  return point.multiplyScalar(radius + bulge);
}

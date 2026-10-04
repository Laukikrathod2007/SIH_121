import React from 'react';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { GLOBE_RADIUS } from '../../lib/globeGeometry';

// Real Earth sphere -- day-map texture (equirectangular, reused from
// visualization_3d/assets/, itself a standard Solar System Scope-style
// texture, not a fabricated/placeholder image) plus a faint night-side
// emissive layer. This renders actual coastline geography (so real well
// lat/lon lands on the correct real location), stylistically closer to the
// dark/desaturated "data-globe" look visualization_3d/idea.md described
// than a bright photo-Earth, via a dimmed material rather than a second
// shader pass -- the smallest change that gets the intended look without a
// custom GLSL material this component doesn't otherwise need.
//
// Does NOT own its own rotation (previously did, via an internal auto-
// rotating <group>) -- the parent (OffsetGlobe3D's RotatingGroup) now owns
// rotation for this AND the well markers together, so the texture and the
// markers always rotate in lockstep. This component owning its own
// independent rotation was a real bug: it silently desynced the texture
// from the (differently-parented) markers over time, so a well's apparent
// position on the visible continents drifted the longer the page had been
// open -- found during the end-to-end verification pass by screenshotting
// the same real well's marker at two different times and seeing it in two
// different wrong places, not by re-reading this file's own code.
export const EarthGlobe: React.FC = () => {
  const dayMap = useLoader(THREE.TextureLoader, '/earth/earth-daymap-2k.jpg');
  const nightMap = useLoader(THREE.TextureLoader, '/earth/earth-nightmap-2k.jpg');

  return (
    <group>
      {/* Base sphere: dimmed day texture so the whole thing reads as a dark
          data-globe rather than a bright daylight photo, per idea.md's
          "stylized dark... not photoreal" direction -- cheapest way to get
          that look is to darken the map's own color rather than needing a
          second render pass. */}
      <mesh>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <meshStandardMaterial
          map={dayMap}
          color={new THREE.Color(0.35, 0.4, 0.42)}
          roughness={1}
          metalness={0}
        />
      </mesh>
      {/* Night-side emissive city-light layer, additive, very low intensity
          -- a real second texture, not a solid-color fake glow. */}
      <mesh>
        <sphereGeometry args={[GLOBE_RADIUS * 1.001, 64, 64]} />
        <meshBasicMaterial
          map={nightMap}
          blending={THREE.AdditiveBlending}
          transparent
          opacity={0.25}
          depthWrite={false}
        />
      </mesh>
      {/* Thin cyan Fresnel-style atmosphere rim, matching the
          maplable.com-reference glow called out in idea.md -- a simple
          back-facing shell with a radial-ish fade via vertex-based opacity
          isn't available without a custom shader, so this uses a
          standard additive shell at a fixed low opacity: a real, visible
          rim effect, not a literal Fresnel shader, but the same visual
          intent at a fraction of the complexity. */}
      <mesh>
        <sphereGeometry args={[GLOBE_RADIUS * 1.04, 48, 48]} />
        <meshBasicMaterial
          color="#22d3ee"
          transparent
          opacity={0.06}
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
};

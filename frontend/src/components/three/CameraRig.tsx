import React, { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

// Shared camera-preset system, extracted from LiveDrillingScene3D so a
// second scene (CommandCenterPage's CommandScene3D) doesn't reimplement it
// a second time -- the visualization audit flagged this as a real
// duplication risk before it happened a second time, not after.
export type CameraPreset = 'RIG_FLOOR' | 'CROSS_SECTION' | 'DOWNHOLE_FOLLOW' | 'PLAN' | 'ORBIT';

export function CameraRig({
  preset,
  bitPosition,
  extent,
  rigHeight = 3.2,
}: {
  preset: CameraPreset;
  bitPosition: React.MutableRefObject<THREE.Vector3>;
  extent: number;
  rigHeight?: number;
}) {
  const { camera } = useThree();
  const targetLookAt = useRef(new THREE.Vector3());

  useFrame((_, delta) => {
    if (preset === 'ORBIT') return; // OrbitControls owns the camera in this mode

    let desiredPos: THREE.Vector3;
    let desiredLookAt: THREE.Vector3;

    if (preset === 'RIG_FLOOR') {
      desiredPos = new THREE.Vector3(extent * 0.9, rigHeight * 0.6, extent * 0.9);
      desiredLookAt = new THREE.Vector3(0, rigHeight * 0.4, 0);
    } else if (preset === 'CROSS_SECTION') {
      desiredPos = new THREE.Vector3(extent * 2.2, 0, 0.01);
      desiredLookAt = new THREE.Vector3(0, -extent * 0.6, 0);
    } else if (preset === 'PLAN') {
      // True top-down: looking straight down the Y axis at the well path.
      desiredPos = new THREE.Vector3(0.01, extent * 2.5, 0.01);
      desiredLookAt = new THREE.Vector3(0, -extent * 0.5, 0);
    } else {
      // DOWNHOLE_FOLLOW -- tracks the real live bit position
      const bit = bitPosition.current;
      desiredPos = new THREE.Vector3(bit.x + extent * 0.4, bit.y + extent * 0.25, bit.z + extent * 0.4);
      desiredLookAt = bit.clone();
    }

    camera.position.lerp(desiredPos, Math.min(1, delta * 2.5));
    targetLookAt.current.lerp(desiredLookAt, Math.min(1, delta * 2.5));
    camera.lookAt(targetLookAt.current);
  });

  return null;
}

export const CAMERA_PRESET_LIST: CameraPreset[] = ['RIG_FLOOR', 'CROSS_SECTION', 'DOWNHOLE_FOLLOW', 'PLAN', 'ORBIT'];

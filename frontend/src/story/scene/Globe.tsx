import React, { useMemo, useRef } from 'react';
import { useFrame, useLoader, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import type { StoryState } from './state';

// The story's opening: the whole Earth, turning, the night side lit by
// cities, then a push in on Upper Assam until the planet fills the frame
// and the shot hands over to the real basin terrain (World cross-dissolves
// the two under a short white-haze flash, so the seam never shows).
//
// Built to start fast (the /film globe took ~5 s): one 96-segment sphere,
// the two 2k textures already in public/earth (0.7 MB total, cached by the
// service worker / HTTP cache after the first visit), no stars geometry
// beyond a single Points draw, and no post effects of its own.

const R = 1;
// NHK-002, Upper Assam.
const LAT = 27.23;
const LON = 95.35;

/** Unit vector for (lat, lon) on a three.js sphere whose u=0 is lon -180. */
export function latLonToVec(lat: number, lon: number, r = R) {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

const earthVertex = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vN;
  varying vec3 vV;
  void main() {
    vUv = uv;
    vN = normalize(mat3(modelMatrix) * normal);
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vV = normalize(cameraPosition - wp.xyz);
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;
const earthFragment = /* glsl */ `
  uniform sampler2D uDay;
  uniform sampler2D uNight;
  uniform vec3 uSun;
  varying vec2 vUv;
  varying vec3 vN;
  varying vec3 vV;
  void main() {
    float sun = dot(normalize(vN), normalize(uSun));
    vec3 day = texture2D(uDay, vUv).rgb;
    vec3 night = texture2D(uNight, vUv).rgb;
    float lum = dot(night, vec3(0.299, 0.587, 0.114));
    vec3 cities = night * vec3(1.4, 1.0, 0.6) * smoothstep(0.06, 0.5, lum) * 1.6;
    float dayMix = smoothstep(-0.08, 0.3, sun);
    // A dark, cinematic Earth: muted day side, deep night side.
    vec3 col = mix(cities + day * 0.02, day * 0.62, dayMix);
    // thin warm band along the terminator
    col += vec3(0.95, 0.42, 0.14) * 0.1 * (1.0 - smoothstep(0.0, 0.18, abs(sun)));
    // atmosphere: blue limb on the lit side
    float rim = pow(1.0 - max(dot(normalize(vN), normalize(vV)), 0.0), 3.0);
    col += vec3(0.25, 0.5, 1.0) * rim * (0.25 + 0.75 * smoothstep(-0.2, 0.4, sun));
    gl_FragColor = vec4(col, 1.0);
    #include <colorspace_fragment>
  }
`;
const haloFragment = /* glsl */ `
  uniform vec3 uSun;
  varying vec3 vN;
  varying vec3 vV;
  void main() {
    float rim = 1.0 - max(dot(normalize(vN), normalize(vV)), 0.0);
    float lit = 0.3 + 0.7 * smoothstep(-0.3, 0.5, dot(normalize(vN), normalize(uSun)));
    gl_FragColor = vec4(vec3(0.3, 0.55, 1.0), pow(rim, 4.0) * 0.9 * lit);
  }
`;

function Stars() {
  const geo = useMemo(() => {
    const n = 1800;
    const pos = new Float32Array(n * 3);
    let s = 3;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < n; i++) {
      const u = rnd() * 2 - 1;
      const th = rnd() * Math.PI * 2;
      const r = 40 + rnd() * 20;
      const k = Math.sqrt(1 - u * u);
      pos.set([r * k * Math.cos(th), r * u, r * k * Math.sin(th)], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    return g;
  }, []);
  return (
    <points geometry={geo}>
      <pointsMaterial size={0.06} sizeAttenuation color="#cfd8e3" transparent opacity={0.7} depthWrite={false} fog={false} />
    </points>
  );
}

/**
 * Drives the camera itself while the globe is on screen (state.globe > 0).
 * The basin's CameraDriver hands over when globe reaches 0.
 */
export function Globe({ state }: { state: React.MutableRefObject<StoryState> }) {
  const [day, night] = useLoader(THREE.TextureLoader, ['/earth/earth-daymap-2k.jpg', '/earth/earth-nightmap-2k.jpg']);
  const { camera } = useThree();
  const group = useRef<THREE.Group>(null);
  const site = useMemo(() => latLonToVec(LAT, LON), []);
  const mats = useMemo(() => {
    day.colorSpace = THREE.SRGBColorSpace;
    night.colorSpace = THREE.SRGBColorSpace;
    day.anisotropy = night.anisotropy = 8;
    // Sun over the western Indian Ocean: Assam sits just on the lit side
    // of the terminator, with the night (and city lights) to its east.
    const sun = latLonToVec(5, 55).normalize();
    const earth = new THREE.ShaderMaterial({
      uniforms: { uDay: { value: day }, uNight: { value: night }, uSun: { value: sun } },
      vertexShader: earthVertex,
      fragmentShader: earthFragment,
      fog: false,
    });
    const halo = new THREE.ShaderMaterial({
      uniforms: { uSun: { value: sun } },
      vertexShader: earthVertex,
      fragmentShader: haloFragment,
      transparent: true,
      side: THREE.BackSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      fog: false,
    });
    return { earth, halo };
  }, [day, night]);
  const marker = useRef<THREE.Mesh>(null);
  const dir = useMemo(() => new THREE.Vector3(), []);
  const up = useMemo(() => new THREE.Vector3(0, 1, 0), []);

  useFrame(() => {
    const s = state.current;
    if (!group.current) return;
    group.current.visible = s.globe > 0.001;
    if (!group.current.visible) return;
    // g: 0 at the start of the opening, 1 when the camera reaches the ground.
    const g = s.globeT;
    // The planet turns slowly toward Assam as we approach.
    group.current.rotation.y = (1 - g) * 0.9;
    group.current.updateMatrixWorld();
    const target = site.clone().applyMatrix4(group.current.matrixWorld);
    dir.copy(target).normalize();
    // Distance from the surface: 2.6 radii out -> skimming the atmosphere.
    // Exponential, so the speed feels constant at every scale.
    const alt = 2.6 * Math.pow(0.004 / 2.6, Math.pow(g, 1.25));
    // Start slightly off-axis (a three-quarter view), straighten onto the
    // site as we fall.
    const side = new THREE.Vector3().crossVectors(dir, up).normalize();
    const off = (1 - g) * 0.55;
    camera.position.copy(dir).multiplyScalar(R + alt).addScaledVector(side, off * (R + alt) * 0.6).addScaledVector(up, off * 0.25);
    const look = target.clone().lerp(new THREE.Vector3(), Math.max(0, 1 - g * 1.4) * 0.6);
    camera.up.set(0, 1, 0);
    camera.lookAt(look);
    const pc = camera as THREE.PerspectiveCamera;
    pc.near = Math.max(0.0005, alt * 0.2);
    pc.far = 200;
    pc.fov = THREE.MathUtils.lerp(34, 46, g);
    pc.updateProjectionMatrix();
    if (marker.current) {
      marker.current.position.copy(site).multiplyScalar(1.002);
      const m = marker.current.material as THREE.MeshBasicMaterial;
      m.opacity = Math.min(1, g * 3) * (1 - Math.max(0, (g - 0.8) / 0.2)) * (0.75 + 0.25 * Math.sin(s.time * 4));
      marker.current.scale.setScalar(0.006 + alt * 0.012);
    }
  });

  return (
    <group ref={group}>
      <Stars />
      <mesh material={mats.earth}>
        <sphereGeometry args={[R, 96, 64]} />
      </mesh>
      <mesh material={mats.halo} scale={1.035}>
        <sphereGeometry args={[R, 64, 32]} />
      </mesh>
      {/* NHK-002: a small amber point, the only colour on the planet */}
      <mesh ref={marker}>
        <sphereGeometry args={[1, 12, 8]} />
        <meshBasicMaterial color="#f5a524" transparent opacity={0} toneMapped={false} depthWrite={false} />
      </mesh>
    </group>
  );
}

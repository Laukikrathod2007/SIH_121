import React, { useMemo, useRef } from 'react';
import { useFrame, useLoader, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { latLonToVec3 } from '../../lib/globeGeometry';
import { FALLBACK_MAP_WELLS } from '../../data/fallbackWells';
import { glowTexture } from '../textures';
import { ACT, clamp, easeInOut, lerp, smoothstep, type Shot } from '../timeline';
import type { FilmClock } from '../clock';

// Earth from orbit at night. The opening descends from space onto the
// Upper Assam basin; the finale pulls back out, and every well in the
// dataset is threaded to the active one along the surface.
//
// Well positions are the real coordinates from the NWIS dataset
// (data/fallbackWells.ts mirrors the backend's /api/v2/map/wells).

const R = 2;
const ACTIVE = FALLBACK_MAP_WELLS.find((w) => w.well_id === 'WELL-NHK-002') ?? FALLBACK_MAP_WELLS[0];

const atmosphereVertex = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;
const atmosphereFragment = /* glsl */ `
  uniform vec3 uColor;
  uniform float uPower;
  uniform float uStrength;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    float rim = 1.0 - max(dot(vNormal, vView), 0.0);
    gl_FragColor = vec4(uColor, pow(rim, uPower) * uStrength);
  }
`;

const nightVertex = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorldNormal;
  void main() {
    vUv = uv;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
// Night side shows city lights; a thin terminator band shows a hint of the
// day map so the planet reads as round. Lights are boosted only where the
// texture is bright, so oceans stay black.
const nightFragment = /* glsl */ `
  uniform sampler2D uNight;
  uniform sampler2D uDay;
  uniform vec3 uSunDir;
  uniform float uLights;
  varying vec2 vUv;
  varying vec3 vWorldNormal;
  void main() {
    float sun = dot(normalize(vWorldNormal), normalize(uSunDir));
    vec3 day = texture2D(uDay, vUv).rgb;
    vec3 night = texture2D(uNight, vUv).rgb;
    float lum = dot(night, vec3(0.299, 0.587, 0.114));
    vec3 cities = night * vec3(1.35, 1.0, 0.62) * smoothstep(0.08, 0.5, lum) * uLights;
    float dayMix = smoothstep(-0.05, 0.35, sun);
    vec3 col = mix(cities + day * 0.018, day * 0.55, dayMix);
    // warm terminator glow
    col += vec3(0.9, 0.38, 0.12) * 0.08 * (1.0 - abs(sun * 4.0)) * step(abs(sun), 0.25);
    gl_FragColor = vec4(col, 1.0);
  }
`;

function Stars() {
  const geo = useMemo(() => {
    const n = 2600;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    let s = 3;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < n; i++) {
      const u = rnd() * 2 - 1;
      const th = rnd() * Math.PI * 2;
      const r = 60 + rnd() * 40;
      const k = Math.sqrt(1 - u * u);
      pos.set([r * k * Math.cos(th), r * u, r * k * Math.sin(th)], i * 3);
      const b = 0.35 + rnd() * 0.65;
      col.set([b, b * (0.92 + rnd() * 0.08), b * (0.85 + rnd() * 0.15)], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    return g;
  }, []);
  return (
    <points geometry={geo}>
      <pointsMaterial size={0.16} sizeAttenuation vertexColors transparent opacity={0.85} depthWrite={false} />
    </points>
  );
}

/**
 * Arc from the active well to another well, drawn progressively from the
 * film clock (starting at `startAt` seconds into the finale), with a light
 * that arrives at the far end.
 */
function Thread({ clock, from, to, startAt, color, endSize }: {
  clock: FilmClock; from: THREE.Vector3; to: THREE.Vector3; startAt: number; color: string; endSize: number;
}) {
  const glow = glowTexture();
  const spriteRef = useRef<THREE.Sprite>(null);
  const line = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const n = 64;
    const dist = from.distanceTo(to);
    for (let i = 0; i <= n; i++) {
      const p = from.clone().lerp(to, i / n).normalize();
      pts.push(p.multiplyScalar(R * (1.0006 + Math.sin((Math.PI * i) / n) * dist * 0.35)));
    }
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const m = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    return new THREE.Line(g, m);
  }, [from, to, color]);

  useFrame(() => {
    const p = clamp((clock.t - ACT.finale.start - startAt) / 2.6);
    const e = easeInOut(p);
    line.geometry.setDrawRange(0, Math.max(0, Math.floor(e * 65)));
    (line.material as THREE.LineBasicMaterial).opacity = 0.7 * clamp(p * 4);
    if (spriteRef.current) {
      const arrive = smoothstep(0.85, 1, p);
      spriteRef.current.scale.setScalar(endSize * (0.3 + arrive));
      (spriteRef.current.material as THREE.SpriteMaterial).opacity = arrive;
    }
  });

  return (
    <>
      <primitive object={line} />
      <sprite ref={spriteRef} position={to}>
        <spriteMaterial map={glow} color={color} transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} />
      </sprite>
    </>
  );
}

export function EarthScene({ clock, shot }: { clock: FilmClock; shot: Shot }) {
  const [day, night] = useLoader(THREE.TextureLoader, ['/earth/earth-daymap-2k.jpg', '/earth/earth-nightmap-2k.jpg']);
  const { camera } = useThree();
  const glow = glowTexture();
  const globeRef = useRef<THREE.Group>(null);
  const markerRef = useRef<THREE.Sprite>(null);
  const haloRef = useRef<THREE.Sprite>(null);

  const activePos = useMemo(() => latLonToVec3(ACTIVE.lat, ACTIVE.lon, R), []);
  const wells = useMemo(
    () => FALLBACK_MAP_WELLS.map((w) => ({ id: w.well_id, pos: latLonToVec3(w.lat, w.lon, R * 1.0008) })),
    [],
  );
  // The Volve wells sit in the North Sea; adding them makes the finale's
  // "every well" a planetary statement rather than a basin-scale one.
  const volve = useMemo(() => [latLonToVec3(58.44, 1.89, R * 1.0008), latLonToVec3(58.43, 1.92, R * 1.0008)], []);

  // Sun placed behind the planet, off to one side, so Assam is in night with the terminator in frame.
  const sunDir = useMemo(() => {
    const d = activePos.clone().normalize().multiplyScalar(-1);
    d.add(new THREE.Vector3(0, 0.35, 0)).normalize();
    return d.applyAxisAngle(new THREE.Vector3(0, 1, 0), 1.25);
  }, [activePos]);

  const uniforms = useMemo(
    () => ({ uNight: { value: night }, uDay: { value: day }, uSunDir: { value: sunDir }, uLights: { value: 1.6 } }),
    [night, day, sunDir],
  );

  useFrame(() => {
    const t = clock.t;
    const up = activePos.clone().normalize();
    // Local "east" so the camera can tilt along the surface toward the horizon.
    const east = new THREE.Vector3(0, 1, 0).cross(up).normalize();
    const north = up.clone().cross(east).normalize();

    let dist: number;
    let tilt: number; // 0 = straight down, 1 = grazing the horizon
    let orbit: number;
    if (shot.variant === 'finale') {
      const p = easeInOut(clamp((t - ACT.finale.start) / 14));
      dist = lerp(0.07, 4.6, p);
      tilt = lerp(0.62, 0.18, p);
      orbit = lerp(0.0, -0.55, p);
    } else {
      const p = easeInOut(clamp((t - ACT.earth.start) / (ACT.earth.end - ACT.earth.start)));
      dist = lerp(5.4, 0.055, Math.pow(p, 0.75));
      tilt = lerp(0.12, 0.68, smoothstep(0.45, 1, p));
      orbit = lerp(0.9, 0.0, p);
    }
    // Camera direction from the surface point: mostly "up", tilted toward north,
    // swung around the local up axis for a slow orbital drift.
    const swing = east.clone().multiplyScalar(Math.sin(orbit)).add(north.clone().multiplyScalar(-Math.cos(orbit)));
    const dir = up.clone().multiplyScalar(Math.cos(tilt * 1.25)).add(swing.multiplyScalar(Math.sin(tilt * 1.25))).normalize();
    camera.position.copy(activePos.clone().add(dir.multiplyScalar(dist)));
    const look = activePos.clone().add(north.clone().multiplyScalar(dist * tilt * 0.35));
    camera.up.copy(up);
    camera.lookAt(look);
    (camera as THREE.PerspectiveCamera).fov = shot.variant === 'finale' ? 32 : lerp(30, 46, smoothstep(ACT.earth.start + 6, ACT.earth.end, t));
    (camera as THREE.PerspectiveCamera).near = 0.0005;
    (camera as THREE.PerspectiveCamera).updateProjectionMatrix();

    // The active well's light: a slow breathing pulse.
    const pulse = 0.75 + Math.sin(t * 2.2) * 0.25;
    const s = Math.max(0.004, dist * 0.06);
    markerRef.current?.scale.setScalar(s * 0.5);
    haloRef.current?.scale.setScalar(s * (2.4 + pulse));
    if (haloRef.current) (haloRef.current.material as THREE.SpriteMaterial).opacity = 0.5 * pulse;
  });

  return (
    <>
      <color attach="background" args={['#010204']} />
      <ambientLight intensity={0.05} />
      <Stars />
      <group ref={globeRef}>
        <mesh>
          <sphereGeometry args={[R, 128, 128]} />
          <shaderMaterial vertexShader={nightVertex} fragmentShader={nightFragment} uniforms={uniforms} />
        </mesh>
        <mesh scale={1.035}>
          <sphereGeometry args={[R, 96, 96]} />
          <shaderMaterial
            vertexShader={atmosphereVertex}
            fragmentShader={atmosphereFragment}
            uniforms={{ uColor: { value: new THREE.Color('#4aa8ff') }, uPower: { value: 3.2 }, uStrength: { value: 0.9 } }}
            side={THREE.BackSide}
            transparent
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
        <mesh scale={1.004}>
          <sphereGeometry args={[R, 96, 96]} />
          <shaderMaterial
            vertexShader={atmosphereVertex}
            fragmentShader={atmosphereFragment}
            uniforms={{ uColor: { value: new THREE.Color('#7cc4ff') }, uPower: { value: 5.0 }, uStrength: { value: 0.55 } }}
            transparent
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>

        {/* Active well: a single warm light on the night side. */}
        <sprite ref={haloRef} position={activePos.clone().multiplyScalar(1.0012)}>
          <spriteMaterial map={glow} color="#ffb067" transparent blending={THREE.AdditiveBlending} depthWrite={false} />
        </sprite>
        <sprite ref={markerRef} position={activePos.clone().multiplyScalar(1.0012)}>
          <spriteMaterial map={glow} color="#fff3df" transparent blending={THREE.AdditiveBlending} depthWrite={false} />
        </sprite>

        {shot.variant === 'finale' && (
          <>
            {wells
              .filter((w) => w.id !== ACTIVE.well_id)
              .map((w, i) => (
                <Thread key={w.id} clock={clock} from={activePos} to={w.pos} startAt={0.8 + i * 0.28} color="#67e8f9" endSize={0.012} />
              ))}
            {volve.map((v, i) => (
              <Thread key={'volve' + i} clock={clock} from={activePos} to={v} startAt={6.5 + i * 0.5} color="#7dd3fc" endSize={0.05} />
            ))}
          </>
        )}
      </group>
    </>
  );
}

useLoader.preload(THREE.TextureLoader, ['/earth/earth-daymap-2k.jpg', '/earth/earth-nightmap-2k.jpg']);

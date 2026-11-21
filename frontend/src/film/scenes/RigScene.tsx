import React, { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { glowTexture, smokeTexture, mulberry32 } from '../textures';
import { ACT, clamp, easeInOut, lerp, smoothstep, type Shot } from '../timeline';
import type { FilmClock } from '../clock';

// The rig at night. Built around the project's own rig model
// (public/models/active_surface_rig.glb, original project geometry, ~30 m
// tall). Lighting is "practical": sodium work lights on the mast and pad,
// a warm doghouse window, a red aviation beacon, cold moonlight. Steam
// and light rain catch the work lights.

const MODEL = '/models/active_surface_rig.glb';
const MAST_TOP = 29.8;

type V3 = [number, number, number];

const SODIUM = '#ff9a3c';
const SODIUM_LIGHTS: { pos: V3; intensity: number }[] = [
  { pos: [6.5, 9.5, 5.5], intensity: 900 },
  { pos: [-6.0, 7.5, -5.0], intensity: 650 },
  { pos: [1.5, 18.0, 2.0], intensity: 600 },
  { pos: [-11.0, 4.0, 7.0], intensity: 450 },
];

function RigModel() {
  const { scene } = useGLTF(MODEL);
  const model = useMemo(() => {
    const s = scene.clone(true);
    s.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.castShadow = true;
      m.receiveShadow = true;
      const src = m.material as THREE.MeshStandardMaterial;
      const mat = src.clone();
      // Wet-night steel: a touch more metal, a bit less rough.
      mat.metalness = Math.min(1, (src.metalness ?? 0.5) + 0.15);
      mat.roughness = Math.max(0.28, (src.roughness ?? 0.6) - 0.2);
      mat.envMapIntensity = 0.4;
      m.material = mat;
    });
    return s;
  }, [scene]);
  return <primitive object={model} />;
}

/** Wet ground: dark, faintly reflective, with puddle variation. */
function Ground() {
  const tex = useMemo(() => {
    const S = 512;
    const c = document.createElement('canvas');
    c.width = S;
    c.height = S;
    const g = c.getContext('2d')!;
    const rnd = mulberry32(5);
    g.fillStyle = '#7a7a7a';
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 90; i++) {
      const x = rnd() * S;
      const y = rnd() * S;
      const r = 10 + rnd() * 60;
      const grad = g.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, 'rgba(10,10,10,0.9)');
      grad.addColorStop(1, 'rgba(10,10,10,0)');
      g.fillStyle = grad;
      g.fillRect(0, 0, S, S);
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(6, 6);
    return t;
  }, []);
  return (
    <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, -0.3, 0]}>
      <circleGeometry args={[220, 64]} />
      <meshStandardMaterial color="#14161a" roughnessMap={tex} roughness={1} metalness={0.25} />
    </mesh>
  );
}

/**
 * Night sky: deep blue overhead, a faint warm glow on the horizon from a
 * distant town, so the derrick reads as a silhouette against it.
 */
function Sky() {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        uniforms: {},
        vertexShader: /* glsl */ `
          varying vec3 vDir;
          void main() {
            vDir = normalize(position);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: /* glsl */ `
          varying vec3 vDir;
          void main() {
            float h = vDir.y;
            vec3 top = vec3(0.012, 0.02, 0.04);
            vec3 mid = vec3(0.05, 0.075, 0.12);
            vec3 hor = vec3(0.16, 0.12, 0.11);
            vec3 col = mix(mid, top, smoothstep(0.05, 0.6, h));
            col = mix(hor, col, smoothstep(-0.02, 0.12, h));
            // Town glow, low on the horizon off to one side.
            float glow = exp(-pow((atan(vDir.x, -vDir.z) - 0.5) / 0.5, 2.0)) * exp(-max(h, 0.0) * 14.0);
            col += vec3(0.22, 0.12, 0.05) * glow;
            gl_FragColor = vec4(col, 1.0);
          }
        `,
      }),
    [],
  );
  return (
    <mesh material={mat}>
      <sphereGeometry args={[400, 32, 16]} />
    </mesh>
  );
}

/** Distant tree line as layered silhouettes, so the horizon isn't empty. */
function TreeLine() {
  const geo = useMemo(() => {
    const rnd = mulberry32(17);
    const shape = new THREE.Shape();
    const W = 900;
    shape.moveTo(-W / 2, 0);
    for (let x = -W / 2; x <= W / 2; x += 3) {
      shape.lineTo(x, 7 + Math.sin(x * 0.03) * 3 + rnd() * 5);
    }
    shape.lineTo(W / 2, 0);
    shape.lineTo(-W / 2, 0);
    return new THREE.ShapeGeometry(shape);
  }, []);
  return (
    <>
      <mesh geometry={geo} position={[0, -0.3, -160]}>
        <meshBasicMaterial color="#05070a" fog />
      </mesh>
      <mesh geometry={geo} position={[60, -0.3, -230]} scale={[1, 1.4, 1]}>
        <meshBasicMaterial color="#070a10" fog />
      </mesh>
    </>
  );
}

function Halo({ pos, color, size, flicker = 0 }: { pos: V3; color: string; size: number; flicker?: number }) {
  const ref = useRef<THREE.Sprite>(null);
  const seed = useMemo(() => Math.random() * 100, []);
  useFrame(({ clock }) => {
    if (!ref.current || !flicker) return;
    const f = 1 - flicker * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 23 + seed)) * (Math.sin(clock.elapsedTime * 3.1 + seed) > 0.97 ? 1 : 0);
    ref.current.scale.setScalar(size * f);
  });
  return (
    <sprite ref={ref} position={pos} scale={size}>
      <spriteMaterial map={glowTexture()} color={color} transparent blending={THREE.AdditiveBlending} depthWrite={false} />
    </sprite>
  );
}

/** Aviation beacon at the crown: a slow red blink. */
function Beacon({ clock }: { clock: FilmClock }) {
  const ref = useRef<THREE.Sprite>(null);
  const light = useRef<THREE.PointLight>(null);
  useFrame(() => {
    const on = Math.pow(Math.max(0, Math.sin(clock.t * 2.1)), 6);
    if (ref.current) ref.current.scale.setScalar(1.2 + on * 3.2);
    if (light.current) light.current.intensity = on * 60;
  });
  return (
    <>
      <pointLight ref={light} position={[0, MAST_TOP + 0.6, 0]} color="#ff2a1a" distance={30} decay={2} />
      <sprite ref={ref} position={[0, MAST_TOP + 0.6, 0]}>
        <spriteMaterial map={glowTexture()} color="#ff3322" transparent blending={THREE.AdditiveBlending} depthWrite={false} />
      </sprite>
    </>
  );
}

/** Steam drifting off the mud tanks, lit by the work lights. */
function Steam({ clock }: { clock: FilmClock }) {
  const N = 46;
  const ref = useRef<THREE.Group>(null);
  const puffs = useMemo(() => {
    const rnd = mulberry32(23);
    return Array.from({ length: N }, () => ({
      x: -4 + rnd() * 5,
      z: -6 + rnd() * 3,
      phase: rnd(),
      speed: 0.035 + rnd() * 0.03,
      drift: 0.6 + rnd() * 0.8,
      size: 4 + rnd() * 5,
      rot: rnd() * Math.PI,
    }));
  }, []);
  useFrame(() => {
    const g = ref.current;
    if (!g) return;
    g.children.forEach((c, i) => {
      const p = puffs[i];
      const life = (clock.t * p.speed + p.phase) % 1;
      c.position.set(p.x + life * 9 * p.drift, 1.5 + life * 16, p.z - life * 4);
      c.scale.setScalar(p.size * (0.5 + life * 1.6));
      const mat = (c as THREE.Sprite).material as THREE.SpriteMaterial;
      mat.opacity = Math.sin(life * Math.PI) * 0.22;
      mat.rotation = p.rot + life * 0.6;
    });
  });
  const tex = smokeTexture();
  return (
    <group ref={ref}>
      {puffs.map((_, i) => (
        <sprite key={i}>
          <spriteMaterial map={tex} color="#c9b8a0" transparent depthWrite={false} opacity={0} />
        </sprite>
      ))}
    </group>
  );
}

/** Fine rain streaks; only visible where they cross the light. */
function Rain({ clock }: { clock: FilmClock }) {
  const N = 2400;
  const { geo, base } = useMemo(() => {
    const rnd = mulberry32(31);
    const base = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) base.set([(rnd() - 0.5) * 70, rnd() * 45, (rnd() - 0.5) * 70], i * 3);
    const pos = new Float32Array(N * 6);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    return { geo: g, base };
  }, []);
  useFrame(() => {
    const arr = geo.attributes.position.array as Float32Array;
    for (let i = 0; i < N; i++) {
      const x = base[i * 3];
      const z = base[i * 3 + 2];
      const y = 45 - ((45 - base[i * 3 + 1] + clock.t * 24) % 45);
      arr[i * 6] = x;
      arr[i * 6 + 1] = y;
      arr[i * 6 + 2] = z;
      arr[i * 6 + 3] = x + 0.12;
      arr[i * 6 + 4] = y - 0.55;
      arr[i * 6 + 5] = z;
    }
    geo.attributes.position.needsUpdate = true;
  });
  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial color="#9aa8b8" transparent opacity={0.16} depthWrite={false} />
    </lineSegments>
  );
}

// Camera paths. Every move is slow and continuous; no cuts within a shot.
function rigCamera(t: number, shot: Shot, out: { pos: THREE.Vector3; look: THREE.Vector3; fov: number }) {
  if (shot.variant === 'decision') {
    // Low and close on the drill floor, pushing in on the rotary table.
    const p = easeInOut(clamp((t - shot.start) / (shot.end - shot.start)));
    out.pos.set(lerp(8.5, 5.2, p), lerp(4.2, 3.6, p), lerp(10.5, 7.0, p));
    out.look.set(0, lerp(4.0, 3.2, p), 0);
    out.fov = lerp(34, 28, p);
    return;
  }
  const lt = t - ACT.rig.start;
  const dur = ACT.rig.end - ACT.rig.start;
  const p = clamp(lt / dur);
  if (p < 0.55) {
    // 1. Wide establishing: symmetrical, low, slow dolly in.
    const q = easeInOut(p / 0.55);
    out.pos.set(lerp(-3, 0, q), lerp(2.2, 3.0, q), lerp(78, 52, q));
    out.look.set(0, lerp(15, 13, q), 0);
    out.fov = 30;
  } else {
    // 2. Keep pushing in while tilting up the mast toward the crown and
    //    the beacon. The camera stays far enough back that the whole mast
    //    stays in frame.
    const q = easeInOut((p - 0.55) / 0.45);
    out.pos.set(lerp(0, 4, q), lerp(3.0, 1.6, q), lerp(52, 40, q));
    out.look.set(0, lerp(13, 22, q), 0);
    out.fov = lerp(30, 40, q);
  }
}

export function RigScene({ clock, shot }: { clock: FilmClock; shot: Shot }) {
  const { camera, scene } = useThree();
  const cam = useMemo(() => ({ pos: new THREE.Vector3(), look: new THREE.Vector3(), fov: 30 }), []);
  const moon = useRef<THREE.DirectionalLight>(null);

  useFrame(() => {
    rigCamera(clock.t, shot, cam);
    // Handheld: a faint, slow breathing drift on top of the dolly.
    const t = clock.t;
    const hx = Math.sin(t * 0.7) * 0.05 + Math.sin(t * 1.9) * 0.02;
    const hy = Math.sin(t * 0.9 + 1) * 0.04;
    camera.position.set(cam.pos.x + hx, cam.pos.y + hy, cam.pos.z);
    camera.up.set(0, 1, 0);
    camera.lookAt(cam.look);
    const pc = camera as THREE.PerspectiveCamera;
    pc.fov = cam.fov;
    pc.near = 0.1;
    pc.updateProjectionMatrix();
  });

  // Exponential fog: light rain haze that the sodium lights glow through.
  React.useEffect(() => {
    scene.fog = new THREE.FogExp2('#0a0c10', 0.0075);
    return () => {
      scene.fog = null;
    };
  }, [scene]);

  const introGlow = shot.variant === 'intro' ? smoothstep(ACT.rig.start, ACT.rig.start + 4, clock.t) : 1;

  return (
    <>
      <color attach="background" args={['#06080c']} />
      <Sky />
      <hemisphereLight args={['#2a3c58', '#0b0906', 0.22 * introGlow]} />
      {/* Moon from behind the rig: rim light on the mast's edges. */}
      <directionalLight ref={moon} position={[-30, 50, -60]} intensity={1.1} color="#9db4d6" />
      {SODIUM_LIGHTS.map((l, i) => (
        <React.Fragment key={i}>
          <pointLight position={l.pos} color={SODIUM} intensity={l.intensity} distance={60} decay={2} castShadow={i === 0} shadow-mapSize={[1024, 1024]} />
          <Halo pos={l.pos} color={SODIUM} size={3.2} flicker={i === 3 ? 0.4 : 0} />
        </React.Fragment>
      ))}
      {/* Doghouse window: cold blue-white screen glow, where the engineer is. */}
      <pointLight position={[-8.2, 2.4, 4.6]} color="#bfe3ff" intensity={60} distance={14} decay={2} />
      <Halo pos={[-8.2, 2.4, 4.6]} color="#cfeaff" size={1.6} />
      <Beacon clock={clock} />
      <RigModel />
      <Ground />
      <TreeLine />
      <Steam clock={clock} />
      <Rain clock={clock} />
    </>
  );
}

useGLTF.preload(MODEL);

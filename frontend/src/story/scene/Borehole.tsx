import React, { Suspense, useEffect, useMemo, useRef } from 'react';
import { useFrame, useLoader, useThree } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import type { StoryState } from './state';

// Down the hole. A self-contained scene (rendered instead of the basin
// while the camera is underground): the open borehole of NHK-002, its
// walls the real formations at their real depths, textured with CC0 rock
// scans (Poly Haven) matched to each lithology, the drill string rotating
// in the middle and a tricone bit cutting at the bottom.
//
// Units: metres. The hole is a 12¼" (0.31 m) section, drawn wider (2.4 m
// radius) so the camera can travel inside it; depth runs from 0 at the
// surface to 3,200 m, with the camera covering it in ~10 s.

export const HOLE_R = 2.4;
const PIPE_R = 0.55;

/** NHK-002 formation tops (m MD), from /api/v2/formations. */
export const COLUMN: { name: string; top: number; tex: string; tint: string }[] = [
  { name: 'Alluvium · Dihing', top: 0, tex: 'alluvium', tint: '#b9a98f' },
  { name: 'Tipam Sandstone', top: 390, tex: 'tipam', tint: '#d9b48a' },
  { name: 'Girujan Clay', top: 1169, tex: 'girujan', tint: '#b58f7a' },
  { name: 'Barail', top: 1451, tex: 'barail', tint: '#a59a86' },
  { name: 'Barail Coal-Shale', top: 2135, tex: 'kopili', tint: '#6f6a64' },
  { name: 'Kopili', top: 2674, tex: 'kopili', tint: '#9c6440' },
  { name: 'Sylhet · Langpar', top: 3128, tex: 'sylhet', tint: '#d6d0c2' },
];
export const BASE_M = 3240;

export function formationAt(md: number) {
  let f = COLUMN[0];
  for (const c of COLUMN) if (md >= c.top) f = c;
  return f;
}

function useRockSet(name: string) {
  const [diff, nor, rough] = useLoader(THREE.TextureLoader, [
    `/story/rock/${name}_diff.jpg`,
    `/story/rock/${name}_nor.jpg`,
    `/story/rock/${name}_rough.jpg`,
  ]);
  return useMemo(() => {
    diff.colorSpace = THREE.SRGBColorSpace;
    for (const t of [diff, nor, rough]) {
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.repeat.set(3, 2.2);
      t.anisotropy = 8;
    }
    return { diff, nor, rough };
  }, [diff, nor, rough]);
}

/** One formation interval of the hole wall, from top to base (m). */
function Wall({ top, base, tex, tint }: { top: number; base: number; tex: string; tint: string }) {
  const set = useRockSet(tex);
  const len = base - top;
  const geo = useMemo(() => {
    // Inside-out cylinder with a little radial noise so the wall isn't a
    // perfect tube (washouts, ledges).
    const g = new THREE.CylinderGeometry(HOLE_R, HOLE_R, len, 48, Math.max(8, Math.round(len / 6)), true);
    const pos = g.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const z = pos.getZ(i);
      const a = Math.atan2(z, x);
      const n = 1 + 0.06 * Math.sin(a * 5 + y * 0.31) + 0.04 * Math.sin(a * 11 - y * 0.9) + 0.03 * Math.sin(y * 2.3);
      pos.setX(i, x * n);
      pos.setZ(i, z * n);
    }
    g.computeVertexNormals();
    // UVs: wrap 3x around, and tile vertically every ~6 m.
    const uv = g.attributes.uv as THREE.BufferAttribute;
    for (let i = 0; i < uv.count; i++) uv.setY(i, (uv.getY(i) * len) / 6);
    return g;
  }, [len]);
  return (
    <mesh geometry={geo} position={[0, -top - len / 2, 0]}>
      <meshStandardMaterial
        map={set.diff}
        normalMap={set.nor}
        normalScale={new THREE.Vector2(1.6, 1.6)}
        roughnessMap={set.rough}
        color={tint}
        side={THREE.BackSide}
        roughness={1}
      />
    </mesh>
  );
}

/** Formation contacts: a thin bright seam where the rock changes. */
function Contacts() {
  return (
    <>
      {COLUMN.slice(1).map((c) => (
        <mesh key={c.name} position={[0, -c.top, 0]} rotation-x={-Math.PI / 2}>
          <ringGeometry args={[HOLE_R * 0.96, HOLE_R * 1.08, 64]} />
          <meshBasicMaterial color={c.name === 'Kopili' ? '#ff8a3c' : '#e8dcc4'} transparent opacity={0.55} side={THREE.DoubleSide} toneMapped={false} />
        </mesh>
      ))}
    </>
  );
}

/** Drill string: steel pipe with tool joints every 9.5 m, rotating. */
function DrillString({ bitMd }: { bitMd: number }) {
  const ref = useRef<THREE.Group>(null);
  const len = bitMd;
  const joints = useMemo(() => {
    const out: number[] = [];
    for (let d = 9.5; d < len - BHA_LEN - 2; d += 9.5) out.push(d);
    return out;
  }, [len]);
  const steel = useMemo(() => new THREE.MeshStandardMaterial({ color: '#9aa3ad', metalness: 0.9, roughness: 0.28 }), []);
  const joint = useMemo(() => new THREE.CylinderGeometry(PIPE_R * 1.35, PIPE_R * 1.35, 0.5, 20), []);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 2.4; // ~ 23 rpm on screen
  });
  return (
    <group ref={ref}>
      {/* Drill pipe down to the top of the bottom-hole assembly (~15 m above the bit). */}
      <mesh material={steel} position={[0, -(len - BHA_LEN) / 2, 0]}>
        <cylinderGeometry args={[PIPE_R, PIPE_R, len - BHA_LEN, 20]} />
      </mesh>
      {joints.map((d) => (
        <mesh key={d} geometry={joint} material={steel} position={[0, -d, 0]} />
      ))}
      <Suspense
        fallback={
          <>
            <mesh material={steel} position={[0, -len + 8, 0]}>
              <cylinderGeometry args={[PIPE_R * 1.6, PIPE_R * 1.6, 13, 20]} />
            </mesh>
            <PdcBit y={-len} />
          </>
        }
      >
        <ModelBha y={-len} />
      </Suspense>
    </group>
  );
}

/**
 * The detailed bottom-hole assembly from the project's own digital-twin
 * model (public/landing/assets/3d-models/well-digital-twin.glb, also used
 * on the landing page): PDC bit with 24 cutters and nozzles, rotary
 * steerable unit, sensor sub, MWD with telemetry bands, collar and
 * stabilizers. Only those parts are taken from the file (not its wellhead,
 * casing or formation slabs). In the file the BHA lies along +x at
 * y = -2.15 with the bit face at x ≈ 2.18; here it is stood upright, bit
 * down, and scaled so the bit just fills the drawn hole (gauge).
 */
const BHA_URL = '/landing/assets/3d-models/well-digital-twin.glb';
const BHA_PARTS = /^(Bit|Collar|MWD|Steering|Sensor|Stabilizer_blade\d*)$/;
// The bit's gauge in the file is ~0.36 units radius (node scale 1.45
// included): x4 = 1.46 m. The drawn hole is already wider than true
// scale (so the camera fits); this leaves an annulus the camera can look
// down, past the whole assembly (bit to collar ~10.6 m) to the bit.
const BHA_SCALE = 4;
/** Top of the model assembly above the bit (m), at BHA_SCALE. */
const BHA_LEN = 10.6;

function ModelBha({ y }: { y: number }) {
  const gltf = useGLTF(BHA_URL);
  const { gl } = useThree();
  const bha = useMemo(() => {
    const g = new THREE.Group();
    // Studio reflections for the steel (generated locally, no download),
    // applied to these materials only, so the rock walls are unaffected.
    const pmrem = new THREE.PMREMGenerator(gl);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    const mats = new Map<THREE.Material, THREE.Material>();
    for (const child of gltf.scene.children) {
      if (!BHA_PARTS.test(child.name)) continue;
      const c = child.clone(true);
      c.traverse((o) => {
        const m = o as THREE.Mesh;
        if (!m.isMesh) return;
        const src = m.material as THREE.MeshStandardMaterial;
        let mm = mats.get(src) as THREE.MeshStandardMaterial | undefined;
        if (!mm) {
          mm = src.clone();
          mm.envMap = env;
          mm.envMapIntensity = 0.7;
          mats.set(src, mm);
        }
        m.material = mm;
      });
      g.add(c);
    }
    return { g, env };
  }, [gltf, gl]);
  useEffect(() => () => bha.env.dispose(), [bha]);
  return (
    <group position={[0, y, 0]}>
      <group rotation-z={-Math.PI / 2} scale={BHA_SCALE}>
        <group position={[-2.18, 2.15, 0]}>
          <primitive object={bha.g} />
        </group>
      </group>
    </group>
  );
}
useGLTF.preload(BHA_URL);

/**
 * A PDC (polycrystalline diamond compact) bit, the type used for most
 * modern Assam sections: a steel/matrix body with six spiral blades, each
 * set with a row of round diamond cutters, nozzles between the blades.
 * Built from primitives; the whole bit turns with the string.
 */
function PdcBit({ y }: { y: number }) {
  const BLADES = 6;
  const R = HOLE_R * 0.86;
  const body = useMemo(() => new THREE.MeshStandardMaterial({ color: '#4a4f57', metalness: 0.75, roughness: 0.42 }), []);
  const blade = useMemo(() => new THREE.MeshStandardMaterial({ color: '#2f3339', metalness: 0.7, roughness: 0.5 }), []);
  const cutterFace = useMemo(() => new THREE.MeshStandardMaterial({ color: '#cfd6de', metalness: 0.95, roughness: 0.12 }), []);
  const cutterBody = useMemo(() => new THREE.MeshStandardMaterial({ color: '#8b8f94', metalness: 0.85, roughness: 0.3 }), []);
  const cutter = useMemo(() => new THREE.CylinderGeometry(0.11, 0.11, 0.14, 18), []);
  const bladeGeo = useMemo(() => new THREE.BoxGeometry(0.34, 0.95, R * 0.92), [R]);
  return (
    <group position={[0, y, 0]}>
      {/* Shank and gauge body */}
      <mesh material={body} position={[0, 1.55, 0]}>
        <cylinderGeometry args={[PIPE_R * 1.6, R * 0.82, 1.1, 32]} />
      </mesh>
      {/* Crown: a shallow dome the blades sit on */}
      <mesh material={body} position={[0, 0.62, 0]} scale={[1, 0.45, 1]}>
        <sphereGeometry args={[R * 0.8, 36, 18, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>
      {Array.from({ length: BLADES }, (_, i) => {
        const a = (i / BLADES) * Math.PI * 2;
        return (
          <group key={i} rotation={[0, a, 0]}>
            {/* Blade: a rib from the centre to the gauge, slightly swept */}
            <mesh material={blade} geometry={bladeGeo} position={[0, 0.55, R * 0.46]} rotation={[0, 0.18, 0]} />
            {/* Cutters along the leading edge, facing the direction of rotation */}
            {Array.from({ length: 5 }, (_, k) => {
              const r = R * (0.2 + k * 0.17);
              const dy = 0.1 + Math.sqrt(Math.max(0, 1 - (r / R) ** 2)) * 0.12;
              return (
                <group key={k} position={[0.19, dy, r]} rotation={[0, 0, Math.PI / 2]}>
                  <mesh geometry={cutter} material={cutterBody} />
                  <mesh position={[0, 0.072, 0]} rotation={[0, 0, 0]}>
                    <cylinderGeometry args={[0.1, 0.1, 0.012, 18]} />
                    <primitive object={cutterFace} attach="material" />
                  </mesh>
                </group>
              );
            })}
          </group>
        );
      })}
    </group>
  );
}

/**
 * Drilling mud rising up the annulus: a faint, slow, streaked sheet just
 * inside the wall, so the hole reads as full of fluid, not empty air.
 */
function MudFlow({ bitMd }: { bitMd: number }) {
  const L = 140;
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        side: THREE.BackSide,
        uniforms: { uTime: { value: 0 } },
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
        fragmentShader: /* glsl */ `
          uniform float uTime;
          varying vec2 vUv;
          float h(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 45758.5); }
          float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
            return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
          void main(){
            // streaks stretched along the hole, moving up
            vec2 p = vec2(vUv.x * 40.0, vUv.y * 18.0 - uTime * 0.9);
            float s = n(p) * 0.6 + n(p * 2.3 + 7.0) * 0.4;
            float a = smoothstep(0.55, 0.9, s) * 0.10;
            // fade near the ends of the sheet
            a *= smoothstep(0.0, 0.15, vUv.y) * smoothstep(1.0, 0.85, vUv.y);
            gl_FragColor = vec4(vec3(0.62, 0.52, 0.42), a);
          }`,
      }),
    [],
  );
  useFrame(({ clock }) => {
    mat.uniforms.uTime.value = clock.elapsedTime;
  });
  return (
    <mesh material={mat} position={[0, -bitMd + L / 2, 0]}>
      <cylinderGeometry args={[HOLE_R * 0.9, HOLE_R * 0.9, L, 40, 1, true]} />
    </mesh>
  );
}

/** Cuttings: rock fragments lifted by the mud up the annulus. */
function Cuttings({ bitMd }: { bitMd: number }) {
  const N = 260;
  const ref = useRef<THREE.InstancedMesh>(null);
  const seeds = useMemo(() => {
    let s = 11;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    return Array.from({ length: N }, () => ({ a: rnd() * Math.PI * 2, r: PIPE_R + 0.25 + rnd() * (HOLE_R - PIPE_R - 0.6), y: rnd() * 60, sp: 2 + rnd() * 3, sz: 0.03 + rnd() * 0.07 }));
  }, []);
  const m = useMemo(() => new THREE.Matrix4(), []);
  const q = useMemo(() => new THREE.Quaternion(), []);
  const e = useMemo(() => new THREE.Euler(), []);
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (!ref.current) return;
    seeds.forEach((c, i) => {
      const yy = -bitMd + ((c.y + t * c.sp) % 60);
      const a = c.a + t * 0.8;
      e.set(t * c.sp, t, 0);
      q.setFromEuler(e);
      m.compose(new THREE.Vector3(Math.cos(a) * c.r, yy, Math.sin(a) * c.r), q, new THREE.Vector3(c.sz, c.sz * 0.6, c.sz));
      ref.current!.setMatrixAt(i, m);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  });
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, N]}>
      <dodecahedronGeometry args={[1, 0]} />
      <meshStandardMaterial color="#8a7a66" roughness={0.9} />
    </instancedMesh>
  );
}

/**
 * The borehole scene. `camMd` (state) is the camera's depth; the camera
 * looks down the hole past the drill string, with a lamp that travels with
 * it. At the bottom the view settles on the bit cutting into the Kopili.
 */
export function Borehole({ state }: { state: React.MutableRefObject<StoryState> }) {
  const { camera, scene } = useThree();
  const lamp = useRef<THREE.PointLight>(null);
  const fill = useRef<THREE.PointLight>(null);
  const bitMd = 2850;
  const intervals = useMemo(
    () =>
      COLUMN.map((c, i) => ({ ...c, base: i + 1 < COLUMN.length ? COLUMN[i + 1].top : BASE_M })),
    [],
  );
  useFrame(() => {
    const s = state.current;
    // The hole owns the camera only while it is the world on screen.
    if (s.world !== 'hole') return;
    const md = s.holeMd;
    // Camera in the annulus, beside the pipe, looking down the hole: the
    // string runs off into the dark below, the wall streams past. It
    // swings slowly around the string as it falls.
    const a = s.time * 0.25;
    const r = HOLE_R * 0.72;
    camera.position.set(Math.cos(a) * r, -md, Math.sin(a) * r);
    // Look straight down the hole, toward the far side of the pipe.
    const look = new THREE.Vector3(-Math.cos(a) * 0.15, -md - s.holeLook, -Math.sin(a) * 0.15);
    camera.lookAt(look);
    const pc = camera as THREE.PerspectiveCamera;
    pc.fov = s.holeFov;
    pc.near = 0.05;
    pc.far = 400;
    pc.updateProjectionMatrix();
    // The lamp rides just above and behind the lens, so it never shows as a
    // hot spot in frame; it only rakes the wall ahead of us.
    lamp.current?.position.set(camera.position.x * 0.8, -md + 0.6, camera.position.z * 0.8);
    fill.current?.position.set(0, -Math.min(md + 22, bitMd - 3), 0);
  });
  return (
    <group>
      <color attach="background" args={['#030302']} />
      <ambientLight intensity={0.22} color="#f2dcc0" />
      {/* Camera lamp: lights the wall around us and well ahead. */}
      <pointLight ref={lamp} color="#ffe6c4" intensity={70} distance={34} decay={1.7} />
      {/* Soft warm glow from below, so the hole has depth. */}
      <pointLight ref={fill} color="#e8a36a" intensity={40} distance={55} decay={1.6} />
      {/* Key on the bottom-hole assembly: a cool rim from the side, so the
          steel and the cutters catch light against the dark rock. */}
      <pointLight position={[1.9, -bitMd + 8, 0.6]} color="#dfe8f2" intensity={60} distance={22} decay={1.6} />
      <pointLight position={[-1.9, -bitMd + 4, -0.6]} color="#ffd2a0" intensity={40} distance={16} decay={1.6} />
      <pointLight position={[0.4, -bitMd + 1.2, 1.9]} color="#ffe2c0" intensity={30} distance={10} decay={1.6} />
      <MudFlow bitMd={bitMd} />
      {intervals.map((c) => (
        <Wall key={c.name} top={c.top} base={c.base} tex={c.tex} tint={c.tint} />
      ))}
      <Contacts />
      <DrillString bitMd={bitMd} />
      <Cuttings bitMd={bitMd} />
      {/* Bottom of the hole: rock face under the bit */}
      <mesh position={[0, -bitMd - 0.15, 0]} rotation-x={-Math.PI / 2}>
        <circleGeometry args={[HOLE_R * 1.1, 48]} />
        <meshStandardMaterial color="#6a4632" roughness={1} />
      </mesh>
    </group>
  );
}

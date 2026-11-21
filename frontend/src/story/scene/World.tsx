import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import * as THREE from 'three';
import { loadBasin } from '../terrain';
import { Events, Fence, Subsurface, Terrain, Wells } from './Basin';
import { Borehole } from './Borehole';
import { Reports } from './Reports';
import { Surround, SurroundGate } from './Surround';
import { createState, updateState, type StoryState } from './state';
import { POINTER } from '../pointer';

// Suspend rendering until the real basin data (elevation, wells) is
// decoded; the satellite textures load through useLoader inside Terrain.
let basinPromise: Promise<unknown> | null = null;
let basinReady = false;
function BasinGate({ children }: { children: React.ReactNode }) {
  if (!basinReady) {
    basinPromise ??= loadBasin().then(() => {
      basinReady = true;
    });
    throw basinPromise;
  }
  return <>{children}</>;
}

// The story's 3D world: one canvas, one continuous scene. The DOM page
// owns the clock and passes (t, phase index, phase progress) in; this
// component turns that into scene state every frame.

export interface WorldClock {
  t: number;
  index: number;
  p: number;
}

/**
 * Sun direction: golden hour into early dusk, low in the west-north-west
 * (late-afternoon sun in Assam). Shared by the sky and the directional light.
 */
const tmp = new THREE.Vector3();
const bgUnder = new THREE.Color();
function sunDir(_night: number, out: THREE.Vector3) {
  // Clear mid-morning daylight from the south-east (~35° up): soft, even
  // light with long enough shadows to model the relief, as in aerial
  // survey imagery.
  return out.setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - 35), THREE.MathUtils.degToRad(140));
}

/**
 * Sky: a high-altitude gradient (deep navy at the zenith, bright blue,
 * then a luminous white haze band sitting on the horizon), the look of
 * aerial/orbital photography. Follows the camera so the horizon band is
 * always where the land meets the sky; its colour also drives the fog,
 * so distant terrain dissolves into exactly the same white haze.
 */
export const HAZE = new THREE.Color('#dbe8f4');
function DuskSky({ state }: { state: React.MutableRefObject<StoryState> }) {
  const { camera } = useThree();
  const mesh = useRef<THREE.Mesh>(null);
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        uniforms: { uHaze: { value: HAZE }, uHorizon: { value: 0 } },
        vertexShader: /* glsl */ `
          varying vec3 vDir;
          void main() {
            vDir = normalize(position);
            vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            gl_Position = p.xyww;
          }`,
        fragmentShader: /* glsl */ `
          uniform vec3 uHaze;
          uniform float uHorizon;
          varying vec3 vDir;
          void main() {
            float h = vDir.y - uHorizon;
            vec3 zenith = vec3(0.012, 0.045, 0.17);
            vec3 blue = vec3(0.07, 0.26, 0.62);
            vec3 col = mix(blue, zenith, smoothstep(0.08, 0.55, h));
            // the luminous haze band on the horizon
            col = mix(uHaze, col, smoothstep(-0.005, 0.11, h));
            // below the horizon line, stay in haze (land covers it anyway)
            if (h < 0.0) col = uHaze;
            gl_FragColor = vec4(col, 1.0);
            #include <colorspace_fragment>
          }`,
      }),
    [],
  );
  useFrame(() => {
    if (!mesh.current) return;
    mesh.current.position.copy(camera.position);
    // From altitude the horizon dips (Earth's curvature), so lower the band.
    mat.uniforms.uHorizon.value = -Math.min(0.06, Math.max(0, camera.position.y) * 0.0025);
    mesh.current.visible = state.current.cutaway < 0.5;
  });
  return (
    <mesh ref={mesh} material={mat} renderOrder={-1} frustumCulled={false}>
      <sphereGeometry args={[2500, 32, 16]} />
    </mesh>
  );
}

function Lights({ state }: { state: React.MutableRefObject<StoryState> }) {
  const sun = useRef<THREE.DirectionalLight>(null);
  const hemi = useRef<THREE.HemisphereLight>(null);
  const { scene } = useThree();
  useEffect(() => {
    scene.fog = new THREE.FogExp2('#b8c4cf', 0.02);
    return () => {
      scene.fog = null;
    };
  }, [scene]);
  useFrame(() => {
    const s = state.current;
    const n = s.night;
    if (sun.current) {
      sun.current.intensity = 2.6;
      // Light comes from the same direction as the sun drawn in the sky,
      // and the shadow camera stays centred on what we're looking at.
      sunDir(n, tmp);
      sun.current.target.position.set(s.camLook.x, 0, s.camLook.z);
      sun.current.position.set(s.camLook.x + tmp.x * 80, tmp.y * 80, s.camLook.z + tmp.z * 80);
      sun.current.target.updateMatrixWorld();
    }
    void n;
    if (hemi.current) hemi.current.intensity = 1.5;
    let fog = scene.fog as THREE.FogExp2 | null;
    if (!fog || !(fog as THREE.FogExp2).isFogExp2) fog = scene.fog = new THREE.FogExp2('#dbe8f4', 0.02);
    // Aerial perspective into the sky's own white haze band: near land
    // keeps its colour, distant ranges fade to haze.
    fog.color.copy(HAZE);
    const alt = Math.max(0, s.camPos.y);
    fog.density = THREE.MathUtils.lerp(0.012, 0.0028, Math.min(1, alt / 12) ** 0.5);
    // In the correlation phase the land becomes a veil over the subsurface;
    // haze there would just wash it out.
    fog.density *= 1 - 0.85 * s.cutaway;
    scene.background = s.cutaway > 0.05 ? bgUnder.setRGB(0.03, 0.035, 0.04) : null;
  });
  return (
    <>
      {/* Low warm sun from the west: long shadows across the plain. */}
      {/* Shadows matter only up close (the rig on its pad), so the shadow
          camera covers 600 m around what we look at; beyond that, terrain
          relief is shaded by its normals. */}
      <directionalLight
        ref={sun}
        color="#fff4e6"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-0.3}
        shadow-camera-right={0.3}
        shadow-camera-top={0.3}
        shadow-camera-bottom={-0.3}
        shadow-camera-near={1}
        shadow-camera-far={160}
        shadow-bias={-0.0002}
        shadow-normalBias={0.0004}
      />
      <hemisphereLight ref={hemi} args={['#cfe0f2', '#5a5444', 1.5]} />
    </>
  );
}

function CameraDriver({ state }: { state: React.MutableRefObject<StoryState> }) {
  const { camera } = useThree();
  const look = useRef(new THREE.Vector3());
  const ptr = useRef({ x: 0, y: 0 });
  const first = useRef(true);
  useFrame((_, dt) => {
    const s = state.current;
    const pc0 = camera as THREE.PerspectiveCamera;
    // Surface camera range (the hole sets its own near/far).
    if (pc0.far !== 3000) {
      pc0.near = 0.0008;
      pc0.far = 3000;
      first.current = true;
    }
    // A short smoothing on top of the scripted path so phase seams (and
    // seeks) never jump.
    const k = first.current ? 1 : 1 - Math.exp(-dt * 3.2);
    first.current = false;
    camera.position.lerp(s.camPos, k);
    look.current.lerp(s.camLook, k);
    // A faint breath, proportional to how far away we look: two slow,
    // incommensurate sines per axis so it never visibly repeats.
    const dist = camera.position.distanceTo(look.current);
    const T = s.time;
    const bx = Math.sin(T * 0.31) * 0.6 + Math.sin(T * 0.53 + 1.3) * 0.4;
    const by = Math.sin(T * 0.23 + 0.7) * 0.6 + Math.sin(T * 0.41 + 2.1) * 0.4;
    // Cursor parallax, eased: under 1% of the view distance.
    ptr.current.x += (POINTER.x - ptr.current.x) * Math.min(1, dt * 1.5);
    ptr.current.y += (POINTER.y - ptr.current.y) * Math.min(1, dt * 1.5);
    const b = new THREE.Vector3(
      (bx * 0.0035 + ptr.current.x * 0.008) * dist,
      (by * 0.0025 - ptr.current.y * 0.005) * dist,
      0,
    ).applyQuaternion(camera.quaternion);
    camera.lookAt(look.current.clone().add(b));
    const pc = camera as THREE.PerspectiveCamera;
    pc.fov += (s.fov - pc.fov) * k;
    pc.updateProjectionMatrix();
  });
  return null;
}

/** Flags the document once the real scene has drawn a few frames (used by the frame-capture dev script). */
function Rendered() {
  const n = useRef(0);
  useFrame(() => {
    n.current += 1;
    if (n.current === 4) document.documentElement.dataset.storyRendered = '1';
  });
  return null;
}

function Driver({ clock, state }: { clock: React.MutableRefObject<WorldClock>; state: React.MutableRefObject<StoryState> }) {
  const get = useThree((s) => s.get);
  useEffect(() => {
    // Dev only: expose the scene to scripts/scene-probe.mjs.
    if (import.meta.env.DEV) (window as unknown as { __story: unknown }).__story = { get, state, THREE };
  }, [get, state]);
  useFrame(() => {
    const c = clock.current;
    updateState(state.current, c.t, c.index, c.p);
  }, -2);
  return null;
}

// ---------------------------------------------------------------------------
// Post: grain, vignette, soft bloom on lights, gentle grade. One pass.
// ---------------------------------------------------------------------------
// Cinematic look (one pass): anamorphic streak flares on bright lights,
// soft bloom, a teal/orange large-format grade with lifted-then-crushed
// blacks, slight chromatic fringe at the edges, vignette and 35 mm grain.
const POST_FRAG = /* glsl */ `
  uniform sampler2D tScene;
  uniform vec2 uRes;
  uniform float uTime;
  varying vec2 vUv;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
  vec3 bright(vec2 uv, float th) { return max(texture2D(tScene, uv).rgb - th, 0.0); }
  void main() {
    vec2 uv = vUv;
    vec2 c = uv - 0.5;
    float r2 = dot(c, c);
    // Lens: faint chromatic fringe toward the frame edge.
    float ca = 0.0012 * r2 * 4.0;
    vec3 col;
    col.r = texture2D(tScene, uv + c * ca).r;
    col.g = texture2D(tScene, uv).g;
    col.b = texture2D(tScene, uv - c * ca).b;
    // Bloom: sparse ring, lights only.
    vec3 b = vec3(0.0);
    for (int i = 0; i < 8; i++) {
      float a = float(i) * 0.7854;
      for (int j = 1; j <= 3; j++) {
        vec2 o = vec2(cos(a), sin(a)) * float(j * j) * 4.0 / uRes;
        b += bright(uv + o, 0.9);
      }
    }
    col += b / 24.0 * 1.2;
    // Clean, photographic grade (aerial/IMAX look): a gentle S-curve,
    // slightly cool, a light vignette, and only a trace of grain.
    float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
    col = mix(vec3(l), col, 1.05);
    col *= mix(1.0, 0.8, smoothstep(0.12, 0.7, r2 * 1.3));
    float g = hash(uv * uRes + fract(uTime * 11.3) * 113.0) - 0.5;
    col += g * 0.006;
    gl_FragColor = vec4(max(col, 0.0), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

function Post() {
  const { gl, size, scene, camera } = useThree();
  const target = useMemo(() => new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }), []);
  const quad = useMemo(() => {
    const m = new THREE.ShaderMaterial({
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader: POST_FRAG,
      uniforms: { tScene: { value: target.texture }, uRes: { value: new THREE.Vector2() }, uTime: { value: 0 } },
      depthTest: false,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), m);
    mesh.frustumCulled = false;
    const s = new THREE.Scene();
    s.add(mesh);
    return { scene: s, m, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  }, [target]);
  useEffect(() => {
    const dpr = gl.getPixelRatio();
    target.setSize(Math.floor(size.width * dpr), Math.floor(size.height * dpr));
    quad.m.uniforms.uRes.value.set(size.width * dpr, size.height * dpr);
  }, [gl, size, target, quad]);
  useEffect(() => () => target.dispose(), [target]);
  useFrame(({ clock }) => {
    quad.m.uniforms.uTime.value = clock.elapsedTime;
    gl.setRenderTarget(target);
    gl.clear();
    gl.render(scene, camera);
    gl.setRenderTarget(null);
    gl.render(quad.scene, quad.cam);
  }, 1);
  return null;
}

/**
 * Mounts exactly one world at a time: the basin (surface) or the inside
 * of the borehole. Each is a separate scene graph, so the GPU only ever
 * draws what can be seen. Both stay loaded (textures cached), so the
 * switch, hidden under a dip to black, is instant.
 */
function Worlds({ state, clock }: { state: React.MutableRefObject<StoryState>; clock: React.MutableRefObject<WorldClock> }) {
  const [world, setWorld] = useState<'surface' | 'hole'>('surface');
  const surface = useRef<THREE.Group>(null);
  const hole = useRef<THREE.Group>(null);
  const { scene } = useThree();
  useFrame(() => {
    const w = state.current.world;
    if (w !== world) setWorld(w);
    if (surface.current) surface.current.visible = w === 'surface';
    if (hole.current) hole.current.visible = w === 'hole';
  });
  useEffect(() => {
    // The hole has its own fog/background; the surface has the sky's.
    if (world === 'hole') {
      scene.fog = new THREE.FogExp2('#060403', 0.022);
      scene.background = new THREE.Color('#030202');
    } else {
      scene.fog = new THREE.FogExp2('#b8c4cf', 0.012);
      scene.background = null;
    }
  }, [world, scene]);
  return (
    <>
      <Driver clock={clock} state={state} />
      <group ref={surface}>
        {world === 'surface' && (
          <>
            <DuskSky state={state} />
            <Lights state={state} />
            <CameraDriver state={state} />
          </>
        )}
        <SurroundGate>
          <Surround state={state} />
        </SurroundGate>
        <Terrain state={state} />
        <Wells state={state} />
        <Subsurface state={state} />
        <Fence state={state} />
        <Events state={state} />
        <Reports state={state} />
      </group>
      <group ref={hole}>
        {/* Mounted only while in use, so it never touches the camera,
            fog or lights of the surface world. Its textures stay cached. */}
        {world === 'hole' && <Borehole state={state} />}
      </group>
      <Rendered />
    </>
  );
}

/** Fade to black between worlds (and cover the first frames while loading). */
function Dip({ state }: { state: React.MutableRefObject<StoryState> }) {
  const mat = useMemo(() => new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: 0, depthTest: false, depthWrite: false, toneMapped: false }), []);
  const { camera } = useThree();
  const mesh = useRef<THREE.Mesh>(null);
  useFrame(() => {
    mat.opacity = state.current.dip;
    if (mesh.current) {
      mesh.current.position.copy(camera.position);
      mesh.current.quaternion.copy(camera.quaternion);
      mesh.current.translateZ(-0.01);
      mesh.current.visible = mat.opacity > 0.001;
    }
  });
  return (
    <mesh ref={mesh} material={mat} renderOrder={999} frustumCulled={false}>
      <planeGeometry args={[1, 1]} />
    </mesh>
  );
}

export function World({ clock, lowPower }: { clock: React.MutableRefObject<WorldClock>; lowPower: boolean }) {
  const state = useRef<StoryState>(createState());
  const [dpr, setDpr] = useState(lowPower ? 1 : 1.5);
  return (
    <Canvas
      className="story-canvas"
      dpr={dpr}
      shadows={!lowPower ? 'soft' : false}
      gl={{ antialias: false, powerPreference: 'high-performance', stencil: false }}
      camera={{ position: [-1.2, 0.75, 0.95], fov: 32, near: 0.0008, far: 3000 }}
      onCreated={({ gl }) => {
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 1.0;
        gl.outputColorSpace = THREE.SRGBColorSpace;
      }}
    >
      {/* Keep it smooth: drop resolution if frames run slow, raise it back
          when there's headroom (between 0.75x and the starting ratio). */}
      <PerformanceMonitor onDecline={() => setDpr((d) => Math.max(0.75, d - 0.25))} onIncline={() => setDpr((d) => Math.min(lowPower ? 1 : 1.5, d + 0.25))} />
      <Suspense fallback={null}>
        <BasinGate>
          <Worlds state={state} clock={clock} />
        </BasinGate>
      </Suspense>
      <Dip state={state} />
      {!lowPower && <Post />}
    </Canvas>
  );
}

export default World;

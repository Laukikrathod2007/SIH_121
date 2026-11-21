import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { EarthScene } from './scenes/EarthScene';
import { RigScene } from './scenes/RigScene';
import { DescentScene } from './scenes/DescentScene';
import { OffsetsScene } from './scenes/OffsetsScene';
import { shotAt, type Shot } from './timeline';
import type { FilmClock } from './clock';

// One WebGL canvas for the whole film. Only the active shot's scene is
// mounted; all of them are cheap to mount because heavy assets (the rig
// GLB, textures) are cached after first use.
//
// Post: the scene renders into an offscreen target and a final full-screen
// pass adds the film look (grain, vignette, soft chromatic fringe, gentle
// highlight bloom and a teal/orange grade). Written as a single shader so
// the app doesn't need a postprocessing dependency.

const gradeVertex = /* glsl */ `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;
const gradeFragment = /* glsl */ `
  uniform sampler2D tScene;
  uniform vec2 uRes;
  uniform float uTime;
  uniform float uGrain;
  uniform float uWarm;
  varying vec2 vUv;

  float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

  vec3 sampleBloom(vec2 uv) {
    vec3 acc = vec3(0.0);
    float w = 0.0;
    for (int i = -3; i <= 3; i++) {
      for (int j = -3; j <= 3; j++) {
        vec2 o = vec2(float(i), float(j)) * 3.5 / uRes;
        vec3 c = texture2D(tScene, uv + o).rgb;
        float k = exp(-float(i*i + j*j) / 6.0);
        acc += max(c - 0.55, 0.0) * k;
        w += k;
      }
    }
    return acc / w;
  }

  void main() {
    vec2 uv = vUv;
    vec2 c = uv - 0.5;
    float r2 = dot(c, c);

    // Lens: faint chromatic fringe toward the edges.
    float ca = 0.0016 + r2 * 0.006;
    vec3 col;
    col.r = texture2D(tScene, uv + c * ca).r;
    col.g = texture2D(tScene, uv).g;
    col.b = texture2D(tScene, uv - c * ca).b;

    // Highlight bloom.
    col += sampleBloom(uv) * 1.5;

    // Grade: lift shadows toward teal, push highlights toward warm.
    float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
    vec3 shadowTint = vec3(0.86, 0.98, 1.08);
    vec3 highTint = mix(vec3(1.0), vec3(1.08, 1.0, 0.9), uWarm);
    col *= mix(shadowTint, highTint, smoothstep(0.05, 0.6, lum));

    // Vignette.
    col *= mix(1.0, 0.32, smoothstep(0.08, 0.62, r2 * 1.6));

    // Grain: animated, luminance-weighted (applied in linear light, before
    // tone mapping, so it sits in the shadows like real stock).
    float g = hash(uv * uRes + fract(uTime * 13.7) * 100.0) - 0.5;
    col += g * uGrain * (0.25 + 0.5 * (1.0 - smoothstep(0.0, 0.5, lum)));

    gl_FragColor = vec4(max(col, 0.0), 1.0);
    // The scene was rendered linear into the target; apply the renderer's
    // ACES tone mapping and sRGB output here, on the way to the screen.
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

/** Renders the scene to a target, then draws the graded result. */
function FilmLook({ warm }: { warm: number }) {
  const { gl, size, scene, camera } = useThree();
  const target = useMemo(() => {
    const t = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
    t.texture.colorSpace = THREE.LinearSRGBColorSpace;
    return t;
  }, []);
  const quad = useMemo(() => {
    const m = new THREE.ShaderMaterial({
      vertexShader: gradeVertex,
      fragmentShader: gradeFragment,
      uniforms: {
        tScene: { value: target.texture },
        uRes: { value: new THREE.Vector2(1, 1) },
        uTime: { value: 0 },
        uGrain: { value: 0.03 },
        uWarm: { value: 0 },
      },
      depthTest: false,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), m);
    mesh.frustumCulled = false;
    const s = new THREE.Scene();
    s.add(mesh);
    return { scene: s, material: m, camera: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  }, [target]);

  useEffect(() => {
    const dpr = gl.getPixelRatio();
    target.setSize(Math.floor(size.width * dpr), Math.floor(size.height * dpr));
    quad.material.uniforms.uRes.value.set(size.width * dpr, size.height * dpr);
  }, [gl, size, target, quad]);

  useEffect(() => () => target.dispose(), [target]);

  // Priority 1 takes over rendering from R3F's default render loop.
  useFrame(({ clock }, delta) => {
    quad.material.uniforms.uTime.value = clock.elapsedTime;
    const u = quad.material.uniforms.uWarm;
    u.value += (warm - u.value) * Math.min(1, delta * 2);
    gl.setRenderTarget(target);
    gl.clear();
    gl.render(scene, camera);
    gl.setRenderTarget(null);
    gl.render(quad.scene, quad.camera);
  }, 1);
  return null;
}

/**
 * Marks the document once a shot's scene has actually rendered (it sits
 * inside the Suspense boundary, so it only mounts after the scene's assets
 * have loaded). Used by the frame-capture dev script; harmless otherwise.
 */
function RenderedMark({ id }: { id: string }) {
  const frames = useRef(0);
  useFrame(() => {
    frames.current += 1;
    if (frames.current === 3) document.documentElement.dataset.filmRendered = id;
  });
  return null;
}

/** Advances the film clock from the render loop. */
function Ticker({ clock, onShot }: { clock: FilmClock; onShot: (s: Shot) => void }) {
  const last = useRef<Shot | null>(null);
  useFrame((_, delta) => {
    const dt = Math.min(delta, 1 / 20);
    if (clock.playing) clock.t += dt;
    clock.dt = clock.playing ? dt : 0;
    const s = shotAt(clock.t);
    if (s !== last.current) {
      last.current = s;
      onShot(s);
    }
  }, -1);
  return null;
}

function SceneFor({ shot, clock }: { shot: Shot; clock: FilmClock }) {
  switch (shot.scene) {
    case 'earth':
      return <EarthScene clock={clock} shot={shot} />;
    case 'rig':
      return <RigScene clock={clock} shot={shot} />;
    case 'descent':
      return <DescentScene clock={clock} shot={shot} />;
    case 'offsets':
      return <OffsetsScene clock={clock} />;
    default:
      return <color attach="background" args={['#000000']} />;
  }
}

export function FilmCanvas({ clock, lowPower, onReady }: { clock: FilmClock; lowPower: boolean; onReady: () => void }) {
  const [shot, setShot] = useState<Shot>(() => shotAt(clock.t));
  const warm = shot.scene === 'rig' || (shot.scene === 'earth' && shot.variant === 'finale') ? 1 : shot.scene === 'descent' ? 0.7 : 0.2;

  return (
    <Canvas
      dpr={lowPower ? [1, 1] : [1, 1.75]}
      gl={{ antialias: false, powerPreference: 'high-performance', alpha: false }}
      camera={{ position: [0, 0, 10], fov: 35, near: 0.05, far: 2000 }}
      shadows={!lowPower}
      onCreated={({ gl }) => {
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 1.0;
        gl.outputColorSpace = THREE.SRGBColorSpace;
        onReady();
      }}
    >
      <Ticker clock={clock} onShot={setShot} />
      <Suspense fallback={null}>
        <SceneFor key={`${shot.scene}-${shot.variant}`} shot={shot} clock={clock} />
        <RenderedMark key={`mark-${shot.scene}-${shot.variant}`} id={`${shot.scene}-${shot.variant}`} />
      </Suspense>
      {!lowPower && <FilmLook warm={warm} />}
    </Canvas>
  );
}

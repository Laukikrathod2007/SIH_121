import React, { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { COLUMN_BASE_M, STRATA, grainTexture, glowTexture, mulberry32, strataTexture } from '../textures';
import { ACT, KOPILI_TOP_MD, bitMd, clamp, descentCamMd, easeInOut, lerp, smoothstep, type Shot } from '../timeline';
import type { FilmClock } from '../clock';

// BELOW. A slow fall through the rock column alongside the bit. The world
// is a cutaway: a thick cylinder of strata, the borehole running down its
// centre, the camera inside a half-open cut face. The only light is the
// bit's own lamp and faint volumetric shafts down the bore, as in a cave.
//
// Scale: 1 scene unit = 10 m, so the 3,200 m column is 320 units tall.

const U = 0.1; // scene units per metre
const RADIUS = 9;
const BORE = 0.35;

const yOf = (md: number) => -md * U;

// The detailed section around the bit. Everything above it uses one coarse
// texture for the whole column; this keeps bedding sharp where the camera
// lingers without a gigantic texture.
const DETAIL_TOP = 2700;

function RockSection({ top, base }: { top: number; base: number }) {
  const tex = strataTexture(top, base);
  const bump = useMemo(() => {
    const b = grainTexture().clone();
    b.needsUpdate = true;
    b.repeat.set(6, Math.max(2, (base - top) / 12));
    return b;
  }, [top, base]);
  const height = (base - top) * U;
  // The camera stands inside a cut chamber around the bore: the strata are
  // the inside face of the chamber wall, so whichever way it looks there is
  // rock behind the bit.
  return (
    <mesh position={[0, yOf(top) - height / 2, 0]}>
      <cylinderGeometry args={[RADIUS, RADIUS, height, 160, 1, true]} />
      <meshStandardMaterial map={tex} bumpMap={bump} bumpScale={0.6} roughness={0.95} metalness={0} side={THREE.BackSide} />
    </mesh>
  );
}

function RockColumn() {
  return (
    <>
      <RockSection top={0} base={DETAIL_TOP} />
      <RockSection top={DETAIL_TOP} base={COLUMN_BASE_M} />
    </>
  );
}

/**
 * Formation names float in the dark beside the bore as the camera passes
 * each contact, like depth marks in a mine shaft. Opacity follows the
 * camera's distance from the contact.
 */
function FormationLabels({ camMd }: { camMd: React.MutableRefObject<number> }) {
  const ref = useRef<THREE.Group>(null);
  const sprites = useMemo(
    () =>
      STRATA.map((s) => {
        const c = document.createElement('canvas');
        c.width = 1024;
        c.height = 128;
        const g = c.getContext('2d')!;
        g.font = '500 54px "JetBrains Mono", monospace';
        g.fillStyle = s.name === 'KOPILI' ? '#ffb38a' : '#eadfca';
        g.textBaseline = 'middle';
        g.fillText(s.name.split('').join(' '), 8, 64);
        const tex = new THREE.CanvasTexture(c);
        tex.colorSpace = THREE.SRGBColorSpace;
        return { s, tex };
      }),
    [],
  );
  useFrame(() => {
    ref.current?.children.forEach((c, i) => {
      const s = sprites[i].s;
      const d = camMd.current - s.top;
      // Visible as the camera approaches and passes the contact.
      const o = smoothstep(-90, -20, d) * (1 - smoothstep(25, 70, d));
      ((c as THREE.Sprite).material as THREE.SpriteMaterial).opacity = o * 0.85;
    });
  });
  return (
    <group ref={ref}>
      {sprites.map(({ s, tex }) => (
        <sprite key={s.name} position={[2.4, yOf(s.top) - 1.2, 1.4]} scale={[5.6, 0.7, 1]}>
          <spriteMaterial map={tex} transparent opacity={0} depthWrite={false} fog={false} />
        </sprite>
      ))}
    </group>
  );
}

/** Formation contacts as faint luminous rings, so each boundary reads. */
function Contacts({ clock }: { clock: FilmClock }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(() => {
    const y = yOf(bitMd(clock.t));
    ref.current?.children.forEach((c) => {
      const d = Math.abs(c.position.y - y);
      ((c as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity = 0.03 + 0.14 * Math.exp(-d / 6);
    });
  });
  return (
    <group ref={ref}>
      {STRATA.slice(1).map((s) => (
        <mesh key={s.name} position={[0, yOf(s.top), 0]} rotation-x={-Math.PI / 2}>
          <ringGeometry args={[BORE * 1.5, RADIUS * 0.98, 96]} />
          <meshBasicMaterial color={s.name === 'KOPILI' ? '#ff7a3d' : '#d9c7a3'} transparent opacity={0.1} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}

/** The drill string: casing above, open hole below, and the bit. */
function Wellbore({ clock, lampIntensity }: { clock: FilmClock; lampIntensity: number }) {
  const string = useRef<THREE.Mesh>(null);
  const bit = useRef<THREE.Group>(null);
  const lamp = useRef<THREE.PointLight>(null);
  const glow = glowTexture();
  useFrame(() => {
    const md = bitMd(clock.t);
    const y = yOf(md);
    if (string.current) {
      string.current.scale.y = Math.max(0.001, -y);
      string.current.position.y = y / 2;
      string.current.rotation.y = clock.t * 2.4;
    }
    if (bit.current) {
      bit.current.position.y = y;
      bit.current.rotation.y = clock.t * 9;
    }
    if (lamp.current) lamp.current.position.set(0.9, y + 0.6, 1.2);
  });
  const cuttersGeo = useMemo(() => new THREE.ConeGeometry(0.06, 0.12, 6), []);
  return (
    <>
      {/* Open-hole wall, slightly darker than the rock. */}
      <mesh position={[0, -(COLUMN_BASE_M * U) / 2, 0]}>
        <cylinderGeometry args={[BORE, BORE, COLUMN_BASE_M * U, 24, 1, true]} />
        <meshStandardMaterial color="#120f0d" roughness={1} side={THREE.BackSide} />
      </mesh>
      {/* Drill pipe, a unit-height cylinder scaled to the current depth. */}
      <mesh ref={string}>
        <cylinderGeometry args={[0.12, 0.12, 1, 20]} />
        <meshStandardMaterial color="#8d97a3" metalness={0.9} roughness={0.32} />
      </mesh>
      <group ref={bit}>
        <mesh position={[0, 0.18, 0]}>
          <cylinderGeometry args={[0.3, 0.22, 0.36, 24]} />
          <meshStandardMaterial color="#c7a24a" metalness={0.85} roughness={0.3} />
        </mesh>
        {Array.from({ length: 10 }, (_, i) => {
          const a = (i / 10) * Math.PI * 2;
          return (
            <mesh key={i} geometry={cuttersGeo} position={[Math.cos(a) * 0.2, -0.02, Math.sin(a) * 0.2]} rotation-x={Math.PI}>
              <meshStandardMaterial color="#e8eef5" metalness={0.6} roughness={0.25} emissive="#2b3440" />
            </mesh>
          );
        })}
        <sprite position={[0, -0.05, 0]} scale={1.6}>
          <spriteMaterial map={glow} color="#ffb070" transparent opacity={0.5} blending={THREE.AdditiveBlending} depthWrite={false} />
        </sprite>
      </group>
      {/* The bit's lamp: the brightest light down here. */}
      <pointLight ref={lamp} color="#ffc48a" intensity={lampIntensity} distance={30} decay={2} />
    </>
  );
}

/** Dust motes drifting in the lamp light. */
function Motes({ clock }: { clock: FilmClock }) {
  const N = 500;
  const { geo, base } = useMemo(() => {
    const rnd = mulberry32(51);
    const base = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const a = rnd() * Math.PI * 2;
      const r = 1 + rnd() * 7;
      base.set([Math.cos(a) * r, rnd() * 30 - 15, Math.sin(a) * r], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
    return { geo: g, base };
  }, []);
  useFrame(() => {
    const y0 = yOf(bitMd(clock.t));
    const arr = geo.attributes.position.array as Float32Array;
    for (let i = 0; i < N; i++) {
      arr[i * 3] = base[i * 3] + Math.sin(clock.t * 0.3 + i) * 0.2;
      arr[i * 3 + 1] = y0 + (((base[i * 3 + 1] + clock.t * 0.25 + 15) % 30) - 15);
      arr[i * 3 + 2] = base[i * 3 + 2] + Math.cos(clock.t * 0.27 + i) * 0.2;
    }
    geo.attributes.position.needsUpdate = true;
  });
  return (
    <points geometry={geo}>
      <pointsMaterial map={glowTexture()} color="#e9c9a0" size={0.09} transparent opacity={0.55} depthWrite={false} blending={THREE.AdditiveBlending} />
    </points>
  );
}

/**
 * The kick, as the offset well's driller saw it: a pressure front rising
 * from the Kopili. Only appears at the decision beat; here it's contained,
 * because the crew weighted up in time.
 */
function PressureFront({ clock, shot }: { clock: FilmClock; shot: Shot }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(() => {
    if (!ref.current) return;
    const lt = clock.t - shot.start;
    const crossing = smoothstep(0.6, 3.2, lt);
    const settle = 1 - smoothstep(4.5, 7.2, lt);
    const s = 1 + crossing * 2.8;
    ref.current.scale.set(s, 1, s);
    ref.current.position.y = yOf(KOPILI_TOP_MD) - 0.4;
    (ref.current.material as THREE.MeshBasicMaterial).opacity = 0.32 * crossing * settle + 0.03;
  });
  return (
    <mesh ref={ref} rotation-x={-Math.PI / 2}>
      <ringGeometry args={[BORE * 1.2, BORE * 3.2, 64]} />
      <meshBasicMaterial color="#ff6a2b" transparent opacity={0} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} depthWrite={false} />
    </mesh>
  );
}

export function DescentScene({ clock, shot }: { clock: FilmClock; shot: Shot }) {
  const { camera, scene } = useThree();
  const camMd = useRef(0);
  const fill = useRef<THREE.PointLight>(null);

  React.useEffect(() => {
    scene.fog = new THREE.FogExp2('#060504', 0.02);
    return () => {
      scene.fog = null;
    };
  }, [scene]);

  useFrame(() => {
    const t = clock.t;
    const pc = camera as THREE.PerspectiveCamera;
    if (shot.variant === 'decision') {
      // Low, almost level with the contact: the bit crosses into the Kopili.
      const p = easeInOut(clamp((t - shot.start) / (shot.end - shot.start)));
      const a = lerp(0.35, 0.05, p);
      const r = lerp(4.2, 3.1, p);
      camera.position.set(Math.sin(a) * r, yOf(KOPILI_TOP_MD) + lerp(0.6, 0.15, p), Math.cos(a) * r);
      camera.lookAt(0, yOf(bitMd(t)) - 0.1, 0);
      pc.fov = lerp(30, 26, p);
    } else {
      // A fall down the bore beside the drill string, through every
      // formation above the bit, slowing hard to arrive just above it.
      const p = clamp((t - ACT.descent.start) / (ACT.descent.end - ACT.descent.start));
      const md = descentCamMd(t);
      const a = 0.9 - p * 2.2;
      const r = lerp(3.6, 4.4, smoothstep(0.7, 1, p));
      camera.position.set(Math.sin(a) * r, yOf(md), Math.cos(a) * r);
      // Looking down the shaft while falling; level on the bit at the end.
      const lookDown = lerp(22, 1.5, smoothstep(0.55, 1, p));
      camera.lookAt(0, yOf(md) - lookDown, 0);
      pc.fov = lerp(48, 32, smoothstep(0.5, 1, p));
    }
    camMd.current = shot.variant === 'decision' ? KOPILI_TOP_MD : descentCamMd(t);
    // A soft fill that travels with the camera, so the walls it passes
    // aren't pure black far above the bit's lamp.
    fill.current?.position.copy(camera.position);
    camera.up.set(0, 1, 0);
    pc.near = 0.05;
    pc.updateProjectionMatrix();
  });

  return (
    <>
      <color attach="background" args={['#030303']} />
      <ambientLight intensity={0.05} color="#ffd9b0" />
      <hemisphereLight args={['#4a3a2a', '#0a0705', 0.12]} />
      <pointLight ref={fill} color="#e6cfae" intensity={shot.variant === 'decision' ? 6 : 45} distance={22} decay={1.8} />
      <RockColumn />
      <Contacts clock={clock} />
      <FormationLabels camMd={camMd} />
      {/* At the crossing the camera sits close to the bit, so its lamp is
          turned down there to keep the frame from blowing out. */}
      <Wellbore clock={clock} lampIntensity={shot.variant === 'decision' ? 14 : 160} />
      <Motes clock={clock} />
      {shot.variant === 'decision' && <PressureFront clock={clock} shot={shot} />}
    </>
  );
}

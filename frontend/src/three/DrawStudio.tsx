import { Suspense, useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Text, Float, Sparkles, Environment } from '@react-three/drei'
import * as THREE from 'three'

const reducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

interface DrawStudioProps {
  numbers: number[]
  accentColor?: string
  celebrate?: boolean
  /** Height of the canvas container. */
  height?: number | string
}

interface BallProps {
  number: number
  position: [number, number, number]
  reduced: boolean
  seed: number
}

function BallSphere({ number, position, reduced, seed }: BallProps) {
  const group = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (reduced || !group.current) return
    const t = state.clock.elapsedTime
    group.current.rotation.y = Math.sin(t * 0.3 + seed) * 0.4
    group.current.rotation.x = Math.cos(t * 0.22 + seed) * 0.15
  })

  const sphere = (
    <group ref={group} position={position}>
      <mesh castShadow>
        <sphereGeometry args={[0.62, 48, 48]} />
        <meshStandardMaterial
          color={'#f5f0e6'}
          roughness={0.32}
          metalness={0.05}
          envMapIntensity={0.7}
        />
      </mesh>
      {/* Numeral floats just off the surface, always front-ish */}
      <Text
        position={[0, 0, 0.64]}
        fontSize={0.5}
        color={'#0a1410'}
        anchorX="center"
        anchorY="middle"
        fontWeight={700}
      >
        {String(number)}
      </Text>
    </group>
  )

  if (reduced) return sphere
  return (
    <Float speed={1.4} rotationIntensity={0.25} floatIntensity={0.9} floatingRange={[-0.15, 0.15]}>
      {sphere}
    </Float>
  )
}

function Scene({ numbers, accentColor, celebrate, reduced }: {
  numbers: number[]
  accentColor: string
  celebrate: boolean
  reduced: boolean
}) {
  const picks = useMemo(() => numbers.slice(0, 12), [numbers])

  const positions = useMemo<[number, number, number][]>(() => {
    const n = Math.max(picks.length, 1)
    return picks.map((_, i) => {
      // Spread across a gentle arc.
      const spread = Math.min(n, 6)
      const x = (i - (n - 1) / 2) * (7 / spread)
      const y = Math.sin(i * 1.7) * 0.5
      const z = Math.cos(i * 0.9) * 0.6
      return [x, y, z]
    })
  }, [picks])

  return (
    <>
      <color attach="background" args={['#0a1410']} />
      <fog attach="fog" args={['#0a1410', 6, 16]} />
      <ambientLight intensity={0.35} />
      <spotLight
        position={[4, 8, 6]}
        angle={0.5}
        penumbra={0.8}
        intensity={2.4}
        color={'#ffffff'}
        castShadow
      />
      <pointLight position={[-6, -2, 4]} intensity={1.1} color={accentColor} />
      <Environment preset="night" />

      {positions.map((pos, i) => (
        <BallSphere
          key={i}
          number={picks[i]}
          position={pos}
          reduced={reduced}
          seed={i * 1.3}
        />
      ))}

      {celebrate && !reduced && (
        <Sparkles
          count={60}
          scale={[10, 5, 4]}
          size={4}
          speed={0.4}
          opacity={0.7}
          color={'#e8b455'}
        />
      )}
    </>
  )
}

export default function DrawStudio({
  numbers,
  accentColor = '#5fe3b0',
  celebrate = false,
  height = 320,
}: DrawStudioProps) {
  const reduced = reducedMotion()
  const safeNumbers = numbers.length ? numbers : [7, 11, 23, 42, 56]

  return (
    <div style={{ width: '100%', height, position: 'relative' }}>
      <Canvas
        shadows
        dpr={[1, 1.8]}
        camera={{ position: [0, 0, 9], fov: 42 }}
        frameloop={reduced ? 'demand' : 'always'}
        gl={{ antialias: true, alpha: false }}
      >
        <Suspense fallback={null}>
          <Scene
            numbers={safeNumbers}
            accentColor={accentColor}
            celebrate={celebrate}
            reduced={reduced}
          />
        </Suspense>
      </Canvas>
    </div>
  )
}

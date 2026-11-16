import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import clsx from 'clsx'
import type { SensorReading, ThresholdValue } from '../../api/types'

// Meshes come from cad/field_unit.py (CAD units: mm, Z up), packed by cad/pack_viewer.py.
const MODEL_URL = '/field-unit/models.json'
const SKIP = new Set(['adapter', 'cable_usb'])

// Sensor anchor points in three.js space (CAD x, z, -y) where each callout is pinned.
const ANCHORS = {
  dht22: new THREE.Vector3(63, 474, 0),
  moisture: new THREE.Vector3(55, 233, -55),
  ph: new THREE.Vector3(55, 268, 55),
} as const
type AnchorId = keyof typeof ANCHORS

const HIGHLIGHT: Record<AnchorId, string[]> = {
  dht22: ['dht22', 'shield'],
  moisture: ['moisture_probe', 'moisture_pins'],
  ph: ['ph_probe', 'ph_bulb'],
}

interface Part { name: string; color: string; stl_base64: string }

function decode(b64: string) {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return bytes.buffer
}

function fmt(v: number | null | undefined, digits = 1) {
  return v == null ? '—' : v.toFixed(digits)
}

function tone(t?: ThresholdValue) {
  if (!t || t.status === 'UNKNOWN') return 'idle'
  return t.status === 'OPTIMAL' ? 'ok' : 'warn'
}

interface Props {
  reading?: SensorReading
}

export default function FieldUnitHero({ reading }: Props) {
  const mountRef = useRef<HTMLDivElement>(null)
  const labelRefs = useRef<Partial<Record<AnchorId, HTMLDivElement | null>>>({})
  const meshesRef = useRef<Record<string, THREE.Mesh>>({})
  const [state, setState] = useState<'loading' | 'ready' | 'missing'>('loading')
  const [hover, setHover] = useState<AnchorId | null>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(28, 1, 10, 8000)
    camera.position.set(1500, 900, 1380)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(55, 345, 0)
    controls.enableZoom = false
    controls.enablePan = false
    controls.enableDamping = true
    controls.autoRotate = !reduceMotion
    controls.autoRotateSpeed = 0.55
    controls.minPolarAngle = Math.PI * 0.25
    controls.maxPolarAngle = Math.PI * 0.52
    controls.update()

    scene.add(new THREE.HemisphereLight(0xffffff, 0xb9c2b4, 1.05))
    const sun = new THREE.DirectionalLight(0xffffff, 1.1)
    sun.position.set(500, 1100, 700)
    scene.add(sun)
    const rim = new THREE.DirectionalLight(0xe6f7ea, 0.45)
    rim.position.set(-700, 400, -600)
    scene.add(rim)

    // Soft contact shadow under the pot
    const shadowTex = (() => {
      const c = document.createElement('canvas')
      c.width = c.height = 128
      const g = c.getContext('2d')!
      const grad = g.createRadialGradient(64, 64, 4, 64, 64, 64)
      grad.addColorStop(0, 'rgba(20,24,20,0.28)')
      grad.addColorStop(1, 'rgba(20,24,20,0)')
      g.fillStyle = grad
      g.fillRect(0, 0, 128, 128)
      return new THREE.CanvasTexture(c)
    })()
    const shadow = new THREE.Mesh(
      new THREE.PlaneGeometry(420, 420),
      new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false })
    )
    shadow.rotation.x = -Math.PI / 2
    shadow.position.set(20, 0.5, 0)
    scene.add(shadow)

    const model = new THREE.Group()
    model.rotation.x = -Math.PI / 2
    scene.add(model)

    let cancelled = false
    fetch(MODEL_URL)
      .then((r) => {
        if (!r.ok) throw new Error('missing')
        return r.json() as Promise<Part[]>
      })
      .then((parts) => {
        if (cancelled) return
        const loader = new STLLoader()
        for (const p of parts) {
          if (SKIP.has(p.name)) continue
          const geo = loader.parse(decode(p.stl_base64))
          const translucent = p.name === 'case_lid'
          const mat = new THREE.MeshStandardMaterial({
            color: p.color,
            roughness: 0.6,
            metalness: p.name === 'esp32_parts' ? 0.45 : 0.04,
            transparent: translucent,
            opacity: translucent ? 0.4 : 1,
            depthWrite: !translucent,
            side: THREE.DoubleSide,
          })
          const mesh = new THREE.Mesh(geo, mat)
          meshesRef.current[p.name] = mesh
          model.add(mesh)
        }
        setState('ready')
      })
      .catch(() => !cancelled && setState('missing'))

    const resize = () => {
      const w = mount.clientWidth
      const h = mount.clientHeight
      if (!w || !h) return
      renderer.setSize(w, h, false)
      renderer.domElement.style.width = '100%'
      renderer.domElement.style.height = '100%'
      camera.aspect = w / h
      // Keep the whole unit in frame on narrow cards
      camera.fov = w / h < 0.9 ? 33 : 28
      camera.updateProjectionMatrix()
    }
    const ro = new ResizeObserver(resize)
    ro.observe(mount)
    resize()

    const v = new THREE.Vector3()
    let raf = 0
    const loop = () => {
      controls.update()
      renderer.render(scene, camera)
      const w = mount.clientWidth
      const h = mount.clientHeight
      ;(Object.keys(ANCHORS) as AnchorId[]).forEach((id) => {
        const el = labelRefs.current[id]
        if (!el) return
        v.copy(ANCHORS[id]).project(camera)
        const visible = v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05
        el.style.opacity = visible ? '1' : '0'
        el.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px)`
      })
      raf = requestAnimationFrame(loop)
    }
    loop()

    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
      ro.disconnect()
      controls.dispose()
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh) {
          o.geometry.dispose()
          ;(o.material as THREE.Material).dispose()
        }
      })
      shadowTex.dispose()
      renderer.dispose()
      renderer.domElement.remove()
      meshesRef.current = {}
    }
  }, [])

  // Hovering a callout lights up the sensor it belongs to
  useEffect(() => {
    for (const [id, names] of Object.entries(HIGHLIGHT)) {
      for (const n of names) {
        const m = meshesRef.current[n]
        if (m) (m.material as THREE.MeshStandardMaterial).emissive.setHex(hover === id ? 0x1f6e35 : 0x000000)
      }
    }
  }, [hover, state])

  const t = reading?.threshold_status
  // The two soil probes sit at similar heights, so one label hangs below its probe to avoid collisions
  const callouts: Array<{ id: AnchorId; title: string; value: React.ReactNode; tone: string; below?: boolean }> = [
    {
      id: 'dht22',
      title: 'DHT22 · air',
      value: (
        <>
          {fmt(reading?.temperature)}°C <span className="text-faint">/</span> {fmt(reading?.humidity, 0)}%
        </>
      ),
      tone: [tone(t?.temperature), tone(t?.humidity)].includes('warn') ? 'warn' : tone(t?.temperature),
    },
    { id: 'moisture', title: 'Soil moisture', value: <>{fmt(reading?.moisture)}%</>, tone: tone(t?.moisture), below: true },
    { id: 'ph', title: 'Soil pH · relative', value: <>{fmt(reading?.ph, 2)}</>, tone: tone(t?.ph) },
  ]

  return (
    <div className="relative h-full min-h-[420px] overflow-hidden rounded-card bg-[radial-gradient(120%_90%_at_50%_30%,#FBFCFA_0%,#EEF1EB_55%,#E3E8E0_100%)]">
      <div ref={mountRef} className="absolute inset-0 z-0 cursor-grab active:cursor-grabbing" aria-label="3D model of the DeepCrop field unit. Drag to rotate." role="img" />

      {/* Callouts pinned to the sensors; positioned every frame from the 3D anchors */}
      <div className="pointer-events-none absolute inset-0 z-10">
        {state === 'ready' &&
          callouts.map((c) => (
            <div
              key={c.id}
              ref={(el) => (labelRefs.current[c.id] = el)}
              className="absolute left-0 top-0 transition-opacity duration-300"
              style={{ opacity: 0 }}
            >
              <div className={clsx('relative -translate-x-1/2', c.below ? 'pt-3' : '-translate-y-full pb-3')}>
                <button
                  type="button"
                  onMouseEnter={() => setHover(c.id)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(c.id)}
                  onBlur={() => setHover(null)}
                  className={clsx(
                    'pointer-events-auto whitespace-nowrap rounded-full px-3 py-1.5 text-left shadow-lift transition-colors',
                    c.tone === 'warn' ? 'bg-warn-field text-ink' : 'bg-card text-ink'
                  )}
                >
                  <span className={clsx('block text-[11px] font-medium leading-tight', c.tone === 'warn' ? 'text-warn' : 'text-muted')}>
                    {c.title}
                  </span>
                  <span className="num block text-sm font-semibold leading-tight">{c.value}</span>
                </button>
                <span
                  className={clsx(
                    'absolute left-1/2 h-2.5 w-2.5 -translate-x-1/2 rounded-full ring-2 ring-card',
                    c.below ? 'top-0 -translate-y-1/2' : 'bottom-0 translate-y-1/2',
                    c.tone === 'warn' ? 'bg-warn' : c.tone === 'ok' ? 'bg-leaf' : 'bg-ink'
                  )}
                />
              </div>
            </div>
          ))}
      </div>

      {state === 'loading' && (
        <p className="absolute inset-0 grid place-items-center text-sm text-muted">Loading the field unit…</p>
      )}
      {state === 'missing' && (
        <div className="absolute inset-0 grid place-items-center p-8 text-center">
          <div className="max-w-sm">
            <p className="font-semibold text-ink">3D model not built yet</p>
            <p className="mt-1 text-sm text-muted">
              Run <code className="rounded bg-tile px-1">cad/field_unit.py</code>, then{' '}
              <code className="rounded bg-tile px-1">cad/pack_viewer.py --frontend</code>, to generate the meshes.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

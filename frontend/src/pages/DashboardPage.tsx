import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowRight, Info, ScanLine } from 'lucide-react'
import clsx from 'clsx'
import { getLatestSensorReading, getSensorHistory, simulateSensors } from '../api/sensors'
import { getCropDetail } from '../api/crops'
import { getPlantCVHistory } from '../api/cv'
import { getRiskHistory, predictDiseaseRisk } from '../api/recommendations'
import type { CVPrediction, DiseaseRiskPrediction, SensorReading, ThresholdValue } from '../api/types'
import FieldUnitHero from '../components/dashboard/FieldUnitHero'
import DataSourceBadge from '../components/badges/DataSourceBadge'
import ModelStatusBadge from '../components/badges/ModelStatusBadge'
import ConfidenceGauge from '../components/ConfidenceGauge'
import { CROP_ID, PLANT_ID } from '../components/Layout'

type Scenario = 'optimal' | 'drought' | 'overwatered' | 'disease_risk' | 'random'

const SCENARIOS: Array<{ value: Scenario; label: string }> = [
  { value: 'optimal', label: 'Optimal' },
  { value: 'drought', label: 'Drought stress' },
  { value: 'overwatered', label: 'Overwatered' },
  { value: 'disease_risk', label: 'Disease-conducive' },
  { value: 'random', label: 'Random stress' },
]

const METRICS = [
  { key: 'temperature', label: 'Air temp', unit: '°C', digits: 1 },
  { key: 'moisture', label: 'Soil moisture', unit: '%', digits: 1 },
  { key: 'humidity', label: 'Humidity', unit: '%', digits: 0 },
  { key: 'ph', label: 'Soil pH', unit: 'rel.', digits: 2 },
] as const

const STATUS_TEXT: Record<ThresholdValue['status'], string> = {
  OPTIMAL: 'Optimal',
  LOW: 'Below range',
  HIGH: 'Above range',
  UNKNOWN: 'No range',
}

function timeAgo(iso?: string) {
  if (!iso) return ''
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return new Date(iso).toLocaleDateString()
}

type Band = { optimal_min: number; optimal_max: number }

// Dot-matrix history: one column per reading, filled dots = value height, amber when outside the optimal band
function DotHistory({ values, band }: { values: number[]; band?: Band }) {
  const ROWS = 4
  const COLS = 12
  const recent = values.slice(-COLS)
  if (recent.length < 2) return <div className="h-[22px]" aria-hidden="true" />
  const lo = Math.min(...recent, band?.optimal_min ?? Infinity)
  const hi = Math.max(...recent, band?.optimal_max ?? -Infinity)
  const span = hi - lo || 1
  return (
    <div className="flex h-[22px] items-end gap-[3px]" role="img" aria-label={`Last ${recent.length} readings`}>
      {Array.from({ length: COLS - recent.length }).map((_, i) => (
        <span key={`pad${i}`} className="w-[4px]" />
      ))}
      {recent.map((v, i) => {
        const filled = Math.max(1, Math.round(((v - lo) / span) * (ROWS - 1)) + 1)
        const out = band && (v < band.optimal_min || v > band.optimal_max)
        return (
          <span key={i} className="flex w-[4px] flex-col-reverse gap-[2px]">
            {Array.from({ length: ROWS }).map((_, r) => (
              <span
                key={r}
                className={clsx('h-[4px] w-[4px] rounded-full', r < filled ? (out ? 'bg-warn' : 'bg-leaf') : 'bg-line')}
              />
            ))}
          </span>
        )
      })}
    </div>
  )
}

function CardHeader({ id, title, aside }: { id: string; title: string; aside?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <h2 id={id} className="text-[19px] font-semibold tracking-display text-ink">{title}</h2>
      {aside}
    </div>
  )
}

/* ---------- Left column ---------- */

function ConditionsCard({
  reading,
  history,
  bands,
  isLoading,
}: {
  reading?: SensorReading
  history: SensorReading[]
  bands?: Record<string, Band>
  isLoading: boolean
}) {
  const qc = useQueryClient()
  const [scenario, setScenario] = useState<Scenario>('optimal')
  const sim = useMutation({
    mutationFn: () => simulateSensors({ crop_id: CROP_ID, plant_id: PLANT_ID, scenario, count: 1 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sensor-latest'] })
      qc.invalidateQueries({ queryKey: ['sensor-history'] })
    },
  })

  return (
    <section className="card flex flex-col gap-4 p-5" aria-labelledby="conditions-title">
      <div>
        <CardHeader id="conditions-title" title="Current conditions" aside={reading && <DataSourceBadge source={reading.data_source} />} />
        <p className="mt-0.5 text-sm text-muted">
          {reading ? `Last reading ${timeAgo(reading.timestamp)}` : isLoading ? 'Loading…' : 'No readings yet'}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        {METRICS.map((m) => {
          const value = reading?.[m.key] as number | null | undefined
          const t = reading?.threshold_status?.[m.key]
          const off = t && t.status !== 'OPTIMAL' && t.status !== 'UNKNOWN'
          return (
            <div key={m.key} className={clsx('rounded-tile px-3.5 py-3', off ? 'bg-warn-field' : 'bg-tile')}>
              <p className="text-[13px] font-medium text-muted">{m.label}</p>
              <p className="num mt-2 text-[36px] font-light leading-none tracking-display text-ink">
                {value == null ? '—' : value.toFixed(m.digits)}
                <span className="ml-0.5 text-base font-normal tracking-normal text-muted">{m.unit}</span>
              </p>
              <div className="mt-2.5">
                <DotHistory
                  values={history.map((r) => r[m.key]).filter((v): v is number => v != null)}
                  band={bands?.[m.key]}
                />
              </div>
              <p className={clsx('mt-1.5 flex items-center gap-1.5 text-xs font-semibold', off ? 'text-warn' : 'text-leaf-deep')}>
                {t ? (
                  <>
                    <span className={clsx('h-1.5 w-1.5 rounded-full', off ? 'bg-warn' : 'bg-leaf')} />
                    {STATUS_TEXT[t.status]}
                  </>
                ) : (
                  <span className="text-muted">Waiting</span>
                )}
              </p>
            </div>
          )
        })}
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="scenario" className="text-xs font-medium text-muted">
          Simulated scenario
        </label>
        <div className="flex gap-2">
          <select
            id="scenario"
            value={scenario}
            onChange={(e) => setScenario(e.target.value as Scenario)}
            className="min-w-0 flex-1 rounded-tile border-0 bg-tile px-3 py-2.5 text-sm font-medium text-ink"
          >
            {SCENARIOS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <button type="button" className="btn-primary shrink-0" onClick={() => sim.mutate()} disabled={sim.isPending}>
            {sim.isPending ? 'Simulating…' : 'Simulate reading'}
          </button>
        </div>
        {sim.isError && <p className="text-xs text-alert">Couldn't reach the backend. Check that it's running on port 8000.</p>}
        <p className="text-xs text-muted">
          Live readings arrive automatically from the ESP32. Simulated ones stay tagged as simulated.
        </p>
      </div>
    </section>
  )
}

function AlertsCard({ reading, cv, risk }: { reading?: SensorReading; cv?: CVPrediction; risk?: DiseaseRiskPrediction }) {
  const alerts: Array<{ level: 'warn' | 'info'; title: string; detail: string }> = []
  for (const m of METRICS) {
    const t = reading?.threshold_status?.[m.key]
    if (t && (t.status === 'LOW' || t.status === 'HIGH')) {
      alerts.push({ level: 'warn', title: `${m.label} ${t.status === 'LOW' ? 'low' : 'high'}`, detail: `Outside tomato's optimal range` })
    }
  }
  if (cv?.low_confidence_warning) {
    alerts.push({ level: 'warn', title: 'Uncertain leaf diagnosis', detail: `${Math.round(cv.confidence * 100)}% confidence. Retake the photo in shade` })
  }
  if (!risk || risk.model_status === 'demo') {
    alerts.push({ level: 'info', title: 'Risk model is a demo', detail: 'Trained on synthetic data until field data arrives' })
  }
  alerts.push({ level: 'info', title: 'pH is relative', detail: 'Probe is uncalibrated; compare readings, not absolute pH' })

  const warnings = alerts.filter((a) => a.level === 'warn').length
  return (
    <section className="card flex flex-col gap-3 p-5" aria-labelledby="alerts-title">
      <CardHeader id="alerts-title" title={warnings ? `Alerts (${warnings})` : 'Notes'} />
      <ul className="flex flex-col gap-3">
        {alerts.map((a) => (
          <li key={a.title} className="flex gap-2.5">
            {a.level === 'warn' ? (
              <AlertTriangle size={16} className="mt-0.5 shrink-0 text-warn" aria-label="Warning" />
            ) : (
              <Info size={16} className="mt-0.5 shrink-0 text-faint" aria-label="Note" />
            )}
            <div>
              <p className="text-sm font-semibold leading-snug text-ink">{a.title}</p>
              <p className="text-xs text-muted">{a.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

/* ---------- Right column ---------- */

function DiagnosisCard({ cv }: { cv?: CVPrediction }) {
  return (
    <section className="card flex flex-col gap-4 p-5" aria-labelledby="diagnosis-title">
      <CardHeader id="diagnosis-title" title="Leaf diagnosis" aside={cv && <span className="text-xs text-muted">{timeAgo(cv.timestamp)}</span>} />
      {cv ? (
        <>
          <div className="flex items-center gap-4">
            <ConfidenceGauge value={cv.confidence} />
            <div className="min-w-0">
              <p className="text-[26px] font-light leading-tight tracking-display text-ink">{cv.disease}</p>
              <p className={clsx('mt-1 text-xs font-semibold', cv.low_confidence_warning ? 'text-warn' : 'text-leaf-deep')}>
                {cv.low_confidence_warning ? 'Low confidence. Retake the photo' : 'Confident prediction'}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ModelStatusBadge status={cv.model_status} />
            <span className="chip bg-tile text-muted num">{cv.model_version}</span>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted">No leaf scanned yet. Upload a photo to get a diagnosis from the EfficientNet-B0 model.</p>
      )}
      <Link to="/cv" className="btn-quiet self-start">
        <ScanLine size={16} aria-hidden="true" /> Scan a leaf
      </Link>
    </section>
  )
}

const RISK_TEXT: Record<DiseaseRiskPrediction['risk_level'], string> = {
  low: 'Low risk',
  moderate: 'Moderate risk',
  high: 'High risk',
  critical: 'Critical risk',
  unknown: 'Unknown',
}

// Same cut-offs as score_to_risk_level in ml/disease_risk/models/random_forest.py
const RISK_ZONES = [
  { from: 0, to: 25, level: 'low', bar: 'bg-leaf', text: 'text-leaf-deep' },
  { from: 25, to: 50, level: 'moderate', bar: 'bg-[#E5B44A]', text: 'text-warn' },
  { from: 50, to: 75, level: 'high', bar: 'bg-[#E0833F]', text: 'text-[#9A4A12]' },
  { from: 75, to: 100, level: 'critical', bar: 'bg-alert', text: 'text-alert' },
] as const

function RiskScale({ score }: { score?: number }) {
  // Vertical 0–100 scale: a zone bar coloured by risk level, labels every 25, a marker at the score
  return (
    <div className="relative h-[180px] w-[52px] shrink-0" aria-hidden="true">
      <div className="absolute inset-y-0 left-[30px] flex w-2 flex-col-reverse overflow-hidden rounded-full">
        {RISK_ZONES.map((z) => (
          <span key={z.level} className={clsx('flex-1', z.bar, score != null && zoneFor(score) !== z && 'opacity-35')} />
        ))}
      </div>
      {[0, 25, 50, 75, 100].map((t) => (
        <span key={t} className="num absolute left-0 w-6 -translate-y-1/2 text-right text-xs text-muted" style={{ top: `${100 - t}%` }}>
          {t}
        </span>
      ))}
      {score != null && (
        <span
          className="absolute left-[40px] h-0 w-0 -translate-y-1/2 border-y-[6px] border-r-[9px] border-y-transparent border-r-ink transition-[top] duration-700"
          style={{ top: `${100 - score}%` }}
        />
      )}
    </div>
  )
}

function zoneFor(score: number) {
  return RISK_ZONES.find((z) => score < z.to) ?? RISK_ZONES[3]
}

function RiskCard({ reading, cv, risk }: { reading?: SensorReading; cv?: CVPrediction; risk?: DiseaseRiskPrediction }) {
  const qc = useQueryClient()
  const run = useMutation({
    mutationFn: () =>
      predictDiseaseRisk({ crop_id: CROP_ID, plant_id: PLANT_ID, sensor_reading_id: reading?.id, cv_prediction_id: cv?.id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['risk-history'] }),
  })
  const score = risk ? Math.round(risk.risk_score * 100) : undefined
  const canRun = Boolean(reading || cv)

  return (
    <section className="card flex flex-col gap-4 p-5" aria-labelledby="risk-title">
      <CardHeader id="risk-title" title="Disease risk" aside={risk && <ModelStatusBadge status={risk.model_status} />} />
      <div className="flex items-center gap-4">
        <RiskScale score={score} />
        <div className="min-w-0">
          <p className="num text-[56px] font-light leading-none tracking-display text-ink">{score ?? '—'}</p>
          <p className={clsx('mt-2 text-sm font-semibold', score != null ? zoneFor(score).text : 'text-ink')}>
            {risk ? RISK_TEXT[risk.risk_level] : 'Not assessed yet'}
          </p>
          <p className="mt-1 text-xs text-muted">Combines the latest sensor reading and leaf diagnosis</p>
        </div>
      </div>
      {risk?.contributing_factors?.length ? (
        <ul className="flex flex-wrap gap-1.5">
          {risk.contributing_factors.slice(0, 4).map((f) => (
            <li key={f} className="chip bg-tile text-muted">{f}</li>
          ))}
        </ul>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-quiet" onClick={() => run.mutate()} disabled={!canRun || run.isPending}>
          {run.isPending ? 'Assessing…' : risk ? 'Re-assess' : 'Assess risk'}
        </button>
        <Link to="/recommendations" className="btn-quiet">
          Get advice <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </div>
      {!canRun && <p className="text-xs text-muted">Needs a sensor reading or a leaf scan first.</p>}
    </section>
  )
}

/* ---------- Banner ---------- */

function StateBanner({ reading }: { reading?: SensorReading }) {
  const off = METRICS.filter((m) => {
    const t = reading?.threshold_status?.[m.key]
    return t && (t.status === 'LOW' || t.status === 'HIGH')
  })
  const tone = !reading ? 'idle' : off.length ? 'warn' : 'ok'
  const text = !reading
    ? 'No readings yet. Simulate one, or power the ESP32 field unit to start streaming.'
    : off.length
      ? `${off.length} of 4 readings outside tomato's optimal range: ${off.map((m) => m.label.toLowerCase()).join(', ')}.`
      : 'All four readings are inside tomato’s optimal ranges.'
  return (
    <div
      role="status"
      className={clsx(
        'flex items-center gap-3 rounded-card px-5 py-3.5 text-sm font-semibold',
        tone === 'ok' && 'bg-leaf-mint text-leaf-deep',
        tone === 'warn' && 'bg-warn-field text-warn',
        tone === 'idle' && 'bg-shell text-muted'
      )}
    >
      <span className={clsx('h-2 w-2 shrink-0 rounded-full', tone === 'ok' ? 'bg-leaf' : tone === 'warn' ? 'bg-warn' : 'bg-faint')} />
      {text}
    </div>
  )
}

/* ---------- Page ---------- */

export default function DashboardPage() {
  const { data: reading, isLoading } = useQuery({
    queryKey: ['sensor-latest', PLANT_ID, CROP_ID],
    queryFn: () => getLatestSensorReading(PLANT_ID, CROP_ID),
    retry: false,
    refetchInterval: 20_000,
  })
  const { data: cvHistory } = useQuery({
    queryKey: ['cv-history', PLANT_ID],
    queryFn: () => getPlantCVHistory(PLANT_ID),
    retry: false,
  })
  const { data: riskHistory } = useQuery({
    queryKey: ['risk-history', PLANT_ID],
    queryFn: () => getRiskHistory(PLANT_ID),
    retry: false,
  })
  const { data: history } = useQuery({
    queryKey: ['sensor-history', PLANT_ID, CROP_ID, '1d'],
    queryFn: () => getSensorHistory(PLANT_ID, CROP_ID, '1d'),
    retry: false,
    refetchInterval: 20_000,
  })
  const { data: crop } = useQuery({ queryKey: ['crop', CROP_ID], queryFn: () => getCropDetail(CROP_ID) })
  const cv = cvHistory?.[0]
  const risk = riskHistory?.[0]

  return (
    <div className="flex flex-col gap-4">
      <h1 className="sr-only">DeepCrop overview for tomato plant {PLANT_ID}</h1>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(290px,320px)_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-4">
          <ConditionsCard
            reading={reading}
            history={history?.readings ?? []}
            bands={crop?.thresholds ?? undefined}
            isLoading={isLoading}
          />
          <AlertsCard reading={reading} cv={cv} risk={risk} />
        </div>

        <section className="card relative flex min-h-[560px] flex-col overflow-hidden p-0 sm:min-h-[480px] lg:min-h-0" aria-label="Field unit">
          <FieldUnitHero reading={reading} />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-[#E3E8E0] via-[#E3E8E0]/85 to-transparent px-5 pb-4 pt-12 sm:px-6 sm:pb-5 sm:pt-16">
            <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
              <div>
                <p className="text-[22px] font-semibold tracking-display text-ink">Field unit A1</p>
                <p className="hidden text-sm text-muted sm:block">Drag to rotate · hover a reading to find its sensor</p>
              </div>
              <dl className="grid w-full grid-cols-[auto_auto_minmax(0,1fr)_auto] gap-x-5 text-sm sm:w-auto">
                <div>
                  <dt className="text-xs text-muted">Crop</dt>
                  <dd className="font-semibold text-ink">Tomato</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Plant</dt>
                  <dd className="num font-semibold text-ink">{PLANT_ID}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Device</dt>
                  <dd className="num truncate font-semibold text-ink">{reading?.device_id ?? 'None reporting'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted">Last reading</dt>
                  <dd className="num font-semibold text-ink">{reading ? new Date(reading.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        <div className="flex flex-col gap-4 lg:col-span-2 lg:grid lg:grid-cols-2 xl:col-span-1 xl:flex">
          <DiagnosisCard cv={cv} />
          <RiskCard reading={reading} cv={cv} risk={risk} />
        </div>
      </div>
      <StateBanner reading={reading} />
    </div>
  )
}

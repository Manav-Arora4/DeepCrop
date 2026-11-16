import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import clsx from 'clsx'
import { getSensorHistory, simulateSensors } from '../api/sensors'
import { getCropDetail } from '../api/crops'
import DataSourceBadge from '../components/badges/DataSourceBadge'
import PageHeader from '../components/PageHeader'
import { CROP_ID, PLANT_ID } from '../components/Layout'

type TimeRange = '1h' | '6h' | '1d' | '7d' | '30d'
type Scenario = 'optimal' | 'drought' | 'overwatered' | 'disease_risk' | 'random'
const RANGES: TimeRange[] = ['1h', '6h', '1d', '7d', '30d']

const SERIES = [
  { key: 'temperature', label: 'Air temperature', unit: '°C', note: 'DHT22' },
  { key: 'humidity', label: 'Relative humidity', unit: '%', note: 'DHT22' },
  { key: 'moisture', label: 'Soil moisture', unit: '%', note: 'Resistive probe' },
  { key: 'ph', label: 'Soil pH', unit: 'rel.', note: 'Uncalibrated probe, relative only' },
] as const

const AXIS = { stroke: '#596158', fontSize: 12, tickLine: false, axisLine: false }

// Round axis bounds to a 1/2/5 step so ticks land on even values
function niceAxis(lo: number, hi: number, count = 4): { domain: [number, number]; ticks: number[] } {
  const raw = (hi - lo) / count || 1
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag
  const min = Math.floor(lo / step) * step
  const max = Math.ceil(hi / step) * step
  const ticks: number[] = []
  for (let v = min; v <= max + step / 2; v += step) ticks.push(+v.toFixed(6))
  return { domain: [min, max], ticks }
}

function fmt(v: number | null, digits: number) {
  return v == null ? '—' : v.toFixed(digits)
}

export default function SensorsPage() {
  const qc = useQueryClient()
  const [range, setRange] = useState<TimeRange>('1d')
  const [scenario, setScenario] = useState<Scenario>('optimal')

  const { data, isLoading } = useQuery({
    queryKey: ['sensor-history', PLANT_ID, CROP_ID, range],
    queryFn: () => getSensorHistory(PLANT_ID, CROP_ID, range),
    retry: false,
  })
  const { data: crop } = useQuery({ queryKey: ['crop', CROP_ID], queryFn: () => getCropDetail(CROP_ID) })

  const sim = useMutation({
    mutationFn: () => simulateSensors({ crop_id: CROP_ID, plant_id: PLANT_ID, scenario, count: 5 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sensor-history'] })
      qc.invalidateQueries({ queryKey: ['sensor-latest'] })
    },
  })

  const readings = data?.readings ?? []
  const times = readings.map((r) => new Date(r.timestamp).getTime())
  const spanMs = times.length ? times[times.length - 1] - times[0] : 0
  // Under an hour of data, minute labels repeat; show seconds instead
  const timeFmt: Intl.DateTimeFormatOptions =
    spanMs < 3_600_000 ? { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' } : spanMs < 86_400_000 ? { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' } : { month: 'short', day: 'numeric', hour: '2-digit', hourCycle: 'h23' }
  const formatTime = (ms: number) => new Date(ms).toLocaleString([], timeFmt)
  // Insert an empty row across long silences so the line breaks instead of implying continuous sensing
  const GAP_MS = 5 * 60_000
  const chartData: Array<Record<string, number | null>> = []
  readings.forEach((r, i) => {
    if (i > 0 && times[i] - times[i - 1] > GAP_MS) {
      chartData.push({ t: (times[i] + times[i - 1]) / 2, temperature: null, humidity: null, moisture: null, ph: null })
    }
    chartData.push({ t: times[i], temperature: r.temperature, humidity: r.humidity, moisture: r.moisture, ph: r.ph })
  })
  const xTicks = times.length > 1 ? [times[0], (times[0] + times[times.length - 1]) / 2, times[times.length - 1]] : times

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Sensors"
        description="Readings from the field unit over time. The mint band is tomato's optimal range."
        actions={
          <>
            <div role="group" aria-label="Time range" className="flex rounded-full bg-shell p-1">
              {RANGES.map((r) => (
                <button
                  key={r}
                  type="button"
                  aria-pressed={range === r}
                  onClick={() => setRange(r)}
                  className={clsx(
                    'num rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
                    range === r ? 'bg-card text-ink shadow-card' : 'text-muted hover:text-ink'
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
            <label htmlFor="sim-scenario" className="sr-only">Simulated scenario</label>
            <select
              id="sim-scenario"
              value={scenario}
              onChange={(e) => setScenario(e.target.value as Scenario)}
              className="rounded-tile border-0 bg-card px-3 py-2.5 text-sm font-medium shadow-card"
            >
              <option value="optimal">Optimal</option>
              <option value="drought">Drought stress</option>
              <option value="overwatered">Overwatered</option>
              <option value="disease_risk">Disease-conducive</option>
              <option value="random">Random stress</option>
            </select>
            <button type="button" className="btn-primary" onClick={() => sim.mutate()} disabled={sim.isPending}>
              {sim.isPending ? 'Adding…' : 'Add 5 simulated'}
            </button>
          </>
        }
      />

      {isLoading ? (
        <div className="card h-80 animate-pulse" />
      ) : readings.length === 0 ? (
        <div className="card flex flex-col items-center gap-2 p-12 text-center">
          <p className="text-lg font-semibold">No readings in the last {range}</p>
          <p className="max-w-md text-sm text-muted">
            Power the ESP32 field unit to stream live readings, or add simulated ones with the button above. Simulated readings stay
            labelled as simulated.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {SERIES.map((s) => {
              const band = crop?.thresholds?.[s.key]
              const values = readings.map((r) => r[s.key]).filter((v): v is number => v != null)
              const last = values[values.length - 1]
              // Axis covers the data and the optimal band with 25% headroom, so the band reads as a band
              const lo = Math.min(...values, band?.optimal_min ?? Infinity)
              const hi = Math.max(...values, band?.optimal_max ?? -Infinity)
              const pad = Math.max((hi - lo) * 0.2, s.key === 'ph' ? 0.2 : 2)
              const axis = niceAxis(lo - pad, hi + pad)
              return (
                <section key={s.key} className="card p-5" aria-label={s.label}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-[17px] font-semibold tracking-display">{s.label}</h2>
                      <p className="text-xs text-muted">{s.note}</p>
                    </div>
                    <p className="num text-[30px] font-light leading-none tracking-display">
                      {last == null ? '—' : last.toFixed(s.key === 'ph' ? 2 : 1)}
                      <span className="ml-0.5 text-sm font-normal tracking-normal text-muted">{s.unit}</span>
                    </p>
                  </div>
                  <div className="mt-4 h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 4, right: 28, bottom: 0, left: -18 }}>
                        <CartesianGrid vertical={false} stroke="#E3E8E0" />
                        {band && <ReferenceArea y1={band.optimal_min} y2={band.optimal_max} fill="#DCF5E3" fillOpacity={0.9} />}
                        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} ticks={xTicks} interval={0} tickFormatter={formatTime} {...AXIS} padding={{ left: 12, right: 12 }} />
                        <YAxis {...AXIS} domain={axis.domain} ticks={axis.ticks} width={48} allowDataOverflow />
                        <Tooltip
                          contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 8px 24px -12px rgba(20,24,20,.25)', fontSize: 12 }}
                          labelFormatter={(ms: number) => formatTime(ms)}
                          formatter={(v: number) => [`${v.toFixed(s.key === 'ph' ? 2 : 1)} ${s.unit}`, s.label]}
                        />
                        <Line type="linear" dataKey={s.key} stroke="#13662F" strokeWidth={2} dot={{ r: 2.5, fill: '#13662F', strokeWidth: 0 }} activeDot={{ r: 4, fill: '#22C55E' }} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              )
            })}
          </div>

          <section className="card p-5" aria-labelledby="log-title">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="log-title" className="text-[19px] font-semibold tracking-display">Reading log</h2>
              <p className="num text-xs text-muted">Latest {Math.min(15, readings.length)} of {data?.count}</p>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="text-xs text-muted">
                    <th className="pb-2 font-medium">Time</th>
                    <th className="pb-2 text-right font-medium">Moisture</th>
                    <th className="pb-2 text-right font-medium">pH (rel.)</th>
                    <th className="pb-2 text-right font-medium">Temp</th>
                    <th className="pb-2 text-right font-medium">Humidity</th>
                    <th className="pb-2 pl-4 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody className="num">
                  {readings.slice(-15).reverse().map((r) => (
                    <tr key={r.id} className="border-t border-line">
                      <td className="py-2.5 text-muted">{new Date(r.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</td>
                      <td className="py-2.5 text-right">{fmt(r.moisture, 1)}%</td>
                      <td className="py-2.5 text-right">{fmt(r.ph, 2)}</td>
                      <td className="py-2.5 text-right">{fmt(r.temperature, 1)}°C</td>
                      <td className="py-2.5 text-right">{fmt(r.humidity, 0)}%</td>
                      <td className="py-2.5 pl-4"><DataSourceBadge source={r.data_source} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

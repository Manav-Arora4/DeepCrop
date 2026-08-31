import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSensorHistory, simulateSensors } from '../api/sensors'
import DataSourceBadge from '../components/badges/DataSourceBadge'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Activity, Play, Calendar } from 'lucide-react'

const PLANT_ID = 'plant_01'
const CROP_ID = 'tomato'

type TimeRange = '1h' | '6h' | '1d' | '7d' | '30d'

export default function SensorsPage() {
  const [range, setRange] = useState<TimeRange>('1d')
  const [scenario, setScenario] = useState<'optimal' | 'drought' | 'overwatered' | 'disease_risk' | 'random'>('optimal')
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['sensor-history', PLANT_ID, CROP_ID, range],
    queryFn: () => getSensorHistory(PLANT_ID, CROP_ID, range),
    retry: false,
  })

  const simMutation = useMutation({
    mutationFn: () => simulateSensors({ crop_id: CROP_ID, plant_id: PLANT_ID, scenario, count: 5 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sensor-history'] })
      qc.invalidateQueries({ queryKey: ['sensor-latest'] })
    },
  })

  const chartData = (data?.readings ?? []).map((r) => ({
    timestamp: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    moisture: r.moisture,
    humidity: r.humidity,
    temperature: r.temperature,
    ph: r.ph,
  }))

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header & Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Environmental Sensor Telemetry</h2>
          <p className="text-sm text-slate-500 mt-0.5">Time-series environmental analytics for Tomato (Plant Alpha)</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Time range selector */}
          <div className="inline-flex rounded-xl border border-slate-200 p-1 bg-slate-50">
            {(['1h', '6h', '1d', '7d', '30d'] as TimeRange[]).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                  range === r ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Simulator batch trigger */}
          <div className="flex items-center rounded-xl border border-slate-200 p-1 bg-slate-50">
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value as any)}
              className="bg-transparent text-xs font-semibold text-slate-700 px-2.5 py-1 focus:outline-none"
            >
              <option value="optimal">Sim: Optimal</option>
              <option value="drought">Sim: Drought</option>
              <option value="overwatered">Sim: Overwatered</option>
              <option value="disease_risk">Sim: Disease Risk</option>
              <option value="random">Sim: Random</option>
            </select>
            <button
              onClick={() => simMutation.mutate()}
              disabled={simMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition-colors shadow-sm"
            >
              <Play size={12} fill="currentColor" />
              {simMutation.isPending ? 'Ingesting...' : 'Add 5 Readings'}
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="h-96 rounded-2xl bg-slate-100 animate-pulse border border-slate-200" />
      ) : data && data.readings.length > 0 ? (
        <div className="space-y-6">
          {/* Main Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Moisture & Humidity Chart */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span>💧</span> Soil Moisture & Atmospheric Humidity (%)
                </h4>
                <span className="text-xs text-slate-400 font-medium">Bounds: 30% - 70%</span>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={11} />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="moisture" name="Soil Moisture %" stroke="#0ea5e9" strokeWidth={2.5} dot={false} />
                    <Line type="monotone" dataKey="humidity" name="Humidity %" stroke="#8b5cf6" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Temperature & pH Chart */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span>🌡️</span> Ambient Temperature (°C) & Soil pH
                </h4>
                <span className="text-xs text-slate-400 font-medium">Optimal: 10-30°C / pH 5.5-7.0</span>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={11} />
                    <YAxis yAxisId="left" stroke="#ef4444" fontSize={11} domain={['auto', 'auto']} />
                    <YAxis yAxisId="right" orientation="right" stroke="#10b981" fontSize={11} domain={[4, 9]} />
                    <Tooltip />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="temperature" name="Temp (°C)" stroke="#ef4444" strokeWidth={2.5} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="ph" name="Soil pH" stroke="#10b981" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Historical Log Table */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900">Telemetry Ingestion Log ({data.count} records)</h4>
              <span className="text-xs text-slate-400">Displaying most recent 15 records</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 uppercase font-semibold">
                  <tr>
                    <th className="px-5 py-3">Timestamp</th>
                    <th className="px-5 py-3">Soil Moisture</th>
                    <th className="px-5 py-3">pH Level</th>
                    <th className="px-5 py-3">Temperature</th>
                    <th className="px-5 py-3">Humidity</th>
                    <th className="px-5 py-3">Data Provenance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                  {data.readings.slice(-15).reverse().map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-5 py-3 text-slate-500">{new Date(r.timestamp).toLocaleString()}</td>
                      <td className="px-5 py-3 font-semibold">{r.moisture ?? '—'}%</td>
                      <td className="px-5 py-3 font-semibold">{r.ph ?? '—'}</td>
                      <td className="px-5 py-3 font-semibold">{r.temperature ?? '—'}°C</td>
                      <td className="px-5 py-3 font-semibold">{r.humidity ?? '—'}%</td>
                      <td className="px-5 py-3">
                        <DataSourceBadge source={r.data_source} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center max-w-lg mx-auto">
          <Activity className="mx-auto text-slate-400 mb-3" size={32} />
          <h4 className="text-base font-bold text-slate-900">No Historical Records Found</h4>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            There are no telemetry points recorded in the selected time range ({range}).
          </p>
          <button
            onClick={() => simMutation.mutate()}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold transition-colors"
          >
            Generate Synthetic Test Data
          </button>
        </div>
      )}
    </div>
  )
}

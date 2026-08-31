import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLatestSensorReading, simulateSensors } from '../api/sensors'
import { listCrops } from '../api/crops'
import SensorCard from '../components/dashboard/SensorCard'
import DataSourceBadge from '../components/badges/DataSourceBadge'
import { RefreshCw, Play, ArrowRight, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Link } from 'react-router-dom'

const PLANT_ID = 'plant_01'
const CROP_ID = 'tomato'

export default function DashboardPage() {
  const qc = useQueryClient()
  const [scenario, setScenario] = useState<'optimal' | 'drought' | 'overwatered' | 'disease_risk' | 'random'>('optimal')

  const { data: crops } = useQuery({
    queryKey: ['crops'],
    queryFn: listCrops,
  })

  const { data: reading, refetch, isLoading, isFetching } = useQuery({
    queryKey: ['sensor-latest', PLANT_ID, CROP_ID],
    queryFn: () => getLatestSensorReading(PLANT_ID, CROP_ID),
    retry: false,
  })

  const simMutation = useMutation({
    mutationFn: () => simulateSensors({ crop_id: CROP_ID, plant_id: PLANT_ID, scenario, count: 1 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sensor-latest'] })
    },
  })

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Hero Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Agricultural Telemetry Overview</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time multimodal monitoring for <strong className="text-slate-800">Tomato Plot Alpha (plant_01)</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors border border-slate-200"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>

          <div className="flex items-center rounded-xl border border-slate-200 p-1 bg-slate-50">
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value as any)}
              className="bg-transparent text-xs font-semibold text-slate-700 px-2.5 py-1 focus:outline-none"
            >
              <option value="optimal">Scenario: Optimal</option>
              <option value="drought">Scenario: Drought Stress</option>
              <option value="overwatered">Scenario: Overwatered</option>
              <option value="disease_risk">Scenario: Disease Conducive</option>
              <option value="random">Scenario: Random Stress</option>
            </select>
            <button
              onClick={() => simMutation.mutate()}
              disabled={simMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition-colors shadow-sm"
            >
              <Play size={12} fill="currentColor" />
              {simMutation.isPending ? 'Simulating...' : 'Simulate'}
            </button>
          </div>
        </div>
      </div>

      {/* Sensor Reading Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-bold text-slate-800">Environmental Sensor Grid</h3>
            {reading && <DataSourceBadge source={reading.data_source} />}
          </div>
          {reading && (
            <span className="text-xs text-slate-400 font-medium">
              Last Telemetry: {new Date(reading.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-36 rounded-2xl bg-slate-100 animate-pulse border border-slate-200" />
            ))}
          </div>
        ) : reading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <SensorCard
              title="Soil Moisture"
              value={reading.moisture}
              threshold={reading.threshold_status?.moisture}
              icon="💧"
              description="Capacitive VWC probe"
            />
            <SensorCard
              title="Soil pH Level"
              value={reading.ph}
              threshold={reading.threshold_status?.ph}
              icon="⚗️"
              description="Electrochemical probe"
            />
            <SensorCard
              title="Air Temperature"
              value={reading.temperature}
              threshold={reading.threshold_status?.temperature}
              icon="🌡️"
              description="DHT22 ambient sensor"
            />
            <SensorCard
              title="Relative Humidity"
              value={reading.humidity}
              threshold={reading.threshold_status?.humidity}
              icon="💨"
              description="Atmospheric humidity"
            />
          </div>
        ) : (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center">
            <AlertTriangle className="mx-auto text-amber-600 mb-2" size={28} />
            <h4 className="text-base font-semibold text-amber-900">No Sensor Telemetry Received Yet</h4>
            <p className="text-sm text-amber-700 mt-1 max-w-md mx-auto">
              Select a scenario above and click <strong>Simulate</strong> or transmit live telemetry from your ESP32 hardware.
            </p>
          </div>
        )}
      </div>

      {/* Decision-Support Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-emerald-900 to-slate-900 text-white rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="h-10 w-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xl mb-4">
              📷
            </div>
            <h4 className="text-lg font-bold">Leaf Disease Classifier</h4>
            <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
              Upload RGB leaf photos to run PyTorch EfficientNetB0 inference across 10 tomato health & disease categories.
            </p>
          </div>
          <Link
            to="/cv"
            className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-400 hover:text-emerald-300 mt-6 group"
          >
            Launch CV Diagnostic <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="h-10 w-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center text-xl mb-4 border border-purple-100">
              ✨
            </div>
            <h4 className="text-lg font-bold text-slate-900">RAG Agronomic Advisory</h4>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              Generate grounded recommendations combining IoT metrics, CV findings, and local Ollama LLM vector intelligence.
            </p>
          </div>
          <Link
            to="/recommendations"
            className="inline-flex items-center gap-2 text-xs font-semibold text-purple-600 hover:text-purple-700 mt-6 group"
          >
            Consult AI Advisor <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center text-xl mb-4 border border-blue-100">
              📈
            </div>
            <h4 className="text-lg font-bold text-slate-900">Time-Series Trends</h4>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              Inspect historical sensor trendlines (1h, 6h, 1d, 7d, 30d) and evaluate environmental stability bounds.
            </p>
          </div>
          <Link
            to="/sensors"
            className="inline-flex items-center gap-2 text-xs font-semibold text-blue-600 hover:text-blue-700 mt-6 group"
          >
            View Sensor Analytics <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>

      {/* Registered Crop Modules Grid */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-900 mb-4">Registered Crop Modules</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {crops?.map((c) => (
            <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div>
                <h5 className="font-bold text-slate-900">{c.name}</h5>
                <p className="text-xs text-slate-500 mt-0.5">v{c.version} • {c.growth_stages.length} growth stages</p>
              </div>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                c.installed ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-500 border-slate-200'
              }`}>
                {c.installed ? 'Active Module' : 'Stub Module'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

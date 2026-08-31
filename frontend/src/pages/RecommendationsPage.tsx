import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { generateRecommendation, predictDiseaseRisk, getRecommendationHistory } from '../api/recommendations'
import { getLatestSensorReading } from '../api/sensors'
import { getPlantCVHistory } from '../api/cv'
import type { Recommendation, DiseaseRiskPrediction } from '../api/types'
import { Sparkles, Brain, BookOpen, AlertCircle, ShieldAlert, CheckCircle2, FileText, ChevronRight } from 'lucide-react'

const PLANT_ID = 'plant_01'
const CROP_ID = 'tomato'

const URGENCY_STYLE = {
  low: { badge: 'bg-emerald-50 text-emerald-700 border-emerald-300 ring-1 ring-emerald-500/20', border: 'border-emerald-200' },
  medium: { badge: 'bg-amber-50 text-amber-700 border-amber-300 ring-1 ring-amber-500/20', border: 'border-amber-200' },
  moderate: { badge: 'bg-amber-50 text-amber-700 border-amber-300 ring-1 ring-amber-500/20', border: 'border-amber-200' },
  high: { badge: 'bg-orange-50 text-orange-700 border-orange-300 ring-1 ring-orange-500/20', border: 'border-orange-200' },
  critical: { badge: 'bg-rose-50 text-rose-700 border-rose-300 ring-1 ring-rose-500/20', border: 'border-rose-200' },
}

export default function RecommendationsPage() {
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [riskAssessment, setRiskAssessment] = useState<DiseaseRiskPrediction | null>(null)
  const qc = useQueryClient()

  // Fetch contextual telemetry and CV findings
  const { data: latestSensor } = useQuery({
    queryKey: ['sensor-latest', PLANT_ID, CROP_ID],
    queryFn: () => getLatestSensorReading(PLANT_ID, CROP_ID),
  })

  const { data: cvHistory } = useQuery({
    queryKey: ['cv-history', PLANT_ID],
    queryFn: () => getPlantCVHistory(PLANT_ID),
  })
  const latestCV = cvHistory && cvHistory.length > 0 ? cvHistory[0] : null

  const { data: pastRecs, refetch: refetchRecHistory } = useQuery({
    queryKey: ['rec-history', PLANT_ID],
    queryFn: () => getRecommendationHistory(PLANT_ID),
  })

  // Multimodal Risk Assessment Mutation
  const riskMutation = useMutation({
    mutationFn: () => predictDiseaseRisk({
      crop_id: CROP_ID,
      plant_id: PLANT_ID,
      sensor_reading_id: latestSensor?.id,
      cv_prediction_id: latestCV?.id,
    }),
    onSuccess: (data) => setRiskAssessment(data),
  })

  // RAG Advisory Generation Mutation
  const adviseMutation = useMutation({
    mutationFn: async () => {
      // 1. Trigger risk model first if not done
      let rId = riskAssessment?.id
      if (!rId) {
        const rRes = await predictDiseaseRisk({
          crop_id: CROP_ID,
          plant_id: PLANT_ID,
          sensor_reading_id: latestSensor?.id,
          cv_prediction_id: latestCV?.id,
        })
        setRiskAssessment(rRes)
        rId = rRes.id
      }

      // 2. Generate grounded recommendation
      return generateRecommendation({
        crop_id: CROP_ID,
        plant_id: PLANT_ID,
        sensor_reading_id: latestSensor?.id,
        cv_prediction_id: latestCV?.id,
        risk_prediction_id: rId,
      })
    },
    onSuccess: (data) => {
      setRecommendation(data)
      refetchRecHistory()
    },
  })

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">RAG + LLM Agronomic Advisory</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Knowledge-grounded agricultural decision support synthesized via Ollama & ChromaDB vector search.
          </p>
        </div>

        <button
          onClick={() => adviseMutation.mutate()}
          disabled={adviseMutation.isPending}
          className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 transition-all shadow-md shadow-emerald-600/20"
        >
          {adviseMutation.isPending ? (
            <>
              <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Retrieving Agronomic Context & Generating...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Generate Advisory Advisory
            </>
          )}
        </button>
      </div>

      {/* Multimodal Input Context Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Sensor Condition Context */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Modality 1: IoT Sensors</span>
          <div className="mt-3 space-y-1 text-xs">
            {latestSensor ? (
              <>
                <p className="font-semibold text-slate-800">
                  Moisture: {latestSensor.moisture}% • pH: {latestSensor.ph}
                </p>
                <p className="text-slate-500">
                  Temp: {latestSensor.temperature}°C • Humidity: {latestSensor.humidity}%
                </p>
                <span className="inline-block mt-2 text-[10px] text-slate-400 font-mono">
                  Reading ID: #{latestSensor.id} ({latestSensor.data_source})
                </span>
              </>
            ) : (
              <p className="text-slate-400 italic">No sensor telemetry attached</p>
            )}
          </div>
        </div>

        {/* CV Finding Context */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Modality 2: Computer Vision</span>
          <div className="mt-3 space-y-1 text-xs">
            {latestCV ? (
              <>
                <p className="font-bold text-slate-900">{latestCV.disease}</p>
                <p className="text-slate-500">
                  Confidence: {(latestCV.confidence * 100).toFixed(1)}% • Status: {latestCV.model_status}
                </p>
                <span className="inline-block mt-2 text-[10px] text-slate-400 font-mono">
                  Prediction ID: #{latestCV.id}
                </span>
              </>
            ) : (
              <p className="text-slate-400 italic">No leaf imagery attached</p>
            )}
          </div>
        </div>

        {/* Multimodal Risk Score */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Multimodal Risk Assessment</span>
          <div className="mt-3 space-y-1 text-xs">
            {riskAssessment ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 capitalize">Risk: {riskAssessment.risk_level}</span>
                  <span className="font-extrabold text-slate-900">{(riskAssessment.risk_score * 100).toFixed(0)}%</span>
                </div>
                <p className="text-slate-500 text-[11px] truncate">
                  {riskAssessment.contributing_factors.join(', ')}
                </p>
              </>
            ) : (
              <p className="text-slate-400 italic">Calculated during advisory generation</p>
            )}
          </div>
        </div>
      </div>

      {/* Advisory Output Display */}
      {recommendation ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-5">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Agronomic Advisory Document</span>
              <h3 className="text-xl font-extrabold text-slate-900 mt-0.5">Crop Health Recommendation Plan</h3>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase border ${
                URGENCY_STYLE[recommendation.urgency as keyof typeof URGENCY_STYLE]?.badge || 'bg-slate-100'
              }`}>
                Urgency: {recommendation.urgency}
              </span>
            </div>
          </div>

          {/* Situation Analysis / Raw Narrative */}
          <div className="prose prose-slate max-w-none text-sm leading-relaxed text-slate-700 bg-slate-50/70 p-6 rounded-2xl border border-slate-100">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Agronomic Synthesis</h4>
            <div className="whitespace-pre-wrap font-sans text-slate-800">{recommendation.summary}</div>
          </div>

          {/* Action Checklist */}
          {recommendation.recommended_actions && recommendation.recommended_actions.length > 0 && (
            <div>
              <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-600" />
                Actionable Next Steps
              </h4>
              <div className="grid grid-cols-1 gap-2.5">
                {recommendation.recommended_actions.map((act, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-slate-200 bg-white flex items-start gap-3 text-xs text-slate-800 font-medium">
                    <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 font-bold text-[11px]">
                      {idx + 1}
                    </span>
                    <span className="mt-0.5">{act.replace(/^\d+\.\s*/, '')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Grounding Attribution & Sources */}
          {recommendation.sources && recommendation.sources.length > 0 && (
            <div className="pt-4 border-t border-slate-100">
              <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <BookOpen size={14} /> Grounding Knowledge Documents
              </h5>
              <div className="flex flex-wrap gap-2">
                {recommendation.sources.map((s, idx) => (
                  <span key={idx} className="px-3 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 text-xs font-mono">
                    📄 {s.title} (relevance: {(s.relevance * 100).toFixed(0)}%)
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="text-[11px] text-slate-400 font-mono">
            Provider: {recommendation.llm_provider} ({recommendation.llm_model}) • Recorded: {new Date(recommendation.timestamp).toLocaleString()}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center shadow-sm">
          <Brain className="mx-auto text-slate-300 mb-3" size={44} />
          <h4 className="text-base font-bold text-slate-800">No Advisory Generated Yet</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 mb-6">
            Click "Generate Advisory Plan" above to trigger vector retrieval from the crop knowledge repository and synthesis by Ollama.
          </p>
        </div>
      )}
    </div>
  )
}

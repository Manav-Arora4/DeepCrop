import React, { useState, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { predictDisease, getPlantCVHistory } from '../api/cv'
import type { CVPrediction } from '../api/types'
import ModelStatusBadge from '../components/badges/ModelStatusBadge'
import { UploadCloud, Image as ImageIcon, CheckCircle, AlertTriangle, AlertCircle, ShieldAlert, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

const CROP_ID = 'tomato'
const PLANT_ID = 'plant_01'

export default function CVPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<CVPrediction | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ['cv-history', PLANT_ID],
    queryFn: () => getPlantCVHistory(PLANT_ID),
  })

  const predictMutation = useMutation({
    mutationFn: (f: File) => predictDisease(f, CROP_ID, PLANT_ID),
    onSuccess: (data) => {
      setResult(data)
      refetchHistory()
    },
  })

  const handleSelectFile = (f: File) => {
    setFile(f)
    setResult(null)
    setPreview(URL.createObjectURL(f))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectFile(e.dataTransfer.files[0])
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Foliar Computer Vision Diagnostics</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          EfficientNetB0 deep learning classifier trained on 10 Tomato PlantVillage disease classes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Upload & Inference Action Column */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-3">Upload Leaf Imagery</h3>

            <div
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className="border-2 border-dashed border-slate-200 rounded-2xl p-6 text-center cursor-pointer hover:border-emerald-500 hover:bg-emerald-50/30 transition-all flex flex-col items-center justify-center min-h-[220px]"
            >
              {preview ? (
                <div className="relative group w-full">
                  <img src={preview} alt="Leaf preview" className="max-h-52 mx-auto rounded-xl shadow-sm object-contain" />
                  <div className="absolute inset-0 bg-slate-900/40 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs font-semibold">
                    Click to choose different image
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="h-12 w-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                    <UploadCloud size={24} />
                  </div>
                  <p className="text-xs font-bold text-slate-700">Drop leaf photo here, or browse</p>
                  <p className="text-[11px] text-slate-400">Supports RGB JPEG, PNG, WEBP (Max 10MB)</p>
                </div>
              )}
            </div>

            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleSelectFile(e.target.files[0])}
            />

            <button
              onClick={() => file && predictMutation.mutate(file)}
              disabled={!file || predictMutation.isPending}
              className="w-full mt-4 py-3 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-2"
            >
              {predictMutation.isPending ? (
                <>
                  <span className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Running Neural Inference...
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  Run Disease Classifier
                </>
              )}
            </button>
          </div>
        </div>

        {/* Diagnosis & Model Output Column */}
        <div className="lg:col-span-7 space-y-6">
          {result ? (
            <div className="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Diagnosis Result</span>
                  <h3 className="text-xl font-extrabold text-slate-900 mt-0.5">{result.disease}</h3>
                </div>
                <ModelStatusBadge status={result.model_status} />
              </div>

              {/* Confidence Meter */}
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-1.5">
                  <span>Model Classification Confidence</span>
                  <span className="text-emerald-700 font-extrabold">{(result.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      result.confidence >= 0.75 ? 'bg-emerald-500' :
                      result.confidence >= 0.65 ? 'bg-amber-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${result.confidence * 100}%` }}
                  />
                </div>

                {result.low_confidence_warning && (
                  <div className="mt-3 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-2 text-xs text-amber-800 font-medium">
                    <AlertTriangle size={16} className="shrink-0 text-amber-600" />
                    <span>Low Confidence Notice: Capture another high-resolution leaf image under direct lighting.</span>
                  </div>
                )}
              </div>

              {/* Diagnostic Meta Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-slate-400 font-medium">Class Key</span>
                  <p className="font-mono font-semibold text-slate-800 mt-0.5 truncate">{result.disease_id}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-slate-400 font-medium">Model Architecture</span>
                  <p className="font-semibold text-slate-800 mt-0.5">EfficientNetB0</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-slate-400 font-medium">Version</span>
                  <p className="font-semibold text-slate-800 mt-0.5">{result.model_version}</p>
                </div>
              </div>

              {/* Recommendation Bridge CTA */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <p className="text-xs text-slate-500">Bridge this finding into the Multimodal RAG Engine:</p>
                <Link
                  to="/recommendations"
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold transition-colors"
                >
                  Generate AI Treatment Plan →
                </Link>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
              <ImageIcon className="mx-auto text-slate-300 mb-3" size={40} />
              <h4 className="text-base font-bold text-slate-800">Awaiting Leaf Capture</h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                Upload or drag a tomato leaf photograph into the left pane to execute real-time disease diagnostic classification.
              </p>
            </div>
          )}

          {/* Historical Prediction Log */}
          {history && history.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <h4 className="text-sm font-bold text-slate-900 mb-4">Past Foliar Diagnostics ({history.length})</h4>
              <div className="space-y-2.5">
                {history.slice(0, 5).map((h) => (
                  <div key={h.id} className="p-3 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-slate-900">{h.disease}</span>
                      <span className="text-slate-400 ml-2">({(h.confidence * 100).toFixed(0)}% conf)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">{new Date(h.timestamp).toLocaleTimeString()}</span>
                      <ModelStatusBadge status={h.model_status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCrops, getCropDetail } from '../api/crops'
import type { CropDetail } from '../api/types'
import { Layers, ShieldCheck, CheckCircle2, ChevronRight, BookOpen, AlertCircle } from 'lucide-react'

export default function CropsPage() {
  const [selectedCrop, setSelectedCrop] = useState<string>('tomato')

  const { data: crops, isLoading: loadingList } = useQuery({
    queryKey: ['crops'],
    queryFn: listCrops,
  })

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ['crop-detail', selectedCrop],
    queryFn: () => getCropDetail(selectedCrop),
    enabled: !!selectedCrop,
  })

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Crop Modules Architecture</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Modular crop configuration repository. Additional crops can be installed without altering core system code.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Crop Selector Column */}
        <div className="lg:col-span-4 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">Registered Modules</h3>
          {crops?.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedCrop(c.id)}
              className={`w-full p-4 rounded-2xl border text-left transition-all flex items-center justify-between ${
                selectedCrop === c.id
                  ? 'border-emerald-500 bg-emerald-50/40 shadow-sm'
                  : 'border-slate-200 bg-white hover:bg-slate-50'
              }`}
            >
              <div>
                <h4 className="font-bold text-slate-900 text-sm">{c.name}</h4>
                <p className="text-xs text-slate-500 mt-0.5">v{c.version} • {c.growth_stages.length} growth stages</p>
              </div>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                c.installed ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-500 border-slate-200'
              }`}>
                {c.installed ? 'Active' : 'Stub'}
              </span>
            </button>
          ))}
        </div>

        {/* Selected Crop Details Column */}
        <div className="lg:col-span-8 space-y-6">
          {detail ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-8">
              <div className="flex items-center justify-between border-b border-slate-100 pb-5">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Module Specification</span>
                  <h3 className="text-2xl font-extrabold text-slate-900 mt-0.5">{detail.name}</h3>
                  <p className="text-xs text-slate-500 mt-1">{detail.description}</p>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase border ${
                  detail.installed ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-slate-100 text-slate-600'
                }`}>
                  Status: {detail.installed ? 'Installed' : 'Not Installed'}
                </span>
              </div>

              {/* Threshold Specification Grid */}
              {detail.thresholds && (
                <div>
                  <h4 className="text-sm font-bold text-slate-900 mb-3">Evidence-Based Agronomic Thresholds</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {Object.entries(detail.thresholds).map(([key, val]: [string, any]) => {
                      if (typeof val !== 'object' || !val.optimal_min) return null
                      return (
                        <div key={key} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-bold capitalize text-slate-800">{key}</span>
                            <span className="font-mono font-bold text-emerald-700">
                              {val.optimal_min} - {val.optimal_max} {val.unit}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 leading-relaxed">{val.notes}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Disease Classes Table */}
              {detail.disease_classes && (
                <div>
                  <h4 className="text-sm font-bold text-slate-900 mb-3">
                    Supported Disease Diagnostics ({detail.disease_classes.length} Classes)
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {detail.disease_classes.map((cls) => (
                      <div key={cls.id} className="p-3 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span>{cls.is_healthy ? '✅' : '🔴'}</span>
                          <div>
                            <span className="font-bold text-slate-800">{cls.display}</span>
                            {cls.causative_agent && (
                              <p className="text-[10px] text-slate-400 italic">{cls.causative_agent}</p>
                            )}
                          </div>
                        </div>
                        {!cls.is_healthy && (
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                            cls.treatment_urgency === 'critical' ? 'bg-rose-100 text-rose-800' :
                            cls.treatment_urgency === 'high' ? 'bg-orange-100 text-orange-800' :
                            'bg-amber-100 text-amber-800'
                          }`}>
                            {cls.treatment_urgency}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-64 rounded-2xl bg-slate-100 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  )
}

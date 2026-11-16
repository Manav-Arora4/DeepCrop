import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, FileText } from 'lucide-react'
import clsx from 'clsx'
import { generateRecommendation, getRecommendationHistory, getRiskHistory, predictDiseaseRisk } from '../api/recommendations'
import { getLatestSensorReading } from '../api/sensors'
import { getPlantCVHistory } from '../api/cv'
import type { Recommendation } from '../api/types'
import DataSourceBadge from '../components/badges/DataSourceBadge'
import ModelStatusBadge from '../components/badges/ModelStatusBadge'
import PageHeader from '../components/PageHeader'
import { CROP_ID, PLANT_ID } from '../components/Layout'

const URGENCY: Record<string, string> = {
  low: 'bg-leaf-mint text-leaf-deep',
  medium: 'bg-warn-field text-warn',
  moderate: 'bg-warn-field text-warn',
  high: 'bg-alert-field text-alert',
  critical: 'bg-alert-field text-alert',
}

function Step({ title, children, empty }: { title: string; children?: React.ReactNode; empty: string }) {
  return (
    <div className="min-w-0 flex-1 rounded-tile bg-tile p-4">
      <p className="text-xs font-medium text-muted">{title}</p>
      <div className="mt-1.5">{children ?? <p className="text-sm text-muted">{empty}</p>}</div>
    </div>
  )
}

export default function RecommendationsPage() {
  const qc = useQueryClient()
  const [advice, setAdvice] = useState<Recommendation | null>(null)

  const { data: reading } = useQuery({
    queryKey: ['sensor-latest', PLANT_ID, CROP_ID],
    queryFn: () => getLatestSensorReading(PLANT_ID, CROP_ID),
    retry: false,
  })
  const { data: cvHistory } = useQuery({ queryKey: ['cv-history', PLANT_ID], queryFn: () => getPlantCVHistory(PLANT_ID), retry: false })
  const { data: riskHistory } = useQuery({ queryKey: ['risk-history', PLANT_ID], queryFn: () => getRiskHistory(PLANT_ID), retry: false })
  const { data: past } = useQuery({ queryKey: ['rec-history', PLANT_ID], queryFn: () => getRecommendationHistory(PLANT_ID), retry: false })
  const cv = cvHistory?.[0]
  const risk = riskHistory?.[0]
  const shown = advice ?? past?.[0] ?? null

  const generate = useMutation({
    mutationFn: async () => {
      const r = await predictDiseaseRisk({ crop_id: CROP_ID, plant_id: PLANT_ID, sensor_reading_id: reading?.id, cv_prediction_id: cv?.id })
      return generateRecommendation({
        crop_id: CROP_ID,
        plant_id: PLANT_ID,
        sensor_reading_id: reading?.id,
        cv_prediction_id: cv?.id,
        risk_prediction_id: r.id,
      })
    },
    onSuccess: (data) => {
      setAdvice(data)
      qc.invalidateQueries({ queryKey: ['rec-history'] })
      qc.invalidateQueries({ queryKey: ['risk-history'] })
    },
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Advisor"
        description="Advice written by the language model from the tomato knowledge base, grounded in this plant's actual readings, diagnosis and risk."
        actions={
          <button type="button" className="btn-primary" onClick={() => generate.mutate()} disabled={generate.isPending || (!reading && !cv)}>
            {generate.isPending ? 'Writing advice…' : 'Generate advice'}
          </button>
        }
      />

      <section className="card p-5" aria-labelledby="inputs-title">
        <h2 id="inputs-title" className="text-[19px] font-semibold tracking-display">What the advice is based on</h2>
        <div className="mt-3 flex flex-col items-stretch gap-2 md:flex-row md:items-center">
          <Step title="1 · Sensor reading" empty="No reading yet">
            {reading && (
              <>
                <p className="num text-sm font-semibold">
                  {reading.temperature?.toFixed(1) ?? '—'}°C · {reading.humidity?.toFixed(0) ?? '—'}% RH · soil {reading.moisture?.toFixed(1) ?? '—'}%
                </p>
                <div className="mt-2"><DataSourceBadge source={reading.data_source} /></div>
              </>
            )}
          </Step>
          <ChevronRight className="hidden shrink-0 text-faint md:block" size={18} aria-hidden="true" />
          <Step title="2 · Leaf diagnosis" empty="No leaf scanned yet">
            {cv && (
              <>
                <p className="text-sm font-semibold">
                  {cv.disease} <span className="num font-normal text-muted">· {Math.round(cv.confidence * 100)}%</span>
                </p>
                <div className="mt-2"><ModelStatusBadge status={cv.model_status} /></div>
              </>
            )}
          </Step>
          <ChevronRight className="hidden shrink-0 text-faint md:block" size={18} aria-hidden="true" />
          <Step title="3 · Disease risk" empty="Assessed when you generate advice">
            {risk && (
              <>
                <p className="text-sm font-semibold capitalize">
                  {risk.risk_level} <span className="num font-normal text-muted">· {Math.round(risk.risk_score * 100)}/100</span>
                </p>
                <div className="mt-2"><ModelStatusBadge status={risk.model_status} /></div>
              </>
            )}
          </Step>
        </div>
        {!reading && !cv && <p className="mt-3 text-xs text-muted">Add a sensor reading or scan a leaf first; advice needs at least one.</p>}
        {generate.isError && (
          <p className="mt-3 text-xs text-alert">
            Advice couldn't be generated. Check that Ollama is running (<code>ollama serve</code>) with the configured model pulled.
          </p>
        )}
      </section>

      {shown ? (
        <article className="card flex flex-col gap-5 p-6" aria-labelledby="advice-title">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 id="advice-title" className="text-[24px] font-semibold tracking-display">Recommendation</h2>
              <p className="num text-xs text-muted">
                {new Date(shown.timestamp).toLocaleString()} · {shown.llm_provider} ({shown.llm_model})
              </p>
            </div>
            <span className={clsx('chip capitalize', URGENCY[shown.urgency] ?? 'bg-tile text-muted')}>{shown.urgency} urgency</span>
          </div>

          <p className="max-w-[72ch] whitespace-pre-wrap text-[15px] leading-relaxed text-ink">{shown.summary}</p>

          {shown.recommended_actions?.length > 0 && (
            <section aria-labelledby="actions-title">
              <h3 id="actions-title" className="text-[17px] font-semibold tracking-display">Next steps</h3>
              <ol className="mt-2 flex flex-col gap-2">
                {shown.recommended_actions.map((a, i) => (
                  <li key={i} className="flex gap-3 rounded-tile bg-tile p-3 text-sm">
                    <span className="num grid h-6 w-6 shrink-0 place-items-center rounded-full bg-ink text-xs font-semibold text-card">{i + 1}</span>
                    <span className="pt-0.5">{a.replace(/^\d+\.\s*/, '')}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {shown.prevention_steps?.length > 0 && (
            <section aria-labelledby="prevention-title">
              <h3 id="prevention-title" className="text-[17px] font-semibold tracking-display">Prevention</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink marker:text-leaf">
                {shown.prevention_steps.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </section>
          )}

          {shown.sources?.length > 0 && (
            <section aria-labelledby="sources-title" className="border-t border-line pt-4">
              <h3 id="sources-title" className="text-sm font-semibold">Sources retrieved from the knowledge base</h3>
              <ul className="mt-2 flex flex-wrap gap-2">
                {shown.sources.map((s, i) => (
                  <li key={i} className="chip bg-tile font-medium text-ink">
                    <FileText size={13} className="text-faint" aria-hidden="true" />
                    {s.title}
                    <span className="num text-muted">{Math.round(s.relevance * 100)}%</span>
                  </li>
                ))}
              </ul>
              {(() => {
                // References behind the retrieved passages (extension services, FAO), de-duplicated
                const refs = [...new Set(shown.sources.flatMap((s) => s.references ?? []))]
                return refs.length > 0 ? (
                  <ol className="mt-3 flex flex-col gap-1 text-xs text-muted">
                    {refs.map((r) => {
                      const url = r.match(/https?:\/\/\S+/)?.[0]
                      const label = url ? r.replace(url, '').replace(/[:\s]+$/, '').replace(/\*/g, '') : r.replace(/\*/g, '')
                      return (
                        <li key={r}>
                          {url ? (
                            <a href={url} target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-2 hover:text-ink">
                              {label}
                            </a>
                          ) : (
                            label
                          )}
                        </li>
                      )
                    })}
                  </ol>
                ) : null
              })()}
            </section>
          )}
        </article>
      ) : (
        <div className="card p-10 text-center">
          <p className="text-lg font-semibold">No advice yet</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted">
            Press Generate advice. The system assesses risk, retrieves matching passages from the tomato knowledge base, and asks the
            language model to explain them using only this plant's data.
          </p>
        </div>
      )}
    </div>
  )
}

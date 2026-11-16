import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowRight, ImageUp } from 'lucide-react'
import clsx from 'clsx'
import { getPlantCVHistory, predictDisease } from '../api/cv'
import type { CVPrediction } from '../api/types'
import ModelStatusBadge from '../components/badges/ModelStatusBadge'
import ConfidenceGauge from '../components/ConfidenceGauge'
import PageHeader from '../components/PageHeader'
import { CROP_ID, PLANT_ID } from '../components/Layout'

const ACCEPT = 'image/jpeg,image/png,image/webp'

export default function CVPage() {
  const qc = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<CVPrediction | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: history } = useQuery({
    queryKey: ['cv-history', PLANT_ID],
    queryFn: () => getPlantCVHistory(PLANT_ID),
    retry: false,
  })

  const predict = useMutation({
    mutationFn: (f: File) => predictDisease(f, CROP_ID, PLANT_ID),
    onSuccess: (data) => {
      setResult(data)
      qc.invalidateQueries({ queryKey: ['cv-history'] })
    },
  })

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const choose = (f?: File) => {
    if (!f) return
    setFile(f)
    setResult(null)
    predict.reset()
    setPreview(URL.createObjectURL(f))
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Leaf scan"
        description="Upload a photo of a tomato leaf. The EfficientNet-B0 model picks one of 10 classes: nine diseases or healthy."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <section className="card flex flex-col gap-4 p-5" aria-labelledby="upload-title">
          <h2 id="upload-title" className="text-[19px] font-semibold tracking-display">Photo</h2>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files?.[0]) }}
            className={clsx(
              'flex min-h-[260px] flex-col items-center justify-center gap-2 rounded-tile border-2 border-dashed p-5 text-center transition-colors',
              dragging ? 'border-leaf bg-leaf-wash' : 'border-line bg-tile hover:border-faint'
            )}
          >
            {preview ? (
              <img src={preview} alt="Selected leaf" className="max-h-64 rounded-tile object-contain" />
            ) : (
              <>
                <ImageUp size={28} className="text-faint" aria-hidden="true" />
                <span className="text-sm font-semibold text-ink">Drop a leaf photo, or click to browse</span>
                <span className="text-xs text-muted">JPEG, PNG or WebP, up to 10 MB</span>
              </>
            )}
          </button>
          <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={(e) => choose(e.target.files?.[0])} />

          <button type="button" className="btn-primary" onClick={() => file && predict.mutate(file)} disabled={!file || predict.isPending}>
            {predict.isPending ? 'Diagnosing…' : 'Diagnose leaf'}
          </button>
          {predict.isError && <p className="text-xs text-alert">The diagnosis failed. Check that the backend is running, then try again.</p>}

          <ul className="flex flex-col gap-1.5 text-xs text-muted">
            <li>Fill most of the frame with the leaves you want judged.</li>
            <li>Shade or overcast light works best; avoid flash and harsh sun.</li>
            <li>Keep the photo sharp. Retake it if it's blurry.</li>
          </ul>
        </section>

        <div className="flex flex-col gap-4">
          <section className="card flex flex-col gap-5 p-5" aria-labelledby="result-title">
            <div className="flex items-start justify-between gap-3">
              <h2 id="result-title" className="text-[19px] font-semibold tracking-display">Diagnosis</h2>
              {result && <ModelStatusBadge status={result.model_status} />}
            </div>

            {result ? (
              <>
                <div className="flex flex-wrap items-center gap-5">
                  <ConfidenceGauge value={result.confidence} size={128} />
                  <div className="min-w-0">
                    <p className="text-[34px] font-light leading-tight tracking-display">{result.disease}</p>
                    <p className="num mt-1 text-sm text-muted">{result.disease_id}</p>
                  </div>
                </div>

                {result.low_confidence_warning && (
                  <p className="flex items-start gap-2 rounded-tile bg-warn-field p-3 text-sm text-warn">
                    <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
                    Low confidence. Retake the photo closer to the leaf, in shade, and diagnose again.
                  </p>
                )}

                <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                  {[
                    ['Model', result.model_version],
                    ['Architecture', 'EfficientNet-B0'],
                    ['Scanned', new Date(result.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-tile bg-tile p-3">
                      <dt className="text-xs text-muted">{k}</dt>
                      <dd className="num mt-0.5 text-sm font-semibold">{v}</dd>
                    </div>
                  ))}
                </dl>

                <Link to="/recommendations" className="btn-quiet self-start">
                  Get advice for this diagnosis <ArrowRight size={15} aria-hidden="true" />
                </Link>
              </>
            ) : (
              <p className="text-sm text-muted">
                {predict.isPending ? 'Running the model…' : 'Choose a photo and press Diagnose leaf. The result appears here.'}
              </p>
            )}

            <p className="rounded-tile bg-tile p-3 text-xs text-muted">
              How far to trust it: tomato_cv_v2.0 is 99.5% accurate on lab photos but 63% on real field photos. It is weakest on
              bacterial spot, early blight and mosaic virus.
            </p>
          </section>

          {history && history.length > 0 && (
            <section className="card p-5" aria-labelledby="history-title">
              <h2 id="history-title" className="text-[19px] font-semibold tracking-display">Recent scans</h2>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs text-muted">
                      <th className="pb-2 font-medium">Diagnosis</th>
                      <th className="pb-2 font-medium">Confidence</th>
                      <th className="pb-2 font-medium">Model</th>
                      <th className="pb-2 text-right font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody className="num">
                    {history.slice(0, 6).map((h) => (
                      <tr key={h.id} className="border-t border-line">
                        <td className="py-2.5 font-semibold">{h.disease}</td>
                        <td className={clsx('py-2.5', h.low_confidence_warning ? 'text-warn' : 'text-ink')}>{Math.round(h.confidence * 100)}%</td>
                        <td className="py-2.5 text-muted">{h.model_version}</td>
                        <td className="py-2.5 text-right text-muted">{new Date(h.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

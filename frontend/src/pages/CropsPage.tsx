import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { getCropDetail, listCrops } from '../api/crops'
import PageHeader from '../components/PageHeader'

const URGENCY: Record<string, string> = {
  low: 'bg-tile text-muted',
  medium: 'bg-warn-field text-warn',
  high: 'bg-warn-field text-warn',
  critical: 'bg-alert-field text-alert',
}

export default function CropsPage() {
  const [selected, setSelected] = useState('tomato')
  const { data: crops } = useQuery({ queryKey: ['crops'], queryFn: listCrops })
  const { data: detail, isLoading } = useQuery({
    queryKey: ['crop-detail', selected],
    queryFn: () => getCropDetail(selected),
    enabled: !!selected,
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Crops"
        description="Each crop is a module with its own disease classes, thresholds, model and knowledge base. Adding a crop doesn't change the core system."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
        <nav aria-label="Crop modules" className="card flex flex-col gap-1.5 self-start p-2">
          {crops?.map((c) => (
            <button
              key={c.id}
              type="button"
              aria-current={selected === c.id}
              onClick={() => setSelected(c.id)}
              className={clsx(
                'flex items-center justify-between gap-3 rounded-tile px-3.5 py-3 text-left transition-colors',
                selected === c.id ? 'bg-tile' : 'hover:bg-tile/60'
              )}
            >
              <span>
                <span className="block font-semibold">{c.name}</span>
                <span className="num block text-xs text-muted">v{c.version} · {c.growth_stages.length} growth stages</span>
              </span>
              <span className={clsx('chip', c.installed ? 'bg-leaf-mint text-leaf-deep' : 'bg-shell text-muted')}>
                {c.installed ? 'Active' : 'Stub'}
              </span>
            </button>
          ))}
        </nav>

        {isLoading || !detail ? (
          <div className="card h-72 animate-pulse" />
        ) : (
          <div className="flex flex-col gap-4">
            <section className="card p-6" aria-labelledby="crop-title">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 id="crop-title" className="text-[28px] font-semibold tracking-display">{detail.name}</h2>
                <span className={clsx('chip', detail.installed ? 'bg-leaf-mint text-leaf-deep' : 'bg-shell text-muted')}>
                  {detail.installed ? 'Installed' : 'Not installed'}
                </span>
              </div>
              <p className="mt-1 max-w-[72ch] text-sm text-muted">{detail.description}</p>
              <p className="mt-3 text-xs text-muted">Growth stages: {detail.growth_stages.join(' → ').replace(/_/g, ' ')}</p>
            </section>

            {detail.thresholds && (
              <section className="card p-6" aria-labelledby="thresholds-title">
                <h2 id="thresholds-title" className="text-[19px] font-semibold tracking-display">Optimal ranges</h2>
                <dl className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  {Object.entries(detail.thresholds).map(([key, v]) =>
                    typeof v === 'object' && v.optimal_min != null ? (
                      <div key={key} className="rounded-tile bg-tile p-4">
                        <dt className="flex items-baseline justify-between gap-3">
                          <span className="font-semibold capitalize">{key}</span>
                          <span className="num text-sm font-semibold text-leaf-deep">
                            {v.optimal_min}–{v.optimal_max} {v.unit}
                          </span>
                        </dt>
                        {v.notes && <dd className="mt-1 text-xs text-muted">{v.notes}</dd>}
                      </div>
                    ) : null
                  )}
                </dl>
              </section>
            )}

            {detail.disease_classes && (
              <section className="card p-6" aria-labelledby="classes-title">
                <h2 id="classes-title" className="text-[19px] font-semibold tracking-display">
                  Disease classes <span className="num font-normal text-muted">({detail.disease_classes.length})</span>
                </h2>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[520px] text-left text-sm">
                    <thead>
                      <tr className="text-xs text-muted">
                        <th className="pb-2 font-medium">Class</th>
                        <th className="pb-2 font-medium">Cause</th>
                        <th className="pb-2 text-right font-medium">Treatment urgency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.disease_classes.map((c) => (
                        <tr key={c.id} className="border-t border-line">
                          <td className="py-2.5 font-semibold">
                            <span className={clsx('mr-2 inline-block h-2 w-2 rounded-full', c.is_healthy ? 'bg-leaf' : 'bg-ink')} aria-hidden="true" />
                            {c.display}
                          </td>
                          <td className="py-2.5 italic text-muted">{c.causative_agent ?? (c.is_healthy ? '—' : c.pathogen_type)}</td>
                          <td className="py-2.5 text-right">
                            {c.is_healthy ? (
                              <span className="text-xs text-muted">—</span>
                            ) : (
                              <span className={clsx('chip capitalize', URGENCY[c.treatment_urgency] ?? 'bg-tile text-muted')}>{c.treatment_urgency}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

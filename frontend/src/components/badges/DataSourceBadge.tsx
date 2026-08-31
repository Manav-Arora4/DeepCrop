import React from 'react'
import clsx from 'clsx'

interface Props {
  source: 'real' | 'simulated' | 'manual' | string
  className?: string
}

const CONFIG = {
  real: { label: 'Real ESP32 Hardware', className: 'bg-emerald-50 text-emerald-700 border-emerald-200 ring-1 ring-emerald-500/20' },
  simulated: { label: 'Simulated Synthetic', className: 'bg-amber-50 text-amber-700 border-amber-200 ring-1 ring-amber-500/20' },
  manual: { label: 'Manual Entry', className: 'bg-sky-50 text-sky-700 border-sky-200 ring-1 ring-sky-500/20' },
}

export default function DataSourceBadge({ source, className }: Props) {
  const cfg = CONFIG[source as keyof typeof CONFIG] ?? {
    label: source,
    className: 'bg-slate-100 text-slate-700 border-slate-200',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-all',
        cfg.className,
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {cfg.label}
    </span>
  )
}

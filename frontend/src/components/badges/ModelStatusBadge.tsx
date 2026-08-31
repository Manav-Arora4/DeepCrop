import React from 'react'
import clsx from 'clsx'

interface Props {
  status: 'ready' | 'demo' | 'unavailable' | 'error' | string
  className?: string
}

const CONFIG = {
  ready: { label: 'PyTorch Weights Active', className: 'bg-emerald-50 text-emerald-700 border-emerald-300 ring-1 ring-emerald-500/20' },
  demo: { label: 'Demo Simulator Mode', className: 'bg-amber-50 text-amber-700 border-amber-300 ring-1 ring-amber-500/20' },
  unavailable: { label: 'Model Missing', className: 'bg-slate-100 text-slate-700 border-slate-300' },
  error: { label: 'Inference Error', className: 'bg-rose-50 text-rose-700 border-rose-300 ring-1 ring-rose-500/20' },
}

export default function ModelStatusBadge({ status, className }: Props) {
  const cfg = CONFIG[status as keyof typeof CONFIG] ?? {
    label: status,
    className: 'bg-slate-100 text-slate-700 border-slate-200',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border',
        cfg.className,
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {cfg.label}
    </span>
  )
}

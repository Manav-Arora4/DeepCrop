import React from 'react'
import clsx from 'clsx'
import type { ThresholdValue } from '../../api/types'

interface Props {
  title: string
  value: number | null
  threshold?: ThresholdValue
  icon: string
  description?: string
}

const THEME = {
  OPTIMAL: {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    card: 'border-emerald-200 bg-white hover:border-emerald-300',
    val: 'text-slate-900',
    indicator: 'bg-emerald-500',
  },
  LOW: {
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    card: 'border-amber-200 bg-white hover:border-amber-300',
    val: 'text-amber-900',
    indicator: 'bg-amber-500',
  },
  HIGH: {
    badge: 'bg-rose-100 text-rose-800 border-rose-300',
    card: 'border-rose-200 bg-white hover:border-rose-300',
    val: 'text-rose-900',
    indicator: 'bg-rose-500',
  },
  UNKNOWN: {
    badge: 'bg-slate-100 text-slate-700 border-slate-300',
    card: 'border-slate-200 bg-white hover:border-slate-300',
    val: 'text-slate-500',
    indicator: 'bg-slate-400',
  },
}

export default function SensorCard({ title, value, threshold, icon, description }: Props) {
  const status = threshold?.status ?? 'UNKNOWN'
  const unit = threshold?.unit ?? ''
  const t = THEME[status]

  return (
    <div className={clsx('rounded-2xl border p-5 shadow-sm transition-all duration-200 flex flex-col justify-between', t.card)}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl p-2 rounded-xl bg-slate-50 border border-slate-100">{icon}</span>
          <div>
            <h4 className="text-sm font-semibold text-slate-700">{title}</h4>
            {description && <p className="text-xs text-slate-400">{description}</p>}
          </div>
        </div>
        <span className={clsx('text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border', t.badge)}>
          {status}
        </span>
      </div>

      <div className="flex items-baseline justify-between mt-2">
        <div className="text-3xl font-extrabold tracking-tight text-slate-900">
          {value !== null && value !== undefined ? `${value}` : '—'}
          <span className="text-lg font-semibold text-slate-400 ml-1">{unit}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <span className={clsx('h-2 w-2 rounded-full animate-pulse', t.indicator)} />
          Live
        </div>
      </div>
    </div>
  )
}

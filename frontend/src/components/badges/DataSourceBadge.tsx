import React from 'react'
import clsx from 'clsx'

interface Props {
  source: 'real' | 'simulated' | 'manual' | string
  className?: string
}

const CONFIG = {
  real: { label: 'Live ESP32', className: 'bg-leaf-mint text-leaf-deep', dot: 'bg-leaf' },
  simulated: { label: 'Simulated', className: 'bg-warn-field text-warn', dot: 'bg-warn' },
  manual: { label: 'Manual entry', className: 'bg-tile text-muted', dot: 'bg-faint' },
}

export default function DataSourceBadge({ source, className }: Props) {
  const cfg = CONFIG[source as keyof typeof CONFIG] ?? { label: source, className: 'bg-tile text-muted', dot: 'bg-faint' }
  return (
    <span className={clsx('chip', cfg.className, className)}>
      <span className={clsx('h-1.5 w-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}

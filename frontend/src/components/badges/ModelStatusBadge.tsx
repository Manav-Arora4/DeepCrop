import React from 'react'
import clsx from 'clsx'

interface Props {
  status: 'ready' | 'demo' | 'unavailable' | 'error' | string
  className?: string
}

const CONFIG = {
  ready: { label: 'Trained model', className: 'bg-leaf-mint text-leaf-deep', dot: 'bg-leaf' },
  demo: { label: 'Demo model', className: 'bg-warn-field text-warn', dot: 'bg-warn' },
  unavailable: { label: 'Model missing', className: 'bg-tile text-muted', dot: 'bg-faint' },
  error: { label: 'Inference error', className: 'bg-alert-field text-alert', dot: 'bg-alert' },
}

export default function ModelStatusBadge({ status, className }: Props) {
  const cfg = CONFIG[status as keyof typeof CONFIG] ?? { label: status, className: 'bg-tile text-muted', dot: 'bg-faint' }
  return (
    <span className={clsx('chip', cfg.className, className)}>
      <span className={clsx('h-1.5 w-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}

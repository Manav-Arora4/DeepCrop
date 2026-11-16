import React from 'react'

interface Props {
  title: string
  description: React.ReactNode
  actions?: React.ReactNode
}

export default function PageHeader({ title, description, actions }: Props) {
  return (
    <div className="flex flex-col gap-4 pb-2 pt-3 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        <h1 className="text-[32px] font-semibold leading-tight tracking-display text-ink">{title}</h1>
        <p className="mt-1 text-[15px] text-muted">{description}</p>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

import React from 'react'

interface Props {
  value: number // 0–1
  size?: number
}

// 240° arc open at the bottom, like an instrument dial
export default function ConfidenceGauge({ value, size = 110 }: Props) {
  const r = 44
  const c = 2 * Math.PI * r
  const arc = c * (240 / 360)
  const pct = Math.round(value * 100)
  return (
    <svg viewBox="0 0 110 110" width={size} height={size} className="shrink-0" role="img" aria-label={`Confidence ${pct} percent`}>
      <g transform="rotate(150 55 55)">
        <circle cx="55" cy="55" r={r} fill="none" stroke="#E3E8E0" strokeWidth="9" strokeLinecap="round" strokeDasharray={`${arc} ${c}`} />
        <circle
          cx="55" cy="55" r={r} fill="none" stroke={value < 0.65 ? '#B26B00' : '#22C55E'} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={`${arc * value} ${c}`}
          style={{ transition: 'stroke-dasharray 700ms cubic-bezier(0.16, 1, 0.3, 1)' }}
        />
      </g>
      <text x="55" y="58" textAnchor="middle" className="num fill-ink" style={{ fontSize: 26, fontWeight: 300, letterSpacing: '-0.03em' }}>
        {pct}
      </text>
      <text x="55" y="76" textAnchor="middle" className="fill-muted" style={{ fontSize: 10, fontWeight: 500 }}>
        % confidence
      </text>
    </svg>
  )
}

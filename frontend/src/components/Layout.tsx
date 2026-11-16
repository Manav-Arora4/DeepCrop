import React from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { apiClient } from '../api/client'

const navItems = [
  { to: '/dashboard', label: 'Overview' },
  { to: '/sensors', label: 'Sensors' },
  { to: '/cv', label: 'Leaf scan' },
  { to: '/recommendations', label: 'Advisor' },
  { to: '/crops', label: 'Crops' },
]

export const PLANT_ID = 'plant_01'
export const CROP_ID = 'tomato'

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      {/* Three leaflets: the tomato compound leaf, drawn as geometry */}
      <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
        <path d="M15 4c4 3 4.6 8 0 12-4.6-4-4-9 0-12z" fill="#141814" />
        <path d="M5 15c4.8-1 9 1.6 10 6.6-4.8 1.2-9.2-1.4-10-6.6z" fill="#141814" />
        <path d="M25 15c-4.8-1-9 1.6-10 6.6 4.8 1.2 9.2-1.4 10-6.6z" fill="#22C55E" />
        <path d="M15 16v10" stroke="#141814" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className="text-[17px] font-bold tracking-display text-ink">DeepCrop</span>
    </div>
  )
}

function ApiStatus() {
  const { isSuccess, isError, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await apiClient.get('/health')).data,
    refetchInterval: 15_000,
    retry: false,
  })
  const label = isLoading ? 'Connecting…' : isSuccess ? 'API online' : 'API offline'
  return (
    <span className={clsx('chip', isError ? 'bg-alert-field text-alert' : 'bg-card text-muted')}>
      <span className={clsx('h-1.5 w-1.5 rounded-full', isError ? 'bg-alert' : isSuccess ? 'bg-leaf' : 'bg-faint')} />
      {label}
    </span>
  )
}

export default function Layout() {
  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-20 bg-canvas/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1520px] flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-4 sm:px-6 lg:px-8">
          <Wordmark />

          <nav aria-label="Main" className="order-3 w-full overflow-x-auto [mask-image:linear-gradient(to_right,black_92%,transparent)] sm:[mask-image:none] md:order-none md:w-auto">
            <ul className="flex w-max gap-1 rounded-full bg-shell p-1">
              {navItems.map(({ to, label }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    className={({ isActive }) =>
                      clsx(
                        'block rounded-full px-2 py-2 text-[13px] font-medium transition-colors sm:px-4 sm:text-sm',
                        isActive ? 'bg-card text-ink shadow-card' : 'text-muted hover:text-ink'
                      )
                    }
                  >
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="flex items-center gap-2">
            <span className="chip bg-card text-ink">
              Tomato <span className="text-faint">·</span> <span className="num">{PLANT_ID}</span>
            </span>
            <ApiStatus />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1520px] px-4 pb-10 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}

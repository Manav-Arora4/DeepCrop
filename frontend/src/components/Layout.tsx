import React from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, Camera, Sparkles, Layers, ShieldCheck } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', desc: 'System overview & live telemetry' },
  { to: '/sensors', icon: Activity, label: 'IoT Sensors', desc: 'Real-time & historic time-series' },
  { to: '/cv', icon: Camera, label: 'Computer Vision', desc: 'EfficientNetB0 leaf disease diagnosis' },
  { to: '/recommendations', icon: Sparkles, label: 'AI Advisory (RAG)', desc: 'Grounded LLM agronomic support' },
  { to: '/crops', icon: Layers, label: 'Crop Modules', desc: 'Modular crop configurations' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-72 bg-slate-900 text-white flex flex-col border-r border-slate-800 shrink-0">
        <div className="p-6 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <span className="text-xl">🌿</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">AgriHealth AI</h1>
              <p className="text-xs text-emerald-400 font-medium tracking-wide uppercase">Multimodal Platform</p>
            </div>
          </div>
        </div>

        <div className="px-4 py-3">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3">Navigation</span>
        </div>

        <nav className="flex-1 px-3 space-y-1.5 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label, desc }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-sm font-medium transition-all group',
                  isActive
                    ? 'bg-emerald-600/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent'
                )
              }
            >
              <Icon size={20} className="shrink-0 transition-transform group-hover:scale-110 text-emerald-400" />
              <div className="flex flex-col">
                <span className="leading-tight">{label}</span>
                <span className="text-[11px] text-slate-400 font-normal mt-0.5">{desc}</span>
              </div>
            </NavLink>
          ))}
        </nav>

        {/* Academic Project Footer */}
        <div className="p-4 m-3 rounded-xl bg-slate-800/60 border border-slate-700/50 text-xs text-slate-300 space-y-1">
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
            <ShieldCheck size={14} />
            <span>Academic Rigor Active</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Leaf-ID split CV • Multi-modal risk fusion • RAG grounded
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto bg-slate-50">
        <header className="h-16 border-b border-slate-200/80 bg-white/80 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-10 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
              Active Module: <strong className="text-slate-900">Tomato (Solanum lycopersicum)</strong>
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
              Plot: <strong className="text-slate-900">plant_01</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
              API Server Connected
            </span>
          </div>
        </header>

        <div className="flex-1 p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

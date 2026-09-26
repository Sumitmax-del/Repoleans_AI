import { useState } from 'react'
import type { ArchComponent, ArchLayer } from '../types'

// ── Component card colors ────────────────────────────────────────────────────

const ROLE_COLORS: Record<string, { ring: string; bg: string; text: string; dot: string; hover: string }> = {
  'Web Framework':   { ring: 'border-blue-500/30',   bg: 'bg-blue-500/10',   text: 'text-blue-300',   dot: 'bg-blue-400',   hover: 'hover:border-blue-400/60 hover:shadow-[0_0_15px_rgba(59,130,246,0.2)]' },
  'ASGI Foundation': { ring: 'border-sky-500/30',    bg: 'bg-sky-500/10',    text: 'text-sky-300',    dot: 'bg-sky-400',    hover: 'hover:border-sky-400/60 hover:shadow-[0_0_15px_rgba(14,165,233,0.2)]' },
  'Data Validation': { ring: 'border-purple-500/30', bg: 'bg-purple-500/10', text: 'text-purple-300', dot: 'bg-purple-400', hover: 'hover:border-purple-400/60 hover:shadow-[0_0_15px_rgba(168,85,247,0.2)]' },
  'Test Runner':     { ring: 'border-green-500/30',  bg: 'bg-green-500/10',  text: 'text-green-300',  dot: 'bg-green-400',  hover: 'hover:border-green-400/60 hover:shadow-[0_0_15px_rgba(34,197,94,0.2)]' },
  'ORM':             { ring: 'border-orange-500/30', bg: 'bg-orange-500/10', text: 'text-orange-300', dot: 'bg-orange-400', hover: 'hover:border-orange-400/60 hover:shadow-[0_0_15px_rgba(249,115,22,0.2)]' },
  'Task Queue':      { ring: 'border-red-500/30',    bg: 'bg-red-500/10',    text: 'text-red-300',    dot: 'bg-red-400',    hover: 'hover:border-red-400/60 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]' },
  'UI Library':      { ring: 'border-cyan-500/30',   bg: 'bg-cyan-500/10',   text: 'text-cyan-300',   dot: 'bg-cyan-400',   hover: 'hover:border-cyan-400/60 hover:shadow-[0_0_15px_rgba(6,182,212,0.2)]' },
  'Build Tool':      { ring: 'border-gray-500/30',   bg: 'bg-gray-500/10',   text: 'text-gray-300',   dot: 'bg-gray-400',   hover: 'hover:border-gray-400/60 hover:shadow-[0_0_15px_rgba(156,163,175,0.2)]' },
}

const FLOW_LAYER_COLORS: Record<string, {
  border: string; bg: string; label: string; nodeBorder: string; nodeBg: string; nodeText: string; filePill: string; glow: string
}> = {
  blue:   { border: 'border-blue-500/30',   bg: 'bg-blue-500/5',   label: 'text-blue-400',   nodeBorder: 'border-blue-500/30',   nodeBg: 'bg-blue-950/40',   nodeText: 'text-blue-200',   filePill: 'bg-blue-500/10 text-blue-300 border-blue-500/30', glow: 'hover:border-blue-400 hover:shadow-[0_0_15px_rgba(59,130,246,0.25)]' },
  sky:    { border: 'border-sky-500/30',    bg: 'bg-sky-500/5',    label: 'text-sky-400',    nodeBorder: 'border-sky-500/30',    nodeBg: 'bg-sky-950/40',    nodeText: 'text-sky-200',    filePill: 'bg-sky-500/10 text-sky-300 border-sky-500/30', glow: 'hover:border-sky-400 hover:shadow-[0_0_15px_rgba(14,165,233,0.25)]' },
  purple: { border: 'border-purple-500/30', bg: 'bg-purple-500/5', label: 'text-purple-400', nodeBorder: 'border-purple-500/30', nodeBg: 'bg-purple-950/40', nodeText: 'text-purple-200', filePill: 'bg-purple-500/10 text-purple-300 border-purple-500/30', glow: 'hover:border-purple-400 hover:shadow-[0_0_15px_rgba(168,85,247,0.25)]' },
  orange: { border: 'border-orange-500/30', bg: 'bg-orange-500/5', label: 'text-orange-400', nodeBorder: 'border-orange-500/30', nodeBg: 'bg-orange-950/40', nodeText: 'text-orange-200', filePill: 'bg-orange-500/10 text-orange-300 border-orange-500/30', glow: 'hover:border-orange-400 hover:shadow-[0_0_15px_rgba(249,115,22,0.25)]' },
  green:  { border: 'border-green-500/30',  bg: 'bg-green-500/5',  label: 'text-green-400',  nodeBorder: 'border-green-500/30',  nodeBg: 'bg-green-950/40',  nodeText: 'text-green-200',  filePill: 'bg-green-500/10 text-green-300 border-green-500/30', glow: 'hover:border-green-400 hover:shadow-[0_0_15px_rgba(34,197,94,0.25)]' },
  gray:   { border: 'border-gray-500/30',   bg: 'bg-gray-500/5',   label: 'text-gray-400',   nodeBorder: 'border-gray-500/30',   nodeBg: 'bg-gray-900/60',   nodeText: 'text-gray-200',   filePill: 'bg-gray-500/10 text-gray-300 border-gray-500/30', glow: 'hover:border-gray-400 hover:shadow-[0_0_15px_rgba(156,163,175,0.25)]' },
}

const DEFAULT_ROLE_COLOR = { ring: 'border-gray-500/30', bg: 'bg-gray-500/10', text: 'text-gray-300', dot: 'bg-gray-400', hover: 'hover:border-gray-400/60 hover:shadow-[0_0_15px_rgba(156,163,175,0.2)]' }

function roleColor(role: string) {
  return ROLE_COLORS[role] ?? DEFAULT_ROLE_COLOR
}

// ── Props ────────────────────────────────────────────────────────────────────

interface Props {
  components: ArchComponent[]
  flowLayers?: ArchLayer[]
}

type ViewMode = 'flow' | 'components'

// ── Main component ───────────────────────────────────────────────────────────

export default function ArchitectureView({ components, flowLayers }: Props) {
  const [view, setView] = useState<ViewMode>(flowLayers && flowLayers.length > 0 ? 'flow' : 'components')

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl shadow-black/30 animate-fade-in relative overflow-hidden">
      {/* Subtle top ambient gradient line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

      {/* Header + view toggle */}
      <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
        <SectionHeader />
        {flowLayers && flowLayers.length > 0 && (
          <div className="flex items-center gap-1 bg-gray-950/80 border border-white/[0.08] rounded-xl p-1 shrink-0 shadow-inner">
            <TabBtn active={view === 'flow'} onClick={() => setView('flow')}>Project Flow</TabBtn>
            <TabBtn active={view === 'components'} onClick={() => setView('components')}>Components</TabBtn>
          </div>
        )}
      </div>

      {view === 'flow' && flowLayers && flowLayers.length > 0 ? (
        <FlowDiagram layers={flowLayers} />
      ) : (
        <ComponentsView components={components} />
      )}
    </div>
  )
}

// ── Tab button ───────────────────────────────────────────────────────────────

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-3.5 py-1 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95',
        active
          ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
          : 'text-gray-400 hover:text-white hover:bg-white/[0.05]',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

// ── Project Flow diagram ─────────────────────────────────────────────────────

function FlowDiagram({ layers }: { layers: ArchLayer[] }) {
  const [hovered, setHovered] = useState<string | null>(null)

  return (
    <div>
      {/* Horizontal scroll wrapper */}
      <div className="overflow-x-auto pb-4 pt-1">
        <div className="flex items-stretch gap-0 min-w-max">
          {layers.map((layer, idx) => {
            const c = FLOW_LAYER_COLORS[layer.color] ?? FLOW_LAYER_COLORS.gray
            return (
              <div key={layer.id} className="flex items-stretch gap-0">
                {/* Layer column */}
                <div
                  className={`border ${c.border} ${c.bg} rounded-2xl p-3.5 min-w-[175px] max-w-[215px] flex flex-col gap-3 shadow-lg shadow-black/20 transition-all duration-200 backdrop-blur-md`}
                >
                  {/* Layer label */}
                  <div className={`text-xs font-semibold uppercase tracking-wider ${c.label} mb-0.5 flex items-center gap-2`}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current shadow-[0_0_6px_currentColor]" />
                    {layer.label}
                  </div>

                  {/* Nodes */}
                  {layer.nodes.map((node) => {
                    const nodeKey = `${layer.id}/${node.name}`
                    const isHovered = hovered === nodeKey
                    return (
                      <div
                        key={node.name}
                        onMouseEnter={() => setHovered(nodeKey)}
                        onMouseLeave={() => setHovered(null)}
                        className={[
                          'border rounded-xl p-3 cursor-default transition-all duration-200',
                          'hover:-translate-y-1 hover:shadow-lg',
                          c.nodeBorder,
                          c.glow,
                          isHovered ? 'bg-gray-800/95 ring-1 ring-blue-500/40' : c.nodeBg,
                        ].join(' ')}
                      >
                        <p className={`text-sm font-semibold leading-tight ${c.nodeText}`}>
                          {node.name}
                        </p>
                        <p className="text-xs text-gray-400 mt-1 leading-snug">
                          {node.description}
                        </p>
                        {/* File pill */}
                        <div className="mt-2.5">
                          <span className={`inline-block text-xs font-mono px-2 py-0.5 rounded-md border ${c.filePill} truncate max-w-full shadow-xs transition-colors`}>
                            {node.file.split('/').pop()}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Connector arrow between layers */}
                {idx < layers.length - 1 && (
                  <div className="flex items-center px-2.5 shrink-0">
                    <div className="flex items-center justify-center w-7 h-7 rounded-full bg-gray-900/90 border border-white/[0.08] shadow-sm">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-blue-400 drop-shadow-[0_0_6px_rgba(96,165,250,0.5)]">
                        <path d="M5 12h14M13 6l6 6-6 6"
                          stroke="currentColor" strokeWidth="2"
                          strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Request / response annotation */}
      <div className="mt-3 flex items-center gap-3 text-xs text-gray-400 border-t border-white/[0.08] pt-3.5 flex-wrap">
        <div className="flex items-center gap-1.5 bg-gray-900/60 border border-white/[0.06] px-2.5 py-1 rounded-lg">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-blue-400 shrink-0">
            <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>Request flow: left → right</span>
        </div>
        <span className="text-gray-700">·</span>
        <div className="flex items-center gap-1.5 bg-gray-900/60 border border-white/[0.06] px-2.5 py-1 rounded-lg">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-purple-400 shrink-0">
            <path d="M19 12H5M11 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>Response flows in reverse</span>
        </div>
      </div>
    </div>
  )
}

// ── Components grid view ─────────────────────────────────────────────────────

function ComponentsView({ components }: { components: ArchComponent[] }) {
  if (components.length === 0) {
    return <p className="text-sm text-gray-500 italic">No components detected.</p>
  }

  return (
    <>
      <div className="flex items-start gap-3 overflow-x-auto pb-3.5 pt-1">
        {components.map((comp, idx) => {
          const c = roleColor(comp.role)
          return (
            <div key={comp.name} className="flex items-center gap-3 shrink-0">
              <div className={`border ${c.ring} ${c.bg} ${c.hover} rounded-2xl px-4 py-4 min-w-[155px] max-w-[195px] shadow-lg shadow-black/20 transition-all duration-200 hover:-translate-y-1 hover:shadow-xl cursor-default group backdrop-blur-md`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${c.dot} shadow-[0_0_8px_currentColor]`} />
                  <span className={`text-sm font-semibold ${c.text} group-hover:text-white transition-colors`}>{comp.name}</span>
                </div>
                <p className="text-xs text-gray-400 mb-2.5 font-medium">{comp.role}</p>
                <div className="space-y-1.5">
                  {comp.files.slice(0, 2).map((f) => {
                    const short = f.split('/').pop() ?? f
                    return (
                      <p key={f} className="text-xs font-mono text-gray-400 truncate bg-gray-950/60 px-2 py-0.5 rounded-md border border-white/[0.04]" title={f}>
                        {short}
                      </p>
                    )
                  })}
                </div>
              </div>
              {idx < components.length - 1 && (
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-gray-900/90 border border-white/[0.08] shrink-0">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-gray-400">
                    <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2"
                      strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-white/[0.08] flex flex-wrap gap-2.5">
        {components.map((comp) => {
          const c = roleColor(comp.role)
          return (
            <span key={comp.name} className="flex items-center gap-1.5 text-xs text-gray-400 bg-gray-900/60 px-3 py-1 rounded-full border border-white/[0.06] transition-colors hover:border-white/[0.15]">
              <span className={`inline-block w-2 h-2 rounded-full ${c.dot} shadow-[0_0_6px_currentColor]`} />
              <span className="font-semibold text-gray-200">{comp.name}</span>
              <span className="text-gray-600">·</span>
              <span>{comp.role}</span>
            </span>
          )
        })}
      </div>
    </>
  )
}

// ── Section header ───────────────────────────────────────────────────────────

function SectionHeader() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-blue-400">
          <rect x="3"  y="3"  width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.8" />
          <rect x="14" y="3"  width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.8" />
          <rect x="3"  y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.8" />
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.8" />
        </svg>
      </div>
      <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
        Architecture / Project Flow
      </p>
    </div>
  )
}

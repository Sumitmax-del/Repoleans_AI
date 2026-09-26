import { useState } from 'react'
import type { ArchComponent, ArchLayer } from '../types'

// ── Component card colors ────────────────────────────────────────────────────

const ROLE_COLORS: Record<string, { ring: string; bg: string; text: string; dot: string }> = {
  'Web Framework':   { ring: 'border-blue-600/60',   bg: 'bg-blue-950/50',   text: 'text-blue-300',   dot: 'bg-blue-500'   },
  'ASGI Foundation': { ring: 'border-sky-600/60',    bg: 'bg-sky-950/50',    text: 'text-sky-300',    dot: 'bg-sky-500'    },
  'Data Validation': { ring: 'border-purple-600/60', bg: 'bg-purple-950/50', text: 'text-purple-300', dot: 'bg-purple-500' },
  'Test Runner':     { ring: 'border-green-600/60',  bg: 'bg-green-950/50',  text: 'text-green-300',  dot: 'bg-green-500'  },
  'ORM':             { ring: 'border-orange-600/60', bg: 'bg-orange-950/50', text: 'text-orange-300', dot: 'bg-orange-500' },
  'Task Queue':      { ring: 'border-red-600/60',    bg: 'bg-red-950/50',    text: 'text-red-300',    dot: 'bg-red-500'    },
  'UI Library':      { ring: 'border-cyan-600/60',   bg: 'bg-cyan-950/50',   text: 'text-cyan-300',   dot: 'bg-cyan-500'   },
  'Build Tool':      { ring: 'border-gray-600/60',   bg: 'bg-gray-800/50',   text: 'text-gray-300',   dot: 'bg-gray-500'   },
}

const FLOW_LAYER_COLORS: Record<string, {
  border: string; bg: string; label: string; nodeBorder: string; nodeBg: string; nodeText: string; filePill: string
}> = {
  blue:   { border: 'border-blue-700/60',   bg: 'bg-blue-950/30',   label: 'text-blue-400',   nodeBorder: 'border-blue-600/50',   nodeBg: 'bg-blue-900/40',   nodeText: 'text-blue-200',   filePill: 'bg-blue-900/60 text-blue-400 border-blue-700/50'   },
  sky:    { border: 'border-sky-700/60',    bg: 'bg-sky-950/30',    label: 'text-sky-400',    nodeBorder: 'border-sky-600/50',    nodeBg: 'bg-sky-900/40',    nodeText: 'text-sky-200',    filePill: 'bg-sky-900/60 text-sky-400 border-sky-700/50'    },
  purple: { border: 'border-purple-700/60', bg: 'bg-purple-950/30', label: 'text-purple-400', nodeBorder: 'border-purple-600/50', nodeBg: 'bg-purple-900/40', nodeText: 'text-purple-200', filePill: 'bg-purple-900/60 text-purple-400 border-purple-700/50' },
  orange: { border: 'border-orange-700/60', bg: 'bg-orange-950/30', label: 'text-orange-400', nodeBorder: 'border-orange-600/50', nodeBg: 'bg-orange-900/40', nodeText: 'text-orange-200', filePill: 'bg-orange-900/60 text-orange-400 border-orange-700/50' },
  green:  { border: 'border-green-700/60',  bg: 'bg-green-950/30',  label: 'text-green-400',  nodeBorder: 'border-green-600/50',  nodeBg: 'bg-green-900/40',  nodeText: 'text-green-200',  filePill: 'bg-green-900/60 text-green-400 border-green-700/50'  },
  gray:   { border: 'border-gray-700/60',   bg: 'bg-gray-800/30',   label: 'text-gray-400',   nodeBorder: 'border-gray-600/50',   nodeBg: 'bg-gray-800/40',   nodeText: 'text-gray-200',   filePill: 'bg-gray-800/60 text-gray-400 border-gray-700/50'   },
}

const DEFAULT_ROLE_COLOR = { ring: 'border-gray-600/60', bg: 'bg-gray-800/50', text: 'text-gray-300', dot: 'bg-gray-500' }

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
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      {/* Header + view toggle */}
      <div className="flex items-center justify-between gap-4 mb-4">
        <SectionHeader />
        {flowLayers && flowLayers.length > 0 && (
          <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1 shrink-0">
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
        'px-3 py-1 rounded-md text-xs font-medium transition',
        active
          ? 'bg-gray-700 text-white'
          : 'text-gray-500 hover:text-gray-300',
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
      <div className="overflow-x-auto pb-3">
        <div className="flex items-stretch gap-0 min-w-max">
          {layers.map((layer, idx) => {
            const c = FLOW_LAYER_COLORS[layer.color]
            return (
              <div key={layer.id} className="flex items-stretch gap-0">
                {/* Layer column */}
                <div
                  className={`border ${c.border} ${c.bg} rounded-xl p-3 min-w-[160px] max-w-[200px] flex flex-col gap-2`}
                >
                  {/* Layer label */}
                  <div className={`text-xs font-semibold uppercase tracking-wider ${c.label} mb-1`}>
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
                          'border rounded-lg p-2.5 cursor-default transition-all',
                          c.nodeBorder,
                          isHovered ? 'bg-gray-700/60' : c.nodeBg,
                        ].join(' ')}
                      >
                        <p className={`text-sm font-semibold leading-tight ${c.nodeText}`}>
                          {node.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 leading-snug">
                          {node.description}
                        </p>
                        {/* File pill */}
                        <div className="mt-2">
                          <span className={`inline-block text-xs font-mono px-1.5 py-0.5 rounded border ${c.filePill} truncate max-w-full`}>
                            {node.file.split('/').pop()}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Connector arrow between layers */}
                {idx < layers.length - 1 && (
                  <div className="flex items-center px-1 shrink-0">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" className="text-gray-600">
                      <path d="M5 12h14M13 6l6 6-6 6"
                        stroke="currentColor" strokeWidth="1.5"
                        strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Request / response annotation */}
      <div className="mt-3 flex items-center gap-3 text-xs text-gray-600 border-t border-gray-800 pt-3">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="shrink-0">
          <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span>Request flow: left → right</span>
        <span className="ml-4 flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="shrink-0">
            <path d="M19 12H5M11 18l-6-6 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Response flows in reverse
        </span>
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
      <div className="flex items-start gap-2 overflow-x-auto pb-2">
        {components.map((comp, idx) => {
          const c = roleColor(comp.role)
          return (
            <div key={comp.name} className="flex items-center gap-2 shrink-0">
              <div className={`border ${c.ring} ${c.bg} rounded-xl px-4 py-3 min-w-[140px] max-w-[180px]`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${c.dot}`} />
                  <span className={`text-sm font-semibold ${c.text}`}>{comp.name}</span>
                </div>
                <p className="text-xs text-gray-500 mb-2">{comp.role}</p>
                {comp.files.slice(0, 2).map((f) => {
                  const short = f.split('/').pop() ?? f
                  return (
                    <p key={f} className="text-xs font-mono text-gray-400 truncate" title={f}>
                      {short}
                    </p>
                  )
                })}
              </div>
              {idx < components.length - 1 && (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-gray-600 shrink-0">
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.5"
                    strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-800 flex flex-wrap gap-3">
        {components.map((comp) => {
          const c = roleColor(comp.role)
          return (
            <span key={comp.name} className="flex items-center gap-1.5 text-xs text-gray-400">
              <span className={`inline-block w-2 h-2 rounded-full ${c.dot}`} />
              <span className="font-semibold text-gray-300">{comp.name}</span>
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
    <div className="flex items-center gap-2">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-gray-400 shrink-0">
        <rect x="3"  y="3"  width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <rect x="14" y="3"  width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <rect x="3"  y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.5" />
      </svg>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        Architecture / Project Flow
      </p>
    </div>
  )
}

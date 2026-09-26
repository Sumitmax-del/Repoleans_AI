import { useState } from 'react'
import type { FileNode } from '../types'

interface Props {
  root: FileNode
}

export default function FileExplorer({ root }: Props) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [copiedPath, setCopiedPath] = useState<string | null>(null)

  function handleCopy(path: string) {
    navigator.clipboard.writeText(path).then(() => {
      setCopiedPath(path)
      setTimeout(() => setCopiedPath(null), 1500)
    }).catch(() => {})
  }

  // Filter helper: returns true if node or any of its children match filter
  const matchesFilter = (node: FileNode, q: string): boolean => {
    if (!q) return true
    if (node.name.toLowerCase().includes(q.toLowerCase())) return true
    if (node.children) {
      return node.children.some((c) => matchesFilter(c, q))
    }
    return false
  }

  return (
    <div className="bg-gray-950/70 backdrop-blur-xl border border-white/[0.08] rounded-2xl overflow-hidden h-full flex flex-col shadow-xl shadow-black/30">
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-white/[0.08] shrink-0 flex items-center justify-between gap-2 bg-gray-900/50">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 rounded-md bg-blue-500/10 flex items-center justify-center">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="text-blue-400">
              <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke="currentColor" strokeWidth="2" />
            </svg>
          </div>
          <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">File Explorer</p>
        </div>
        {selectedPath && (
          <button
            onClick={() => handleCopy(selectedPath)}
            title="Copy selected path"
            className="text-xs font-mono text-gray-400 hover:text-blue-300 transition-colors px-2 py-0.5 rounded-md bg-gray-800/80 border border-white/[0.06] hover:border-blue-500/30 flex items-center gap-1.5 active:scale-95 shadow-xs"
          >
            {copiedPath === selectedPath ? (
              <span className="text-emerald-400 flex items-center gap-1 text-[11px] font-semibold">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Copied
              </span>
            ) : (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                  <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="2" />
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" strokeWidth="2" />
                </svg>
                <span className="text-[11px]">Copy</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Filter search input */}
      <div className="p-2.5 border-b border-white/[0.06] bg-gray-900/30">
        <div className="relative">
          <svg
            width="12" height="12" viewBox="0 0 24 24" fill="none"
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter files…"
            className="w-full pl-7 pr-6 py-1.5 text-xs rounded-lg border border-white/[0.08] bg-gray-900/90
                       text-gray-200 placeholder-gray-500 outline-none transition-all duration-150
                       focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/30 focus:bg-gray-900"
          />
          {filter && (
            <button
              onClick={() => setFilter('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto p-2 text-sm select-none">
        {root.children?.filter((node) => matchesFilter(node, filter)).map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            depth={0}
            selectedPath={selectedPath}
            onSelect={setSelectedPath}
            onCopy={handleCopy}
            copiedPath={copiedPath}
            filterQuery={filter}
          />
        ))}
      </div>
    </div>
  )
}

function TreeNode({
  node,
  depth,
  selectedPath,
  onSelect,
  onCopy,
  copiedPath,
  filterQuery,
}: {
  node: FileNode
  depth: number
  selectedPath: string | null
  onSelect: (path: string) => void
  onCopy: (path: string) => void
  copiedPath: string | null
  filterQuery: string
}) {
  const [open, setOpen] = useState(depth < 1 || Boolean(filterQuery.trim()))
  const isSelected = selectedPath === node.path

  const isOpen = filterQuery.trim() ? true : open

  if (node.type === 'file') {
    return (
      <div
        onClick={() => onSelect(node.path)}
        onDoubleClick={() => onCopy(node.path)}
        className={[
          'group relative flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-pointer transition-all duration-150',
          isSelected
            ? 'bg-blue-500/15 text-blue-200 border border-blue-500/30 shadow-[0_0_12px_rgba(59,130,246,0.15)] font-medium'
            : 'hover:bg-white/[0.05] text-gray-300 border border-transparent',
        ].join(' ')}
        style={{ paddingLeft: `${depth * 14 + 10}px` }}
        title={`${node.path} (Double-click to copy)`}
      >
        <FileIcon language={node.language} />
        <span className="text-xs font-mono truncate group-hover:text-white transition-colors">{node.name}</span>
        {node.language && (
          <span className="ml-auto text-gray-500 group-hover:text-gray-400 text-[10px] font-mono shrink-0 px-1.5 py-0.5 rounded bg-gray-900/60 border border-white/[0.04]">
            {node.language}
          </span>
        )}
      </div>
    )
  }

  // directory
  const filteredChildren = node.children?.filter((child) => {
    if (!filterQuery.trim()) return true
    const q = filterQuery.toLowerCase()
    const match = (n: FileNode): boolean =>
      n.name.toLowerCase().includes(q) || Boolean(n.children?.some(match))
    return match(child)
  })

  return (
    <div>
      <button
        onClick={() => {
          setOpen((o) => !o)
          onSelect(node.path)
        }}
        className={[
          'w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg transition-all duration-150 text-left group',
          isSelected
            ? 'bg-white/[0.08] text-white font-medium border border-white/[0.06]'
            : 'hover:bg-white/[0.04] text-gray-300',
        ].join(' ')}
        style={{ paddingLeft: `${depth * 14 + 10}px` }}
      >
        <ChevronIcon open={isOpen} />
        <FolderIcon open={isOpen} />
        <span className="text-xs font-mono font-medium truncate group-hover:text-white transition-colors">{node.name}</span>
        {node.children && (
          <span className="ml-auto text-gray-500 text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-900/60 border border-white/[0.04]">{node.children.length}</span>
        )}
      </button>
      {isOpen && filteredChildren && (
        <div className="transition-all duration-150">
          {filteredChildren.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onCopy={onCopy}
              copiedPath={copiedPath}
              filterQuery={filterQuery}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="10" height="10" viewBox="0 0 10 10" fill="currentColor"
      className={`text-gray-500 shrink-0 transition-transform duration-200 ${open ? 'rotate-90 text-blue-400' : ''}`}
    >
      <path d="M3 2l4 3-4 3V2z" />
    </svg>
  )
}

function FolderIcon({ open = false }: { open?: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-amber-400 shrink-0 transition-transform duration-150">
      {open ? (
        <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v2H3V7zm0 4h18l-2 9H5l-2-9z"
          fill="currentColor" opacity="0.9" />
      ) : (
        <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
          fill="currentColor" opacity="0.85" />
      )}
    </svg>
  )
}

function FileIcon({ language }: { language?: string }) {
  const colorMap: Record<string, string> = {
    Python:     'text-blue-400',
    TypeScript: 'text-sky-400',
    JavaScript: 'text-yellow-400',
    Markdown:   'text-gray-400',
    Rust:       'text-orange-400',
    Go:         'text-cyan-400',
    Java:       'text-red-400',
  }
  const color = language ? (colorMap[language] ?? 'text-gray-400') : 'text-gray-500'
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className={`shrink-0 ${color}`}>
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="14,2 14,8 20,8"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

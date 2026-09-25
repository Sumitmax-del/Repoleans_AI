import { useState } from 'react'
import type { FileNode } from '../types'

interface Props {
  root: FileNode
}

export default function FileExplorer({ root }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-gray-800 shrink-0">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">File Explorer</p>
      </div>
      <div className="flex-1 overflow-y-auto p-2 text-sm">
        {root.children?.map((node) => (
          <TreeNode key={node.path} node={node} depth={0} />
        ))}
      </div>
    </div>
  )
}

function TreeNode({ node, depth }: { node: FileNode; depth: number }) {
  const [open, setOpen] = useState(depth < 1)

  if (node.type === 'file') {
    return (
      <div
        className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-800 cursor-default transition-colors"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <FileIcon language={node.language} />
        <span className="text-gray-300 text-xs font-mono truncate">{node.name}</span>
        {node.language && (
          <span className="ml-auto text-gray-600 text-xs shrink-0">{node.language}</span>
        )}
      </div>
    )
  }

  // directory
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-800 transition-colors text-left"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <ChevronIcon open={open} />
        <FolderIcon />
        <span className="text-gray-200 text-xs font-mono font-medium">{node.name}</span>
        {node.children && (
          <span className="ml-auto text-gray-600 text-xs">{node.children.length}</span>
        )}
      </button>
      {open && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.path} node={child} depth={depth + 1} />
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
      className={`text-gray-500 shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
    >
      <path d="M3 2l4 3-4 3V2z" />
    </svg>
  )
}

function FolderIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-yellow-500 shrink-0">
      <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
        fill="currentColor" opacity="0.85" />
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
  const color = language ? (colorMap[language] ?? 'text-gray-500') : 'text-gray-600'
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className={`shrink-0 ${color}`}>
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="14,2 14,8 20,8"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

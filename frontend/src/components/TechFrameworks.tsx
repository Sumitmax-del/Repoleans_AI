import type { RepoSummary } from '../types'

interface Props {
  summary: RepoSummary
}

// Framework badge color palette
const PALETTE = [
  'bg-blue-500/10 text-blue-300 border-blue-500/30 hover:border-blue-400 hover:bg-blue-500/20 hover:shadow-[0_0_12px_rgba(59,130,246,0.2)]',
  'bg-purple-500/10 text-purple-300 border-purple-500/30 hover:border-purple-400 hover:bg-purple-500/20 hover:shadow-[0_0_12px_rgba(168,85,247,0.2)]',
  'bg-sky-500/10 text-sky-300 border-sky-500/30 hover:border-sky-400 hover:bg-sky-500/20 hover:shadow-[0_0_12px_rgba(14,165,233,0.2)]',
  'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 hover:border-emerald-400 hover:bg-emerald-500/20 hover:shadow-[0_0_12px_rgba(16,185,129,0.2)]',
  'bg-orange-500/10 text-orange-300 border-orange-500/30 hover:border-orange-400 hover:bg-orange-500/20 hover:shadow-[0_0_12px_rgba(249,115,22,0.2)]',
  'bg-pink-500/10 text-pink-300 border-pink-500/30 hover:border-pink-400 hover:bg-pink-500/20 hover:shadow-[0_0_12px_rgba(236,72,153,0.2)]',
  'bg-cyan-500/10 text-cyan-300 border-cyan-500/30 hover:border-cyan-400 hover:bg-cyan-500/20 hover:shadow-[0_0_12px_rgba(6,182,212,0.2)]',
  'bg-amber-500/10 text-amber-300 border-amber-500/30 hover:border-amber-400 hover:bg-amber-500/20 hover:shadow-[0_0_12px_rgba(245,158,11,0.2)]',
]

// Known framework → category
const CATEGORY_MAP: Record<string, string> = {
  // Frontend
  React: 'Frontend', Vue: 'Frontend', Angular: 'Frontend',
  Svelte: 'Frontend', 'Next.js': 'Frontend', Remix: 'Frontend',
  Vite: 'Tooling', Webpack: 'Tooling', Rollup: 'Tooling',
  Tailwind: 'Styling', 'CSS Modules': 'Styling',
  // Backend
  FastAPI: 'Backend', Flask: 'Backend', Django: 'Backend',
  Express: 'Backend', Fastify: 'Backend', Starlette: 'Backend',
  Rails: 'Backend', Spring: 'Backend',
  // Data / Infra
  Pydantic: 'Validation', Zod: 'Validation',
  SQLAlchemy: 'ORM', Prisma: 'ORM', Hibernate: 'ORM',
  Celery: 'Queue', Redis: 'Cache',
  // Test
  Pytest: 'Testing', Jest: 'Testing', Vitest: 'Testing', Mocha: 'Testing',
}

function badgeClass(_fw: string, index: number) {
  return PALETTE[index % PALETTE.length]
}

function category(fw: string) {
  return CATEGORY_MAP[fw] ?? 'Library'
}

export default function TechFrameworks({ summary }: Props) {
  if (summary.frameworks.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 shadow-xl shadow-black/30 animate-fade-in">
        <SectionHeader />
        <p className="text-sm text-gray-500 italic">No frameworks detected.</p>
      </div>
    )
  }

  // Group by category
  const grouped = summary.frameworks.reduce<Record<string, string[]>>((acc, fw) => {
    const cat = category(fw)
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(fw)
    return acc
  }, {})

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl shadow-black/30 animate-fade-in relative overflow-hidden">
      {/* Subtle top ambient gradient line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-purple-500/40 to-transparent" />

      <SectionHeader />

      <div className="space-y-4">
        {Object.entries(grouped).map(([cat, fws]) => (
          <div key={cat} className="group">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2.5 font-semibold flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 shadow-[0_0_6px_rgba(168,85,247,0.8)]" />
              {cat}
            </p>
            <div className="flex flex-wrap gap-2">
              {fws.map((fw, i) => (
                <span
                  key={fw}
                  className={`inline-flex items-center gap-1.5 text-sm font-semibold
                               px-3.5 py-1.5 rounded-xl border shadow-sm cursor-default transition-all duration-200 hover:scale-105 hover:-translate-y-0.5 ${badgeClass(fw, i)}`}
                >
                  {fw}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Summary strip */}
      <div className="mt-5 pt-4 border-t border-white/[0.08] flex items-center gap-4 text-xs text-gray-400 flex-wrap">
        <span className="flex items-center gap-1.5 bg-gray-900/60 border border-white/[0.06] px-2.5 py-1 rounded-lg">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          <span className="font-semibold text-gray-200">{summary.frameworks.length}</span> framework
          {summary.frameworks.length !== 1 ? 's' : ''} detected
        </span>
        <span className="text-gray-600">·</span>
        <span>
          Primary language:{' '}
          <span className="font-semibold text-blue-300">{summary.primary_language}</span>
        </span>
        <span className="text-gray-600">·</span>
        <span>
          <span className="font-semibold text-gray-200">{summary.languages.length}</span> language
          {summary.languages.length !== 1 ? 's' : ''} total
        </span>
      </div>
    </div>
  )
}

function SectionHeader() {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-blue-400">
          <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" />
          <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" />
          <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
        Technologies &amp; Frameworks
      </p>
    </div>
  )
}

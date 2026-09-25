import type { RepoSummary } from '../types'

interface Props {
  summary: RepoSummary
}

// Framework badge color palette — cycles through these for unlisted frameworks
const PALETTE = [
  'bg-blue-900/50 text-blue-300 border-blue-700/60',
  'bg-purple-900/50 text-purple-300 border-purple-700/60',
  'bg-sky-900/50 text-sky-300 border-sky-700/60',
  'bg-emerald-900/50 text-emerald-300 border-emerald-700/60',
  'bg-orange-900/50 text-orange-300 border-orange-700/60',
  'bg-pink-900/50 text-pink-300 border-pink-700/60',
  'bg-cyan-900/50 text-cyan-300 border-cyan-700/60',
  'bg-yellow-900/50 text-yellow-300 border-yellow-700/60',
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
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
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
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <SectionHeader />

      <div className="space-y-4">
        {Object.entries(grouped).map(([cat, fws]) => (
          <div key={cat}>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{cat}</p>
            <div className="flex flex-wrap gap-2">
              {fws.map((fw, i) => (
                <span
                  key={fw}
                  className={`inline-flex items-center gap-1.5 text-sm font-semibold
                               px-3 py-1.5 rounded-lg border ${badgeClass(fw, i)}`}
                >
                  {fw}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Summary strip */}
      <div className="mt-4 pt-4 border-t border-gray-800 flex items-center gap-4 text-xs text-gray-500">
        <span>
          <span className="font-semibold text-gray-300">{summary.frameworks.length}</span> framework
          {summary.frameworks.length !== 1 ? 's' : ''} detected
        </span>
        <span>·</span>
        <span>
          Primary language:{' '}
          <span className="font-semibold text-gray-300">{summary.primary_language}</span>
        </span>
        <span>·</span>
        <span>
          <span className="font-semibold text-gray-300">{summary.languages.length}</span> language
          {summary.languages.length !== 1 ? 's' : ''} total
        </span>
      </div>
    </div>
  )
}

function SectionHeader() {
  return (
    <div className="flex items-center gap-2 mb-4">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-gray-400">
        <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" />
        <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
        Technologies &amp; Frameworks
      </p>
    </div>
  )
}

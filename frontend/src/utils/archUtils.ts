import type { RepoSummary, ArchComponent } from '../types'

/**
 * Derives architectural components from a RepoSummary.
 * Maps detected frameworks to their roles and associates notable files.
 */

const FRAMEWORK_ROLES: Record<string, string> = {
  // Python
  FastAPI:    'Web Framework',
  Flask:      'Web Framework',
  Django:     'Web Framework',
  Starlette:  'ASGI Foundation',
  Pydantic:   'Data Validation',
  SQLAlchemy: 'ORM',
  Celery:     'Task Queue',
  Pytest:     'Test Runner',
  // JavaScript / TypeScript
  React:      'UI Library',
  Vue:        'UI Framework',
  Angular:    'UI Framework',
  Next:       'Full-Stack Framework',
  Express:    'Web Framework',
  Fastify:    'Web Framework',
  Prisma:     'ORM',
  Vite:       'Build Tool',
  Tailwind:   'CSS Framework',
  Vitest:     'Test Runner',
  Jest:       'Test Runner',
  // Other
  Spring:     'Web Framework',
  Hibernate:  'ORM',
  Rails:      'Web Framework',
}

export function buildArchComponents(summary: RepoSummary): ArchComponent[] {
  return summary.frameworks.map((fw) => ({
    name: fw,
    role: FRAMEWORK_ROLES[fw] ?? 'Library',
    files: summary.important_files.filter((f) =>
      f.toLowerCase().includes(fw.toLowerCase())
    ),
  }))
}

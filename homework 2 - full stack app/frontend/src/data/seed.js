export const STATUSES = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Done']

export const PRIORITIES = ['Low', 'Medium', 'High']

export const SEED_USERS = [
  { id: 'u-devops', name: 'Mira Shah', role: 'devops' },
  { id: 'u-ana', name: 'Ana Ruiz', role: 'developer' },
  { id: 'u-ben', name: 'Ben Carter', role: 'developer' },
  { id: 'u-cleo', name: 'Cleo Park', role: 'developer' },
  { id: 'u-dev', name: 'Dev Patel', role: 'developer' },
]

const now = Date.now()
const h = 3600_000
const d = 24 * h

function task(o) {
  return {
    description: '',
    priority: 'Medium',
    assigneeId: null,
    comments: [],
    events: [],
    ...o,
  }
}

function ev(id, type, actorId, at, detail = '') {
  return { id, type, actorId, at, detail }
}

function comment(id, authorId, at, body) {
  return { id, authorId, at, body }
}

export const SEED_TASKS = [
  task({
    id: 't-101',
    title: 'Set up CI pipeline for staging',
    description: 'GitHub Actions: lint, test, build on every PR. Cache node_modules.',
    status: 'Backlog',
    priority: 'High',
    assigneeId: null,
    createdBy: 'u-devops',
    createdAt: now - 4 * d,
    updatedAt: now - 4 * d,
    comments: [],
    events: [ev('e-101-1', 'created', 'u-devops', now - 4 * d, 'Created in Backlog')],
  }),
  task({
    id: 't-102',
    title: 'Design empty states for board columns',
    description: 'Figma first, then implement. Keep copy short and friendly.',
    status: 'Backlog',
    priority: 'Low',
    assigneeId: 'u-cleo',
    createdBy: 'u-devops',
    createdAt: now - 3 * d,
    updatedAt: now - 2 * d,
    comments: [comment('c-102-1', 'u-cleo', now - 2 * d, 'Drafted two variants, will attach screenshots.')],
    events: [
      ev('e-102-1', 'created', 'u-devops', now - 3 * d, 'Created in Backlog'),
      ev('e-102-2', 'assigned', 'u-devops', now - 3 * d, 'Assigned to Cleo Park'),
    ],
  }),
  task({
    id: 't-103',
    title: 'API: GET /api/tasks with filters',
    description: 'Support assigneeId, q, priority query params. Paginate later.',
    status: 'To Do',
    priority: 'High',
    assigneeId: 'u-ana',
    createdBy: 'u-devops',
    createdAt: now - 3 * d,
    updatedAt: now - 26 * h,
    comments: [],
    events: [
      ev('e-103-1', 'created', 'u-devops', now - 3 * d, 'Created in Backlog'),
      ev('e-103-2', 'moved', 'u-devops', now - 26 * h, 'Backlog → To Do'),
    ],
  }),
  task({
    id: 't-104',
    title: 'Auth: user switcher + X-User-Id header',
    description: 'Temporary v1 auth. Document swap path to real login.',
    status: 'To Do',
    priority: 'Medium',
    assigneeId: 'u-ben',
    createdBy: 'u-devops',
    createdAt: now - 3 * d,
    updatedAt: now - 30 * h,
    comments: [],
    events: [ev('e-104-1', 'created', 'u-devops', now - 3 * d, 'Created in To Do')],
  }),
  task({
    id: 't-105',
    title: 'Card drag-and-drop between columns',
    description: 'HTML5 DnD with keyboard fallback (Move-to dropdown). Roll back on 403.',
    status: 'In Progress',
    priority: 'High',
    assigneeId: 'u-ana',
    createdBy: 'u-devops',
    createdAt: now - 5 * d,
    updatedAt: now - 5 * h,
    comments: [
      comment('c-105-1', 'u-ana', now - 8 * h, 'DnD working, adding drop highlight + rollback toast.'),
    ],
    events: [
      ev('e-105-1', 'created', 'u-devops', now - 5 * d, 'Created in Backlog'),
      ev('e-105-2', 'moved', 'u-ana', now - 2 * d, 'Backlog → In Progress'),
      ev('e-105-3', 'commented', 'u-ana', now - 8 * h, 'Added a status note'),
    ],
  }),
  task({
    id: 't-106',
    title: 'Task detail drawer with comments',
    description: 'Right slide-over: editable fields, comment thread, activity log.',
    status: 'In Progress',
    priority: 'Medium',
    assigneeId: 'u-dev',
    createdBy: 'u-devops',
    createdAt: now - 4 * d,
    updatedAt: now - 3 * h,
    comments: [
      comment('c-106-1', 'u-dev', now - 6 * h, 'Drawer layout done, wiring permission-gated inputs.'),
    ],
    events: [
      ev('e-106-1', 'created', 'u-devops', now - 4 * d, 'Created in To Do'),
      ev('e-106-2', 'moved', 'u-dev', now - 1 * d, 'To Do → In Progress'),
    ],
  }),
  task({
    id: 't-107',
    title: 'Fix overdue badge timezone bug',
    description: 'Dates render a day off in IST. Normalize to UTC before formatting.',
    status: 'In Progress',
    priority: 'Medium',
    assigneeId: 'u-ben',
    createdBy: 'u-devops',
    createdAt: now - 2 * d,
    updatedAt: now - 10 * h,
    comments: [],
    events: [ev('e-107-1', 'created', 'u-devops', now - 2 * d, 'Created in In Progress')],
  }),
  task({
    id: 't-108',
    title: 'Write permission tests for PATCH /tasks/:id',
    description: 'Dev A cannot edit Dev B tasks (403). DevOps can edit any.',
    status: 'In Review',
    priority: 'High',
    assigneeId: 'u-cleo',
    createdBy: 'u-devops',
    createdAt: now - 6 * d,
    updatedAt: now - 12 * h,
    comments: [
      comment('c-108-1', 'u-cleo', now - 12 * h, 'Ready for review: 6 cases, all passing locally.'),
    ],
    events: [
      ev('e-108-1', 'created', 'u-devops', now - 6 * d, 'Created in To Do'),
      ev('e-108-2', 'moved', 'u-cleo', now - 12 * h, 'In Progress → In Review'),
    ],
  }),
  task({
    id: 't-109',
    title: 'Seed demo users + sample tasks script',
    description: '1 DevOps, 4 developers, 10 tasks across all columns.',
    status: 'Done',
    priority: 'Low',
    assigneeId: 'u-dev',
    createdBy: 'u-devops',
    createdAt: now - 7 * d,
    updatedAt: now - 2 * d,
    comments: [comment('c-109-1', 'u-devops', now - 2 * d, 'Seed looks good.')],
    events: [
      ev('e-109-1', 'created', 'u-devops', now - 7 * d, 'Created in Backlog'),
      ev('e-109-2', 'moved', 'u-devops', now - 2 * d, 'In Review → Done'),
    ],
  }),
  task({
    id: 't-110',
    title: 'Responsive columns for mobile',
    description: 'Horizontal scroll under 1100px. Min usable width 360px.',
    status: 'Done',
    priority: 'Medium',
    assigneeId: 'u-ana',
    createdBy: 'u-devops',
    createdAt: now - 6 * d,
    updatedAt: now - 3 * d,
    comments: [],
    events: [ev('e-110-1', 'created', 'u-devops', now - 6 * d, 'Created in Done')],
  }),
  task({
    id: 't-111',
    title: 'Document backend swap (mock → REST)',
    description: 'One-file swap: replace src/api/mockApi.js with fetch calls. Keep signatures.',
    status: 'To Do',
    priority: 'Low',
    assigneeId: null,
    createdBy: 'u-devops',
    createdAt: now - 1 * d,
    updatedAt: now - 1 * d,
    comments: [],
    events: [ev('e-111-1', 'created', 'u-devops', now - 1 * d, 'Created in To Do')],
  }),
]

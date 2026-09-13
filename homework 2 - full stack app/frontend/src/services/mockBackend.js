// Mock backend — mirrors specifications.md §8.
// Swap this file later with real fetch() calls to /api/*.
// Keep the same function names + signatures so App.jsx does not change.

import { SEED_TASKS, SEED_USERS, STATUSES, PRIORITIES } from '../data/seed.js'

const STORE_KEY = 'kanban-white-v1'
const LATENCY_MS = 120

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

const delay = (ms = LATENCY_MS) => new Promise((r) => setTimeout(r, ms))
const clone = (o) => JSON.parse(JSON.stringify(o))
const uid = (p) => `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`

function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (raw) {
      const s = JSON.parse(raw)
      if (Array.isArray(s.users) && Array.isArray(s.tasks)) return s
    }
  } catch { /* reseed below */ }
  const fresh = { users: clone(SEED_USERS), tasks: clone(SEED_TASKS) }
  try { localStorage.setItem(STORE_KEY, JSON.stringify(fresh)) } catch { /* private mode */ }
  return fresh
}

function saveState(s) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(s)) } catch { /* ignore */ }
}

function getUserOrThrow(state, actorId) {
  const u = state.users.find((x) => x.id === actorId)
  if (!u) throw new ApiError(401, 'Unknown user. Please pick a user.')
  return u
}

function getTaskOrThrow(state, id) {
  const t = state.tasks.find((x) => x.id === id)
  if (!t) throw new ApiError(404, 'Task not found. It may have been deleted.')
  return t
}

export function isDevOps(user) {
  return user?.role === 'devops'
}

// DevOps: anything. Developer: only tasks assigned to them. Unassigned: read-only for devs.
export function canMove(task, user) {
  if (!user || !task) return false
  if (isDevOps(user)) return true
  return task.assigneeId !== null && task.assigneeId === user.id
}

export function canEdit(task, user) {
  return canMove(task, user)
}

export function canComment(task, user) {
  return canMove(task, user)
}

function assertCanMutate(task, user) {
  if (!canMove(task, user)) {
    if (isDevOps(user)) throw new ApiError(403, 'Not allowed.')
    if (!task.assigneeId) throw new ApiError(403, 'Only DevOps can modify unassigned tasks.')
    throw new ApiError(403, 'Only the assignee can modify this task.')
  }
}

function logEvent(task, type, actorId, detail) {
  task.events.push({ id: uid('e'), type, actorId, at: Date.now(), detail })
}

export async function getUsers() {
  await delay()
  return clone(loadState().users)
}

export async function listTasks() {
  await delay()
  return clone(loadState().tasks)
}

export async function getTask(id) {
  await delay()
  return clone(getTaskOrThrow(loadState(), id))
}

export async function createTask(input, actorId) {
  await delay()
  const state = loadState()
  const actor = getUserOrThrow(state, actorId)
  if (!isDevOps(actor)) throw new ApiError(403, 'Only DevOps can create tasks.')

  const title = (input.title ?? '').trim()
  if (!title) throw new ApiError(422, 'Title is required.')
  if (title.length > 120) throw new ApiError(422, 'Title must be 120 characters or fewer.')
  if (input.status && !STATUSES.includes(input.status)) throw new ApiError(422, 'Invalid status.')
  if (input.priority && !PRIORITIES.includes(input.priority)) throw new ApiError(422, 'Invalid priority.')
  if (input.assigneeId != null && input.assigneeId !== '') {
    const a = state.users.find((u) => u.id === input.assigneeId)
    if (!a || a.role !== 'developer') throw new ApiError(422, 'Assignee must be a developer.')
  }
  if ((input.description ?? '').length > 5000) throw new ApiError(422, 'Description is too long.')

  const now = Date.now()
  const t = {
    id: uid('t'),
    title,
    description: input.description ?? '',
    status: input.status ?? 'Backlog',
    assigneeId: input.assigneeId || null,
    priority: input.priority ?? 'Medium',
    createdBy: actor.id,
    createdAt: now,
    updatedAt: now,
    comments: [],
    events: [{ id: uid('e'), type: 'created', actorId: actor.id, at: now, detail: `Created in ${input.status ?? 'Backlog'}` }],
  }
  state.tasks.push(t)
  saveState(state)
  return clone(t)
}

export async function updateTask(id, patch, actorId) {
  await delay()
  const state = loadState()
  const actor = getUserOrThrow(state, actorId)
  const t = getTaskOrThrow(state, id)

  if (patch.assigneeId !== undefined && patch.assigneeId !== t.assigneeId) {
    if (!isDevOps(actor)) throw new ApiError(403, 'Only DevOps can assign tasks.')
    if (patch.assigneeId !== null) {
      const a = state.users.find((u) => u.id === patch.assigneeId)
      if (!a || a.role !== 'developer') throw new ApiError(422, 'Assignee must be a developer.')
    }
    t.assigneeId = patch.assigneeId
    t.updatedAt = Date.now()
    const name = patch.assigneeId ? state.users.find((u) => u.id === patch.assigneeId)?.name : 'Unassigned'
    logEvent(t, 'assigned', actor.id, `Assigned to ${name}`)
  }

  const scalarFields = ['title', 'description', 'priority', 'status']
  const wantsScalar = scalarFields.some((f) => patch[f] !== undefined)
  if (wantsScalar) assertCanMutate(t, actor)

  if (patch.title !== undefined) {
    const title = patch.title.trim()
    if (!title) throw new ApiError(422, 'Title is required.')
    if (title.length > 120) throw new ApiError(422, 'Title must be 120 characters or fewer.')
    if (title !== t.title) {
      t.title = title
      t.updatedAt = Date.now()
      logEvent(t, 'edited', actor.id, 'Edited title')
    }
  }
  if (patch.description !== undefined && patch.description !== t.description) {
    if (patch.description.length > 5000) throw new ApiError(422, 'Description is too long.')
    t.description = patch.description
    t.updatedAt = Date.now()
    logEvent(t, 'edited', actor.id, 'Edited description')
  }
  if (patch.priority !== undefined && patch.priority !== t.priority) {
    if (!PRIORITIES.includes(patch.priority)) throw new ApiError(422, 'Invalid priority.')
    t.priority = patch.priority
    t.updatedAt = Date.now()
    logEvent(t, 'edited', actor.id, `Priority → ${patch.priority}`)
  }
  if (patch.status !== undefined && patch.status !== t.status) {
    if (!STATUSES.includes(patch.status)) throw new ApiError(422, 'Invalid status.')
    const from = t.status
    t.status = patch.status
    t.updatedAt = Date.now()
    logEvent(t, 'moved', actor.id, `${from} → ${patch.status}`)
  }

  saveState(state)
  return clone(t)
}

export async function addComment(taskId, body, actorId) {
  await delay()
  const state = loadState()
  const actor = getUserOrThrow(state, actorId)
  const t = getTaskOrThrow(state, taskId)
  assertCanMutate(t, actor)
  const text = (body ?? '').trim()
  if (!text) throw new ApiError(422, 'Comment cannot be empty.')
  if (text.length > 2000) throw new ApiError(422, 'Comment must be 2000 characters or fewer.')
  const c = { id: uid('c'), authorId: actor.id, at: Date.now(), body: text }
  t.comments.push(c)
  t.updatedAt = Date.now()
  logEvent(t, 'commented', actor.id, 'Added a status note')
  saveState(state)
  return clone(c)
}

export async function deleteTask(id, actorId) {
  await delay()
  const state = loadState()
  const actor = getUserOrThrow(state, actorId)
  if (!isDevOps(actor)) throw new ApiError(403, 'Only DevOps can delete tasks.')
  const i = state.tasks.findIndex((x) => x.id === id)
  if (i === -1) throw new ApiError(404, 'Task not found. It may have been deleted.')
  state.tasks.splice(i, 1)
  saveState(state)
}

export async function resetDemo() {
  await delay(50)
  const fresh = { users: clone(SEED_USERS), tasks: clone(SEED_TASKS) }
  saveState(fresh)
  return clone(fresh.tasks)
}

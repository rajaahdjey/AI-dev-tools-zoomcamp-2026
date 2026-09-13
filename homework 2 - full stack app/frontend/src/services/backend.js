// Real backend client — fetch() calls to /api/* (same-origin; vite proxies
// /api to the FastAPI server in dev). UI code imports ONLY from this file.
//
// Session: login(userId, password) stores the bearer token in memory +
// localStorage; every request below sends it. The server derives the actor
// from the token, so callers never pass user ids. 401s mean the token is
// missing/invalid — the app should return to the login screen.

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

const TOKEN_KEY = 'kanban-token-v1'

let _token = null
try {
  _token = localStorage.getItem(TOKEN_KEY)
} catch {
  _token = null
}

function setToken(token) {
  _token = token || null
  try {
    if (_token) localStorage.setItem(TOKEN_KEY, _token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* private mode */
  }
}

export function hasSession() {
  return _token !== null
}

async function req(path, { method = 'GET', body } = {}) {
  let res
  try {
    res = await fetch(path, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : null),
        ...(_token ? { Authorization: `Bearer ${_token}` } : null),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : null),
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?')
  }
  if (res.status === 204) return null
  let data = null
  try {
    data = await res.json()
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) throw new ApiError(res.status, data?.error || `Request failed (${res.status}).`)
  return data
}

export async function login(userId, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId, password }),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data?.error || 'Login failed.')
  setToken(data.access_token)
  return data.user
}

export async function me() {
  return req('/api/auth/me')
}

export async function logout() {
  if (_token) {
    try {
      await req('/api/auth/logout', { method: 'POST' })
    } catch {
      /* token already dead — still clear it locally */
    }
  }
  setToken(null)
}

// Seed roster, mirrored from the backend seed: only used to populate the
// login dropdown (the directory endpoint itself needs a token).
export const DEMO_USERS = [
  { id: 'u-devops', name: 'Mira Shah', role: 'devops' },
  { id: 'u-ana', name: 'Ana Ruiz', role: 'developer' },
  { id: 'u-ben', name: 'Ben Carter', role: 'developer' },
  { id: 'u-cleo', name: 'Cleo Park', role: 'developer' },
  { id: 'u-dev', name: 'Dev Patel', role: 'developer' },
]

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

export async function getUsers() {
  return req('/api/users')
}

export async function listTasks() {
  return req('/api/tasks')
}

export async function getTask(id) {
  return req(`/api/tasks/${id}`)
}

export async function createTask(input) {
  return req('/api/tasks', { method: 'POST', body: input })
}

export async function updateTask(id, patch) {
  return req(`/api/tasks/${id}`, { method: 'PATCH', body: patch })
}

export async function addComment(taskId, body) {
  return req(`/api/tasks/${taskId}/comments`, { method: 'POST', body: { body } })
}

export async function deleteTask(id) {
  await req(`/api/tasks/${id}`, { method: 'DELETE' })
}

export async function resetDemo() {
  await req('/api/admin/reset', { method: 'POST' })
  setToken(null) // reseed revokes all sessions
}

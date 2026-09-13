import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  addComment,
  canComment,
  canEdit,
  canMove,
  createTask,
  deleteTask,
  getUsers,
  isDevOps,
  listTasks,
  resetDemo,
  updateTask,
} from './services/backend.js'
import { PRIORITIES, STATUSES } from './data/seed.js'

/* ---------- helpers ---------- */

function initials(name) {
  return name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()
}

function avatarColor(name) {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return `hsl(${h} 45% 42%)`
}

function timeAgo(ts) {
  const s = Math.max(1, Math.floor((Date.now() - ts) / 1000))
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const PRI_RANK = { High: 0, Medium: 1, Low: 2 }

function errMsg(e) {
  if (e instanceof ApiError) return e.message
  return 'Something went wrong.'
}

let toastSeq = 0

/* ---------- small components ---------- */

function Avatar({ name, size = '' }) {
  return (
    <span className={`avatar ${size}`} style={{ background: avatarColor(name) }} title={name}>
      {initials(name)}
    </span>
  )
}

function Card({ task, userName, movable, commentCount, onOpen, onDragStart, onDragEnd, dragging }) {
  return (
    <article
      className={`card ${movable ? '' : 'locked'} ${dragging ? 'dragging' : ''} pri-${task.priority}`}
      draggable={movable}
      onDragStart={(e) => onDragStart(e, task.id)}
      onDragEnd={onDragEnd}
      onClick={onOpen}
      title={movable ? 'Open details' : `Assigned to ${userName} — read-only`}
    >
      <div className="card-top">
        <span className="pri"><span className="pri-dot" />{task.priority}</span>
        <span className="meta-right">💬 {commentCount}</span>
      </div>
      <h3 className="card-title">{task.title}</h3>
      {task.description ? <p className="card-snippet">{task.description}</p> : null}
      <div className="card-foot">
        {userName ? (
          <span className="assignee"><Avatar name={userName} /><span className="name">{userName}</span></span>
        ) : (
          <span className="unassigned">Unassigned</span>
        )}
        {!movable ? <span className="lock-hint">🔒 {userName || 'DevOps only'}</span> : null}
      </div>
    </article>
  )
}

function Drawer({ task, users, currentUser, onClose, onChanged, notify }) {
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [priority, setPriority] = useState(task?.priority ?? 'Medium')
  const [status, setStatus] = useState(task?.status ?? 'Backlog')
  const [assigneeId, setAssigneeId] = useState(task?.assigneeId ?? '')
  const [draftComment, setDraftComment] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setTitle(task?.title ?? '')
    setDescription(task?.description ?? '')
    setPriority(task?.priority ?? 'Medium')
    setStatus(task?.status ?? 'Backlog')
    setAssigneeId(task?.assigneeId ?? '')
    setDraftComment('')
    setError('')
  }, [task?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!task) {
    return (
      <>
        <div className="overlay" onClick={onClose} />
        <aside className="drawer">
          <div className="drawer-head"><h2>Task deleted</h2><button className="icon-btn" onClick={onClose}>✕</button></div>
          <div className="drawer-body"><p className="hint">This task no longer exists.</p></div>
        </aside>
      </>
    )
  }

  const editable = canEdit(task, currentUser)
  const commentable = canComment(task, currentUser)
  const devops = isDevOps(currentUser)
  const userById = Object.fromEntries(users.map((u) => [u.id, u]))
  const dirty =
    title !== task.title || description !== task.description ||
    priority !== task.priority || status !== task.status ||
    (assigneeId || null) !== (task.assigneeId ?? null)

  async function handleSave() {
    setSaving(true)
    setError('')
    try {
      // Reassign first (DevOps-only on the backend), then scalar fields.
      if ((assigneeId || null) !== (task.assigneeId ?? null)) {
        await updateTask(task.id, { assigneeId: assigneeId || null }, currentUser.id)
      }
      await updateTask(task.id, { title, description, priority, status }, currentUser.id)
      notify('success', 'Task updated.')
      await onChanged()
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  async function handleCommentSubmit(e) {
    e.preventDefault()
    if (!draftComment.trim()) return
    setSaving(true)
    setError('')
    try {
      await addComment(task.id, draftComment, currentUser.id)
      setDraftComment('')
      await onChanged()
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${task.title}"?`)) return
    try {
      await deleteTask(task.id, currentUser.id)
      notify('success', 'Task deleted.')
      await onChanged()
      onClose()
    } catch (e) {
      setError(errMsg(e))
    }
  }

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Task details">
        <div className="drawer-head">
          <h2>Task details</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="drawer-body">
          {error ? <div className="error">{error}</div> : null}
          {!editable ? (
            <div className="hint">🔒 Read-only — {task.assigneeId ? `assigned to ${userById[task.assigneeId]?.name ?? 'someone else'}` : 'unassigned'}. Only the assignee or DevOps can edit.</div>
          ) : null}

          <div className="field">
            <label>Title</label>
            <input type="text" value={title} maxLength={120} disabled={!editable} onChange={(e) => setTitle(e.target.value)} />
          </div>

          <div className="field-row">
            <div className="field">
              <label>Move to (status)</label>
              <select value={status} disabled={!canMove(task, currentUser)} onChange={(e) => setStatus(e.target.value)}>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Priority</label>
              <select value={priority} disabled={!editable} onChange={(e) => setPriority(e.target.value)}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div className="field">
            <label>Assignee</label>
            <select value={assigneeId} disabled={!devops} onChange={(e) => setAssigneeId(e.target.value)}>
              <option value="">Unassigned</option>
              {users.filter((u) => u.role === 'developer').map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
            {!devops ? <div className="hint">Only DevOps can reassign.</div> : null}
          </div>

          <div className="field">
            <label>Description</label>
            <textarea value={description} disabled={!editable} onChange={(e) => setDescription(e.target.value)} placeholder="Add details, acceptance criteria, links…" />
          </div>

          {editable && dirty ? <button className="btn btn-dark" disabled={saving} onClick={handleSave}>Save changes</button> : null}

          <div className="meta-line">Created {timeAgo(task.createdAt)} · Updated {timeAgo(task.updatedAt)} · {task.id}</div>

          <div className="field">
            <label>Comments ({task.comments.length})</label>
            <div className="comments">
              {task.comments.length === 0 ? <div className="hint">No notes yet. Add the first status update below.</div> : null}
              {task.comments.map((c) => (
                <div className="comment" key={c.id}>
                  <div className="comment-head">
                    <Avatar name={userById[c.authorId]?.name ?? '?'} />
                    <strong>{userById[c.authorId]?.name ?? 'Unknown'}</strong>
                    <time>{timeAgo(c.at)}</time>
                  </div>
                  <p>{c.body}</p>
                </div>
              ))}
            </div>
          </div>

          {commentable ? (
            <form className="comment-form" onSubmit={handleCommentSubmit}>
              <input
                type="text"
                value={draftComment}
                maxLength={2000}
                onChange={(e) => setDraftComment(e.target.value)}
                placeholder="Add a status note…"
              />
              <button className="btn btn-primary" disabled={saving || !draftComment.trim()}>Post</button>
            </form>
          ) : (
            <div className="hint">Only the assignee or DevOps can comment.</div>
          )}

          <div className="field">
            <label>Activity</label>
            <div className="activity">
              <ul>
                {[...task.events].reverse().map((ev) => (
                  <li key={ev.id}>• {ev.detail} — {userById[ev.actorId]?.name ?? '?'} · {timeAgo(ev.at)}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
        <div className="drawer-foot">
          {devops ? <button className="btn btn-danger" onClick={handleDelete}>Delete task</button> : null}
          <span style={{ flex: 1 }} />
          <button className="btn" onClick={onClose}>Close</button>
        </div>
      </aside>
    </>
  )
}

function CreateModal({ users, onClose, onCreated, notify, actor }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assigneeId, setAssigneeId] = useState('')
  const [priority, setPriority] = useState('Medium')
  const [status, setStatus] = useState('Backlog')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await createTask({ title, description, assigneeId: assigneeId || null, priority, status }, actor.id)
      notify('success', 'Task created.')
      await onCreated()
      onClose()
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-label="New task">
        <h2>New task</h2>
        <p className="sub">DevOps only — mirrors POST /api/tasks (403 for developers).</p>
        {error ? <div className="error">{error}</div> : null}
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="field">
            <label>Title *</label>
            <input type="text" autoFocus value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Add retry logic to deploy step" />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Context, acceptance criteria…" />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Assignee</label>
              <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
                <option value="">Unassigned</option>
                {users.filter((u) => u.role === 'developer').map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Priority</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label>Initial status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>Create task</button>
          </div>
        </form>
      </div>
    </>
  )
}

/* ---------- main app ---------- */

export default function App() {
  const [users, setUsers] = useState([])
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [currentUserId, setCurrentUserId] = useState('')
  const [q, setQ] = useState('')
  const [assigneeFilter, setAssigneeFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [mineOnly, setMineOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [toasts, setToasts] = useState([])
  const [draggingId, setDraggingId] = useState(null)
  const [dropStatus, setDropStatus] = useState(null)

  const notify = useCallback((kind, msg) => {
    const id = ++toastSeq
    setToasts((t) => [...t, { id, kind, msg }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200)
  }, [])

  const refresh = useCallback(async () => {
    setTasks(await listTasks())
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const [u, t] = await Promise.all([getUsers(), listTasks()])
        setUsers(u)
        setTasks(t)
        setCurrentUserId(u[0]?.id ?? '')
      } catch (e) {
        notify('error', errMsg(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [notify])

  // Esc closes drawer / modal.
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') {
        setSelectedId(null)
        setShowCreate(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const currentUser = users.find((u) => u.id === currentUserId) ?? null
  const userById = useMemo(() => Object.fromEntries(users.map((u) => [u.id, u])), [users])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return tasks.filter((t) => {
      if (mineOnly && currentUser && t.assigneeId !== currentUser.id) return false
      if (assigneeFilter === 'unassigned' && t.assigneeId !== null) return false
      if (assigneeFilter !== 'all' && assigneeFilter !== 'unassigned' && t.assigneeId !== assigneeFilter) return false
      if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false
      if (needle && !`${t.title}\n${t.description}`.toLowerCase().includes(needle)) return false
      return true
    })
  }, [tasks, q, assigneeFilter, priorityFilter, mineOnly, currentUser])

  const grouped = useMemo(() => {
    const g = Object.fromEntries(STATUSES.map((s) => [s, []]))
    for (const t of filtered) g[t.status]?.push(t)
    for (const s of STATUSES) {
      g[s].sort((a, b) => PRI_RANK[a.priority] - PRI_RANK[b.priority] || b.updatedAt - a.updatedAt)
    }
    return g
  }, [filtered])

  const totalByStatus = useMemo(() => {
    const g = Object.fromEntries(STATUSES.map((s) => [s, 0]))
    for (const t of tasks) if (g[t.status] !== undefined) g[t.status] += 1
    return g
  }, [tasks])

  const selectedTask = selectedId ? tasks.find((t) => t.id === selectedId) ?? null : null
  const filtersActive = q.trim() !== '' || assigneeFilter !== 'all' || priorityFilter !== 'all' || mineOnly

  function clearFilters() {
    setQ('')
    setAssigneeFilter('all')
    setPriorityFilter('all')
    setMineOnly(false)
  }

  function handleDragStart(e, id) {
    setDraggingId(id)
    e.dataTransfer.effectAllowed = 'move'
    try { e.dataTransfer.setData('text/plain', id) } catch { /* safari */ }
  }

  async function handleDrop(toStatus) {
    const id = draggingId
    setDropStatus(null)
    if (!id || !currentUser) return
    const task = tasks.find((t) => t.id === id)
    setDraggingId(null)
    if (!task || task.status === toStatus) return // no-op on same column
    try {
      await updateTask(id, { status: toStatus }, currentUser.id)
      notify('success', `Moved to ${toStatus}.`)
      await refresh()
    } catch (e) {
      notify('error', errMsg(e))
    }
  }

  async function handleReset() {
    if (!window.confirm('Reset demo data? Local changes will be lost.')) return
    await resetDemo()
    await refresh()
    notify('success', 'Demo data reset.')
  }

  if (loading) return <div className="loading">Loading board…</div>

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-mark">K</span>
            <div>
              <h1>Mini Kanban</h1>
              <p>{tasks.length} tasks · {users.filter((u) => u.role === 'developer').length} developers</p>
            </div>
          </div>
          <div className="userbox">
            <label htmlFor="user">Acting as</label>
            <select id="user" value={currentUserId} onChange={(e) => setCurrentUserId(e.target.value)}>
              {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
            {currentUser ? (
              <span className={`role-badge ${currentUser.role}`}>{currentUser.role}</span>
            ) : null}
          </div>
        </div>
      </header>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search title or description…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search tasks"
        />
        <select value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} aria-label="Filter by assignee">
          <option value="all">All assignees</option>
          <option value="unassigned">Unassigned</option>
          {users.filter((u) => u.role === 'developer').map((u) => (
            <option key={u.id} value={u.id}>{u.name}</option>
          ))}
        </select>
        <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} aria-label="Filter by priority">
          <option value="all">All priorities</option>
          {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <label className="toggle" title="Hide tasks not assigned to you">
          <input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} />
          My tasks only
        </label>
        {filtersActive ? <button className="link-btn" onClick={clearFilters}>Clear filters</button> : null}
        <span className="spacer" />
        <button className="btn btn-ghost" onClick={handleReset} title="Restore seeded demo data">Reset demo</button>
        {currentUser && isDevOps(currentUser) ? (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New task</button>
        ) : (
          <button className="btn" disabled title="Only DevOps can create tasks">+ New task</button>
        )}
      </div>

      <main className="board">
        {STATUSES.map((status) => {
          const list = grouped[status]
          const total = totalByStatus[status]
          return (
            <section className="column" key={status} aria-label={status}>
              <div className="column-head">
                <h2>{status}</h2>
                <span className="count">{list.length !== total ? `${list.length} of ${total}` : total}</span>
              </div>
              <div
                className={`column-list ${dropStatus === status ? 'drag-over' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDropStatus(status) }}
                onDragLeave={() => setDropStatus((s) => (s === status ? null : s))}
                onDrop={(e) => { e.preventDefault(); handleDrop(status) }}
              >
                {list.length === 0 ? <div className="empty">No tasks{filtersActive ? ' match filters' : ''}</div> : null}
                {list.map((t) => (
                  <Card
                    key={t.id}
                    task={t}
                    userName={t.assigneeId ? userById[t.assigneeId]?.name : null}
                    movable={currentUser ? canMove(t, currentUser) : false}
                    commentCount={t.comments.length}
                    dragging={draggingId === t.id}
                    onOpen={() => setSelectedId(t.id)}
                    onDragStart={handleDragStart}
                    onDragEnd={() => { setDraggingId(null); setDropStatus(null) }}
                  />
                ))}
              </div>
            </section>
          )
        })}
      </main>

      {selectedId ? (
        <Drawer
          task={selectedTask}
          users={users}
          currentUser={currentUser}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
          notify={notify}
        />
      ) : null}

      {showCreate && currentUser ? (
        <CreateModal
          users={users}
          actor={currentUser}
          onClose={() => setShowCreate(false)}
          onCreated={refresh}
          notify={notify}
        />
      ) : null}

      <div className="toasts">
        {toasts.map((t) => (
          <div className={`toast ${t.kind}`} key={t.id}>
            <span style={{ flex: 1 }}>{t.msg}</span>
            <button onClick={() => setToasts((xs) => xs.filter((x) => x.id !== t.id))} aria-label="Dismiss">✕</button>
          </div>
        ))}
      </div>
    </>
  )
}

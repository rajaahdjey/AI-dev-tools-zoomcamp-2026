// Single entry point for ALL backend calls in the app.
//
// UI code imports ONLY from this file — never from mockBackend.js directly.
// Today this re-exports the mock implementation, so the whole app runs
// with zero backend (localStorage + seed data + simulated latency).
//
// To wire up the real backend later, replace the body of this file with
// fetch() calls to /api/* keeping the SAME exported names + signatures:
//   getUsers, listTasks, getTask, createTask, updateTask,
//   addComment, deleteTask, resetDemo,
//   canMove, canEdit, canComment, isDevOps, ApiError
// No UI changes needed.

export {
  ApiError,
  addComment,
  canComment,
  canEdit,
  canMove,
  createTask,
  deleteTask,
  getTask,
  getUsers,
  isDevOps,
  listTasks,
  resetDemo,
  updateTask,
} from './mockBackend.js'

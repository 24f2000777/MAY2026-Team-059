// Real backend calls for everything under /complaints, /attachments,
// and /feedback that concerns a single complaint. Same pattern as
// authApi.js/chatApi.js: thin wrappers around request() from
// httpClient.js, no logic of its own.
import { API_BASE_URL, request } from './httpClient'

export function getWards({ accessToken }) {
  return request('/complaints/wards', {
    token: accessToken
  })
}

export function getMyComplaints({ accessToken }) {
  return request('/complaints/mine', {
    token: accessToken
  })
}

export function createComplaint({ title, description, category, location, wardCode, accessToken }) {
  return request('/complaints', {
    method: 'POST',
    token: accessToken,
    body: {
      title,
      description,
      category,
      location,
      ward_code: wardCode ?? null
    }
  })
}

// Lists complaints visible to the caller. Citizens only ever see
// their own regardless of filters, staff and admin see everything,
// narrowed by whatever filters are passed. perPage caps at 100 on
// the backend.
export function listComplaints({ accessToken, status, category, wardCode, assignedTo, page = 1, perPage = 100 } = {}) {
  const params = new URLSearchParams({ page, per_page: perPage })
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (wardCode) params.set('ward_code', wardCode)
  if (assignedTo) params.set('assigned_to', assignedTo)
  return request(`/complaints?${params.toString()}`, { token: accessToken })
}

// Same endpoint, but also returns the response's meta (total, total_pages),
// for callers that need to know whether there's more than one page to
// fetch, e.g. AdminDashboard.vue loading every complaint across pages
// rather than silently stopping at the first 100.
export function listComplaintsPage({ accessToken, status, category, wardCode, assignedTo, page = 1, perPage = 100 } = {}) {
  const params = new URLSearchParams({ page, per_page: perPage })
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (wardCode) params.set('ward_code', wardCode)
  if (assignedTo) params.set('assigned_to', assignedTo)
  return request(`/complaints?${params.toString()}`, { token: accessToken, includeMeta: true })
}

// GET /admin/export returns a real CSV file, not the usual JSON
// envelope, so this bypasses request() (which always calls
// response.json()) and triggers a browser download directly instead
// of returning parsed data to the caller.
export async function exportComplaintsCsv({ accessToken, status, category, wardCode, assignedTo }) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (wardCode) params.set('ward_code', wardCode)
  if (assignedTo) params.set('assigned_to', assignedTo)

  const response = await fetch(`${API_BASE_URL}/admin/export?${params.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.message || 'Could not export complaints.')
  }

  const blob = await response.blob()
  const filenameMatch = response.headers.get('content-disposition')?.match(/filename="(.+)"/)
  const filename = filenameMatch?.[1] || 'complaints_export.csv'

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function getComplaint({ id, accessToken }) {
  return request(`/complaints/${id}`, { token: accessToken })
}

export function editComplaint({ id, title, description, accessToken }) {
  const body = {}
  if (title !== undefined) body.title = title
  if (description !== undefined) body.description = description
  return request(`/complaints/${id}`, { method: 'PATCH', token: accessToken, body })
}

export function deleteComplaint({ id, accessToken }) {
  return request(`/complaints/${id}`, { method: 'DELETE', token: accessToken })
}

export function getComplaintHistory({ id, accessToken }) {
  return request(`/complaints/${id}/history`, { token: accessToken })
}

// --- Status transitions. Each one only works from a specific
// starting status, the backend is the source of truth on that, these
// just call the right endpoint, they don't re-validate the state
// machine client side. ---

export function approveComplaint({ id, notes, accessToken }) {
  return request(`/complaints/${id}/approve`, { method: 'PATCH', token: accessToken, body: { notes: notes ?? null } })
}

export function rejectComplaint({ id, reason, accessToken }) {
  return request(`/complaints/${id}/reject`, { method: 'PATCH', token: accessToken, body: { reason } })
}

export function assignComplaint({ id, assignedTo, notes, accessToken }) {
  return request(`/complaints/${id}/assign`, {
    method: 'PATCH',
    token: accessToken,
    body: { assigned_to: assignedTo, notes: notes ?? null }
  })
}

export function startComplaint({ id, notes, accessToken }) {
  return request(`/complaints/${id}/start`, { method: 'PATCH', token: accessToken, body: { notes: notes ?? null } })
}

export function resolveComplaint({ id, notes, accessToken }) {
  return request(`/complaints/${id}/resolve`, { method: 'PATCH', token: accessToken, body: { notes: notes ?? null } })
}

export function withdrawComplaint({ id, accessToken }) {
  return request(`/complaints/${id}/withdraw`, { method: 'PATCH', token: accessToken })
}

export function closeComplaint({ id, accessToken }) {
  return request(`/complaints/${id}/close`, { method: 'PATCH', token: accessToken })
}

// --- Attachments ---

export function listAttachments({ id, accessToken }) {
  return request(`/complaints/${id}/attachments`, { token: accessToken })
}

export function uploadAttachment({ id, file, accessToken }) {
  const formData = new FormData()
  formData.append('file', file)
  return request(`/complaints/${id}/attachments`, { method: 'POST', token: accessToken, formData })
}

export function deleteAttachment({ attachmentId, accessToken }) {
  return request(`/attachments/${attachmentId}`, { method: 'DELETE', token: accessToken })
}

// --- Feedback, always scoped to one complaint ---

export function getFeedback({ id, accessToken }) {
  return request(`/complaints/${id}/feedback`, { token: accessToken })
}

export function submitFeedback({ id, score, feedback, accessToken }) {
  return request(`/complaints/${id}/feedback`, {
    method: 'POST',
    token: accessToken,
    body: { score, feedback: feedback ?? null }
  })
}

// --- Officers, for an assignment dropdown ---

export function listOfficers({ accessToken }) {
  return request('/admin/officers', { token: accessToken })
}

export function createStaffAccount({ name, phone, email, password, accessToken }) {
  return request('/admin/users', {
    method: 'POST',
    token: accessToken,
    body: { name, phone, email, password }
  })
}

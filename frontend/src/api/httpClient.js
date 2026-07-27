// Real HTTP client for the FastAPI backend, used by authApi.js (and
// later by other *Api.js files as more endpoints get wired up). Every
// endpoint returns the same envelope:
//   success: { success: true, message, data, meta }
//   error:   { success: false, message, error_code, details }
// request() unwraps that and throws a real Error (with .code/.details
// attached) on failure, so callers can just try/catch like they did
// against the old mock client.

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined
    })
  } catch {
    throw new Error('Could not reach the server. Is the backend running?')
  }

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    const error = new Error(payload?.message || 'Something went wrong. Please try again.')
    error.code = payload?.error_code
    error.details = payload?.details
    error.status = response.status
    throw error
  }

  return payload?.data
}

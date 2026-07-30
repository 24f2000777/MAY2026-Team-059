// Real backend calls for complaint submission. Same pattern as
// authApi.js/chatApi.js: thin wrappers around request() from httpClient.js.
import { request } from './httpClient'

export function getWards({ accessToken }) {
  return request('/complaints/wards', {
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

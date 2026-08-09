// Real backend call for GET /analytics/summary. Same pattern as
// authApi.js/complaintApi.js: thin wrapper around request() from
// httpClient.js.
import { request } from './httpClient'

export function getAnalyticsSummary({ accessToken }) {
  return request('/analytics/summary', { token: accessToken })
}

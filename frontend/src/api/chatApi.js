// Real backend calls for the Nagrik Saathi chatbot. Same pattern as
// authApi.js: thin wrappers around request() from httpClient.js.
import { request } from './httpClient'

export function sendChatMessage({ sessionId, message, accessToken }) {
  return request('/chat/message', {
    method: 'POST',
    token: accessToken,
    body: { session_id: sessionId, message }
  })
}

export function getChatHistory({ sessionId, accessToken }) {
  return request(`/chat/history/${sessionId}`, {
    token: accessToken
  })
}

// Real backend calls for the Nagrik Saathi chatbot. Same pattern as
// authApi.js: thin wrappers around request() from httpClient.js.
import { request } from './httpClient'

export function sendChatMessage({ sessionId, message, latitude, longitude, address, accessToken }) {
  return request('/chat/message', {
    method: 'POST',
    token: accessToken,
    body: {
      session_id: sessionId,
      message,
      latitude: latitude ?? null,
      longitude: longitude ?? null,
      address: address ?? null
    }
  })
}

export function getChatHistory({ sessionId, accessToken }) {
  return request(`/chat/history/${sessionId}`, {
    token: accessToken
  })
}

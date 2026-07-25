// Real backend calls for auth, replacing the localStorage mock for the
// login/signup flow specifically. See src/api/client.js for what's
// still mocked (complaints, profile, password reset, etc.).
import { request } from './httpClient'

export function registerUser({ name, phone, email, password }) {
  return request('/auth/register', {
    method: 'POST',
    body: { name, phone, email, password }
  })
}

export function verifyOtp({ email, otp }) {
  return request('/auth/verify-otp', {
    method: 'POST',
    body: { email, otp }
  })
}

export function loginUser({ email, password }) {
  return request('/auth/login', {
    method: 'POST',
    body: { email, password }
  })
}

export function logoutUser({ accessToken, refreshToken }) {
  return request('/auth/logout', {
    method: 'POST',
    token: accessToken,
    body: refreshToken ? { refresh_token: refreshToken } : {}
  })
}

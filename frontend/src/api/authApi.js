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
  // Resolves to { access_token, refresh_token, token_type, user } on
  // success, the backend logs the account in as part of verifying it.
  return request('/auth/verify-otp', {
    method: 'POST',
    body: { email, otp }
  })
}

export function resendOtp({ email }) {
  return request('/auth/resend-otp', {
    method: 'POST',
    body: { email }
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

export function forgotPassword({ email }) {
  return request('/auth/forgot-password', {
    method: 'POST',
    body: { email }
  })
}

export function resetPassword({ email, otp, newPassword }) {
  return request('/auth/reset-password', {
    method: 'POST',
    body: { email, otp, new_password: newPassword }
  })
}

export function updateProfile({ name, phone, accessToken }) {
  return request('/auth/me', {
    method: 'PUT',
    token: accessToken,
    body: { name, phone }
  })
}

export function changePassword({ currentPassword, newPassword, accessToken }) {
  return request('/auth/change-password', {
    method: 'POST',
    token: accessToken,
    body: { current_password: currentPassword, new_password: newPassword }
  })
}

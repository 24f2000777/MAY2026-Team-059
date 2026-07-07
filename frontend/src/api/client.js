const USERS_KEY = 'cr_users'
const SESSION_KEY = 'cr_session'

function read(key, fallback) {
  const raw = localStorage.getItem(key)
  return raw ? JSON.parse(raw) : fallback
}

function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

function uid(prefix) {
  return prefix + '_' + Math.random().toString(36).slice(2, 9)
}

export function registerUser({ name, phone, password }) {
  const users = read(USERS_KEY, [])
  if (users.some((u) => u.phone === phone)) {
    throw new Error('An account with this phone number already exists.')
  }
  const user = { id: uid('u'), name, phone, password, role: 'citizen' }
  users.push(user)
  write(USERS_KEY, users)
  return user
}

export function loginUser({ phone, password }) {
  const users = read(USERS_KEY, [])
  const user = users.find((u) => u.phone === phone && u.password === password)
  if (!user) throw new Error('Invalid phone number or password.')
  write(SESSION_KEY, user)
  return user
}

export function logoutUser() {
  localStorage.removeItem(SESSION_KEY)
}

export function getSession() {
  return read(SESSION_KEY, null)
}
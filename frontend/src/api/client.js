/**
 * MOCK DATA LAYER: NOT A REAL API CLIENT!
 
 * This file simulates a backend using localStorage so the frontend can be
 * built and tested before the real API exists. It stores plaintext
 * passwords and does everything client-side, none of this is secure or
 * production-ready.
 
 *  Do not build additional features directly on top of this file assuming
 * it is a real backend. It exists purely so pages have something to call
 * during Phases 1–4 of frontend development.
 */

const USERS_KEY = 'cr_users'
const COMPLAINTS_KEY = 'cr_complaints'
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
function seed() {
  if (!localStorage.getItem(USERS_KEY)) {
    write(USERS_KEY, [
      { id: 'u_admin', name: 'Admin User', email: 'admin@nagrikai.app', phone: '9000000001', password: 'admin123', role: 'admin' },
      { id: 'u_staff1', name: 'Ravi Kumar', email: 'ravi.staff@nagrikai.app', phone: '9000000002', password: 'staff123', role: 'staff' },
      { id: 'u_staff2', name: 'Anita Sharma', email: 'anita.staff@nagrikai.app', phone: '9000000003', password: 'staff123', role: 'staff' },
      { id: 'u_citizen1', name: 'Demo Citizen', email: 'citizen@nagrikai.app', phone: '9000000004', password: 'citizen123', role: 'citizen' }
    ])
  }
  if (!localStorage.getItem(COMPLAINTS_KEY)) {
    const now = Date.now()
    write(COMPLAINTS_KEY, [
      {
        id: uid('c'), citizenId: 'u_citizen1', citizenName: 'Demo Citizen',
        category: 'Water Leak', description: 'Burst pipe flooding the intersection at Andheri Main Road.',
        location: 'Andheri main road', pin: { x: 62, y: 30 }, severity: 'High', photo: null,
        status: 'Submitted', assignedStaffId: null, priorityScore: 92,
        history: [{ status: 'Submitted', note: 'Complaint filed by citizen.', at: now - 1000 * 60 * 60 * 3 }],
        createdAt: now - 1000 * 60 * 60 * 3
      },
      {
        id: uid('c'), citizenId: 'u_citizen1', citizenName: 'Demo Citizen',
        category: 'Pothole', description: 'Deep pothole near the bus stop in Borivalli',
        location: 'Borivalli bus stop', pin: { x: 40, y: 55 }, severity: 'Medium', photo: null,
        status: 'In Progress', assignedStaffId: 'u_staff1', priorityScore: 58,
        history: [
          { status: 'Submitted', note: 'Complaint filed by citizen.', at: now - 1000 * 60 * 60 * 30 },
          { status: 'In Progress', note: 'Assigned to Ravi Kumar.', at: now - 1000 * 60 * 60 * 20 }
        ],
        createdAt: now - 1000 * 60 * 60 * 30
      }
    ])
  }
}
seed()

// auth
export function registerUser({ name, phone, email, password }) {
  const users = read(USERS_KEY, [])
  if (users.some((u) => u.email === email)) {
    throw new Error('An account with this email already exists.')
  }
  const user = { id: uid('u'), name, phone, email, password, role: 'citizen' }
  users.push(user)
  write(USERS_KEY, users)
  return user
}

export function loginUser({ email, password }) {
  const user = read(USERS_KEY, []).find((u) => u.email === email && u.password === password)
  if (!user) throw new Error('Invalid email or password.')
  write(SESSION_KEY, user)
  return user
}

export function logoutUser() {
  localStorage.removeItem(SESSION_KEY)
}
export function getSession() {
  return read(SESSION_KEY, null)
}
export function getStaffList() {
  return read(USERS_KEY, []).filter((u) => u.role === 'staff')
}

// complaints
export function getComplaints() {
  return read(COMPLAINTS_KEY, [])
}
export function getComplaintById(id) {
  return getComplaints().find((c) => c.id === id) || null
}
export function getComplaintsForCitizen(citizenId) {
  return getComplaints().filter((c) => c.citizenId === citizenId)
}
export function getComplaintsForStaff(staffId) {
  return getComplaints().filter((c) => c.assignedStaffId === staffId)
}
function scorePriority(severity) {
  if (severity === 'High') return 80 + Math.floor(Math.random() * 20)
  if (severity === 'Medium') return 40 + Math.floor(Math.random() * 30)
  return Math.floor(Math.random() * 30)
}
export function createComplaint(data) {
  const complaints = getComplaints()
  const complaint = {
    id: uid('c'), citizenId: data.citizenId, citizenName: data.citizenName,
    category: data.category, description: data.description, location: data.location,
    pin: data.pin || { x: 50, y: 50 }, severity: data.severity, photo: data.photo || null,
    status: 'Submitted', assignedStaffId: null, priorityScore: scorePriority(data.severity),
    history: [{ status: 'Submitted', note: 'Complaint filed by citizen.', at: Date.now() }],
    createdAt: Date.now()
  }
  complaints.unshift(complaint)
  write(COMPLAINTS_KEY, complaints)
  return complaint
}
export function updateComplaintStatus(id, status, note) {
  const complaints = getComplaints()
  const complaint = complaints.find((c) => c.id === id)
  if (!complaint) throw new Error('Complaint not found.')
  complaint.status = status
  complaint.history.push({ status, note: note || `Status changed to ${status}.`, at: Date.now() })
  write(COMPLAINTS_KEY, complaints)
  return complaint
}
export function assignComplaint(id, staffId) {
  const complaints = getComplaints()
  const staff = read(USERS_KEY, []).find((u) => u.id === staffId)
  const complaint = complaints.find((c) => c.id === id)
  if (!complaint) throw new Error('Complaint not found.')
  complaint.assignedStaffId = staffId
  complaint.status = 'In Progress'
  complaint.history.push({ status: 'In Progress', note: `Assigned to ${staff ? staff.name : 'staff member'}.`, at: Date.now() })
  write(COMPLAINTS_KEY, complaints)
  return complaint
}

export function rateComplaint(id, rating, review) {
  const complaints = getComplaints()
  const complaint = complaints.find((c) => c.id === id)
  if (!complaint) throw new Error('Complaint not found.')
  complaint.rating = rating
  complaint.review = review || ''
  write(COMPLAINTS_KEY, complaints)
  return complaint
}

// ---- Feedback (general app feedback, not tied to a complaint) ----

const FEEDBACK_KEY = 'cr_feedback'

export function submitFeedback({ userId, userName, subject, message, rating }) {
  const feedback = read(FEEDBACK_KEY, [])
  const entry = { id: uid('f'), userId, userName, subject, message, rating, createdAt: Date.now() }
  feedback.unshift(entry)
  write(FEEDBACK_KEY, feedback)
  return entry
}

// Password reset / profile

export function requestPasswordReset(email) {
  const user = read(USERS_KEY, []).find((u) => u.email === email)
  if (!user) throw new Error('No account found with that email.')
  return true
}

export function resetPassword(email, newPassword) {
  const users = read(USERS_KEY, [])
  const user = users.find((u) => u.email === email)
  if (!user) throw new Error('No account found with that email.')
  user.password = newPassword
  write(USERS_KEY, users)
  return true
}

export function updateProfile(userId, { name, phone }) {
  const users = read(USERS_KEY, [])
  const user = users.find((u) => u.id === userId)
  if (!user) throw new Error('User not found.')
  user.name = name
  user.phone = phone
  write(USERS_KEY, users)
  write(SESSION_KEY, user)
  return user
}

export function changePassword(userId, currentPassword, newPassword) {
  const users = read(USERS_KEY, [])
  const user = users.find((u) => u.id === userId)
  if (!user) throw new Error('User not found.')
  if (user.password !== currentPassword) throw new Error('Current password is incorrect.')
  user.password = newPassword
  write(USERS_KEY, users)
  write(SESSION_KEY, user)
  return user
}
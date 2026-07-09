import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

import LandingPage from '../pages/LandingPage.vue'
import Login from '../pages/Login.vue'
import Register from '../pages/Register.vue'
import CitizenDashboard from '../pages/CitizenDashboard.vue'
import SubmitComplaint from '../pages/SubmitComplaint.vue'
import ComplaintDetail from '../pages/ComplaintDetail.vue'
import StaffDashboard from '../pages/StaffDashboard.vue'
import ComplaintUpdate from '../pages/ComplaintUpdate.vue'
import AdminDashboard from '../pages/AdminDashboard.vue'
import AssignmentPage from '../pages/AssignmentPage.vue'

const routes = [
  { path: '/', name: 'landing', component: LandingPage, meta: { guest: true } },
  { path: '/login', name: 'login', component: Login, meta: { guest: true } },
  { path: '/register', name: 'register', component: Register, meta: { guest: true } },
  { path: '/citizen', name: 'citizen-dashboard', component: CitizenDashboard, meta: { role: 'citizen' } },
  { path: '/citizen/new', name: 'submit-complaint', component: SubmitComplaint, meta: { role: 'citizen' } },
  { path: '/citizen/:id', name: 'complaint-detail', component: ComplaintDetail, meta: { role: 'citizen' } },
  { path: '/staff', name: 'staff-dashboard', component: StaffDashboard, meta: { role: 'staff' } },
  { path: '/staff/:id', name: 'complaint-update', component: ComplaintUpdate, meta: { role: 'staff' } },
  { path: '/admin', name: 'admin-dashboard', component: AdminDashboard, meta: { role: 'admin' } },
  { path: '/admin/assign/:id', name: 'assignment', component: AssignmentPage, meta: { role: 'admin' } }
]

const router = createRouter({ history: createWebHistory(), routes })
const homeForRole = { citizen: '/citizen', staff: '/staff', admin: '/admin' }

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.guest) return auth.isLoggedIn ? homeForRole[auth.role] : true
  if (!auth.isLoggedIn) return '/login'
  if (to.meta.role && to.meta.role !== auth.role) return homeForRole[auth.role]
  return true
})

export default router
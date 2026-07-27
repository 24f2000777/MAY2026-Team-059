import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

import Login from '../pages/Login.vue'
import Register from '../pages/Register.vue'
import LandingPage from '../pages/LandingPage.vue'
import VerifyOtp from '../pages/VerifyOtp.vue'
import ForgotPassword from '../pages/ForgotPassword.vue'
import ResetPassword from '../pages/ResetPassword.vue'

import CitizenDashboard from '../pages/CitizenDashboard.vue'
import SubmitComplaint from '../pages/SubmitComplaint.vue'
import ComplaintDetail from '../pages/ComplaintDetail.vue'
import RateReview from '../pages/RateReview.vue'
import CitizenAnalytics from '../pages/CitizenAnalytics.vue'

import StaffDashboard from '../pages/StaffDashboard.vue'
import ComplaintUpdate from '../pages/ComplaintUpdate.vue'
import StaffAnalytics from '../pages/StaffAnalytics.vue'

import AdminDashboard from '../pages/AdminDashboard.vue'
import AssignmentPage from '../pages/AssignmentPage.vue'
import AnalyticsPage from '../pages/AnalyticsPage.vue'

import NagrikSaathi from '../pages/NagrikSaathi.vue'
import Notifications from '../pages/Notifications.vue'
import Profile from '../pages/Profile.vue'
import FeedbackReport from '../pages/FeedbackReport.vue'
import Faqs from '../pages/Faqs.vue'
import PrivacyPolicy from '../pages/PrivacyPolicy.vue'
import TermsOfService from '../pages/TermsOfService.vue'
import ContactUs from '../pages/ContactUs.vue'
import NotFound from '../pages/NotFound.vue'

const routes = [
  { path: '/', name: 'landing', component: LandingPage, meta: { guest: true } },
  { path: '/login', name: 'login', component: Login, meta: { guest: true } },
  { path: '/register', name: 'register', component: Register, meta: { guest: true } },
  { path: '/verify-otp', name: 'verify-otp', component: VerifyOtp, meta: { guest: true } },
  { path: '/forgot-password', name: 'forgot-password', component: ForgotPassword, meta: { guest: true } },
  { path: '/reset-password', name: 'reset-password', component: ResetPassword, meta: { guest: true } },

  { path: '/citizen', name: 'citizen-dashboard', component: CitizenDashboard, meta: { role: 'citizen' } },
  { path: '/citizen/new', name: 'submit-complaint', component: SubmitComplaint, meta: { role: 'citizen' } },
  { path: '/citizen/analytics', name: 'citizen-analytics', component: CitizenAnalytics, meta: { role: 'citizen' } },
  { path: '/citizen/:id/rate', name: 'rate-review', component: RateReview, meta: { role: 'citizen' } },
  { path: '/citizen/:id', name: 'complaint-detail', component: ComplaintDetail, meta: { role: 'citizen' } },

  { path: '/staff', name: 'staff-dashboard', component: StaffDashboard, meta: { role: 'staff' } },
  { path: '/staff/analytics', name: 'staff-analytics', component: StaffAnalytics, meta: { role: 'staff' } },
  { path: '/staff/:id', name: 'complaint-update', component: ComplaintUpdate, meta: { role: 'staff' } },

  { path: '/admin', name: 'admin-dashboard', component: AdminDashboard, meta: { role: 'admin' } },
  { path: '/admin/assign/:id', name: 'assignment', component: AssignmentPage, meta: { role: 'admin' } },
  { path: '/admin/analytics', name: 'analytics', component: AnalyticsPage, meta: { role: 'admin' } },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFound},

  { path: '/notifications', name: 'notifications', component: Notifications },
  { path: '/profile', name: 'profile', component: Profile },
  { path: '/feedback', name: 'feedback', component: FeedbackReport },
  // Requires login: the real chat API needs a Bearer token, an
  // unauthenticated visitor can't get a reply at all.
  { path: '/nagrik-saathi', name: 'nagrik-saathi', component: NagrikSaathi },

  { path: '/faq', name: 'faq', component: Faqs, meta: { public: true } },
  { path: '/privacy', name: 'privacy', component: PrivacyPolicy, meta: { public: true } },
  { path: '/terms', name: 'terms', component: TermsOfService, meta: { public: true } },
  { path: '/contact', name: 'contact', component: ContactUs, meta: { public: true } },

]

const router = createRouter({ history: createWebHistory(), routes })
const homeForRole = { citizen: '/citizen', staff: '/staff', admin: '/admin' }

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (to.meta.guest) return auth.isLoggedIn ? homeForRole[auth.role] : true
  if (!auth.isLoggedIn) return '/login'
  if (to.meta.role && to.meta.role !== auth.role) return homeForRole[auth.role]
  return true
})

export default router
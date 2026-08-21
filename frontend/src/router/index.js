import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

// Every route component is lazy-loaded (dynamic import) instead of
// imported at the top of this file. A static import here pulls that
// page (and everything it imports) into the same eagerly-loaded
// module graph as every other route, so visiting any single page,
// even the login screen, used to fetch and parse all ~25 pages'
// worth of JS before first paint. Dynamic imports let Vite split
// each route into its own chunk, fetched only when that route is
// actually visited.
const Login = () => import('../pages/Login.vue')
const Register = () => import('../pages/Register.vue')
const LandingPage = () => import('../pages/LandingPage.vue')
const VerifyOtp = () => import('../pages/VerifyOtp.vue')
const ForgotPassword = () => import('../pages/ForgotPassword.vue')
const ResetPassword = () => import('../pages/ResetPassword.vue')

const CitizenDashboard = () => import('../pages/CitizenDashboard.vue')
const SubmitComplaint = () => import('../pages/SubmitComplaint.vue')
const ComplaintDetail = () => import('../pages/ComplaintDetail.vue')
const RateReview = () => import('../pages/RateReview.vue')
const CitizenAnalytics = () => import('../pages/CitizenAnalytics.vue')

const StaffDashboard = () => import('../pages/StaffDashboard.vue')
const ComplaintUpdate = () => import('../pages/ComplaintUpdate.vue')
const StaffAnalytics = () => import('../pages/StaffAnalytics.vue')

const AdminDashboard = () => import('../pages/AdminDashboard.vue')
const AssignmentPage = () => import('../pages/AssignmentPage.vue')
const AnalyticsPage = () => import('../pages/AnalyticsPage.vue')
const StaffManagement = () => import('../pages/StaffManagement.vue')

const NagrikSaathi = () => import('../pages/NagrikSaathi.vue')
const Notifications = () => import('../pages/Notifications.vue')
const Profile = () => import('../pages/Profile.vue')
const FeedbackReport = () => import('../pages/FeedbackReport.vue')
const Faqs = () => import('../pages/Faqs.vue')
const PrivacyPolicy = () => import('../pages/PrivacyPolicy.vue')
const TermsOfService = () => import('../pages/TermsOfService.vue')
const ContactUs = () => import('../pages/ContactUs.vue')
const NotFound = () => import('../pages/NotFound.vue')

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
  { path: '/admin/staff', name: 'staff-management', component: StaffManagement, meta: { role: 'admin' } },
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

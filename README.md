
# NagrikAI: Civic Complaint Management Platform

A civic issue-reporting platform for citizens, municipal staff, and administrators, built with Vue 3. Citizens file complaints with photos and location pins, staff manage assigned tasks, and admins oversee everything with filters and analytics.

This is the **frontend only**. It currently runs on mock data stored in the browser's `localStorage`, no backend is connected yet.


## Tech Stack

- **Vue 3** - Composition API, `<script setup>`
- **Vue Router 4** - routing, role-based route guards
- **Pinia** - state management
- **Vite** - dev server and build tool
- No UI kit, no chart library - all charts (donut, line, bar) and styling are hand-built with SVG and CSS, kept dependency-light on purpose.


## Getting Started

### Requirements
- [Node.js](https://nodejs.org) 18 or later

### Install and run

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

### Build for production

```bash
npm run build
npm run preview   # serve the production build locally
```

## Demo Logins

Accounts are seeded automatically into `localStorage` the first time the app runs.

| Role    | Email                        | Password    |
|---------|-------------------------------|--------------|
| Citizen | citizen@nagrikai.app       | citizen123   |
| Staff   | ravi.staff@nagrikai.app    | staff123     |
| Admin   | admin@nagrikai.app         | admin123     |

You can also register a new citizen account from scratch (see **Auth Flow** below).

If login ever fails with correct-looking credentials after pulling new code, clear stale local data: DevTools → Application → Local Storage → delete `cr_users` and `cr_session` → refresh.


## Features

### Public / Landing
- Marketing landing page with hero, how-it-works, feature grid, Nagrik Saathi preview, and an "For Officials" section
- Glassmorphism footer (blurred translucent background)
- Public pages reachable without login: **FAQ**, **Privacy Policy**, **Terms of Service**, **Contact Us**
- A live demo of **Nagrik Saathi**

### Authentication
- **Register** — name, email, phone, password + confirm, with phone format validation and minimum password length
- **OTP verification** — a second step after registering; a demo one-time code is generated and shown on screen (no real SMS backend exists yet)
- **Login** — email + password, redirects to the correct dashboard by role
- **Forgot / Reset Password** — email lookup, then set a new password (mocked — no real email delivery)

### Citizen
- Dashboard with a personalized greeting, quick-action tiles, and KPI cards (Total / Submitted / In Progress / Resolved)
- **Report an Issue** — category, description, severity, photo upload, click-to-pin map
- **My Complaints** — card list with status/severity badges
- **Complaint Detail** — full status timeline; once resolved, **Rate & Review** the resolution (star rating + comment)
- **My Activity (Analytics)** — status donut chart, category bar chart, resolution rate

### Staff
- Dashboard with assigned tasks sorted by priority, KPI cards
- **Update Task** — change status, add notes, view history - guarded against crashing on an invalid complaint id
- **My Performance (Analytics)** - status donut chart, category breakdown, average resolution time

### Admin
- Dashboard with KPI cards (Total / Unassigned / High Priority Open / Resolved) and a filterable data table (status, category, area, date)
- **Assign / Reassign** complaints to staff
- **Analytics** — KPI cards, 14-day filing trend line chart, status donut chart, category and resolution-time bar charts, complaint density heatmap by area — all with entrance animation

### Shared (any logged-in role)
- **Nagrik Saathi** - a scripted keyword-matched chatbot demo (not a real AI assistant unless functioanlity added)
- **Notifications** - a feed of recent status changes relevant to the logged-in user's role
- **Profile** - edit name/phone, change password
- **Feedback** - general app feedback form with a 1–5 rating
- Custom **404** page for any unmatched route


## Folder Structure

```
frontend/src/
├── pages/
│   ├── LandingPage.vue
│   ├── Login.vue / Register.vue / VerifyOtp.vue
│   ├── ForgotPassword.vue / ResetPassword.vue
│   ├── CitizenDashboard.vue / SubmitComplaint.vue / ComplaintDetail.vue / RateReview.vue /CitizenAnalytics.vue
│   ├── StaffDashboard.vue / ComplaintUpdate.vue / StaffAnalytics.vue
│   ├── AdminDashboard.vue / AssignmentPage.vue / AnalyticsPage.vue
│   ├── NagrikSaathi.vue / Notifications.vue / Profile.vue / FeedbackReport.vue
│   ├── Faqs.vue / PrivacyPolicy.vue / TermsOfService.vue / ContactUs.vue
│   └── NotFound.vue
├── components/
│   ├── Navbar.vue / DashboardHero.vue / ActionTile.vue / footer.vue
│   ├── ComplaintCard.vue / StatusBadge.vue / StatCard.vue
│   └── DonutChart.vue / LineChart.vue
├── stores/          Pinia: authStore.js, complaintStore.js
├── api/client.js    Mock data layer (see below)
├── router/index.js  All routes + role-based guards
└── assets/style.css Global styling
```

## About the Mock Data Layer

`src/api/client.js` simulates a backend using `localStorage`. It is clearly commented as mock-only at the top of the file. Every exported function (`registerUser`, `loginUser`, `getComplaints`, `createComplaint`, etc.) is written to match what a real REST endpoint would expect, so connecting a real backend later means rewriting the function bodies in this one file. No other file needs to change.

Things that are explicitly **not real** right now, by design:
- Passwords are stored in plaintext in `localStorage`
- OTP codes are generated client-side and displayed on screen, not sent via SMS/email
- Password reset has no email/token step — reaching the reset screen is treated as proof of ownership
- Nagrik Saathi is a scripted, keyword-matched demo, not a real AI, till backend with relevant functionality is connected.

---

## Placeholders

A few landing-page footer links intentionally go nowhere yet, since either no corresponding feature exists or login is required to use the same: "Try Nagrik Saathi" chatbot demo is wired up, but points back to login due to requirement.

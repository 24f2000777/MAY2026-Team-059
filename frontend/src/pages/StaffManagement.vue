<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { createStaffAccount, listOfficers } from '../api/complaintApi'

const auth = useAuthStore()
const router = useRouter()

const officers = ref([])
const loading = ref(true)
const loadError = ref('')

const name = ref('')
const phone = ref('')
const email = ref('')
const password = ref('')
const formError = ref('')
const successMessage = ref('')
const saving = ref(false)

const phonePattern = /^[0-9]{10}$/

async function load() {
  loadError.value = ''
  try {
    const data = await listOfficers({ accessToken: auth.accessToken })
    officers.value = data.officers
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function submit() {
  formError.value = ''
  successMessage.value = ''

  if (!phonePattern.test(phone.value)) {
    formError.value = 'Enter a valid 10-digit phone number.'
    return
  }
  if (password.value.length < 8) {
    formError.value = 'Password must be at least 8 characters.'
    return
  }

  saving.value = true
  try {
    await createStaffAccount({
      name: name.value,
      phone: phone.value,
      email: email.value,
      password: password.value,
      accessToken: auth.accessToken
    })
    successMessage.value = `${name.value} can now log in as staff.`
    name.value = ''
    phone.value = ''
    email.value = ''
    password.value = ''
    await load()
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="app-content staff-page">

    <!-- Header -->
    <div class="staff-header">
      <div>
        <p class="staff-eyebrow">ADMINISTRATION</p>
        <h2>Staff Management</h2>
        <p class="staff-subtitle">
          Create and manage accounts for officers handling citizen complaints.
        </p>
      </div>


    </div>

    <!-- Main layout -->
    <div class="staff-layout">

      <!-- Create account -->
      <section class="card create-card">
        <div class="section-heading">
          <div class="section-icon">+</div>
          <div>
            <h3>Create Staff Account</h3>
            <p>
              Accounts created here are active immediately.
            </p>
          </div>
        </div>

        <form @submit.prevent="submit">

          <div class="field">
            <label>Full Name</label>
            <input
              v-model="name"
              type="text"
              placeholder="Staff member's name"
              required
              autocomplete="name"
            />
          </div>

          <div class="field">
            <label>Phone Number</label>
            <input
              v-model="phone"
              type="text"
              placeholder="10-digit phone number"
              maxlength="10"
              required
              autocomplete="tel"
            />
          </div>

          <div class="field">
            <label>Email Address</label>
            <input
              v-model="email"
              type="email"
              placeholder="staff@example.com"
              required
              autocomplete="email"
            />
          </div>

          <div class="field">
            <label>Temporary Password</label>
            <input
              v-model="password"
              type="password"
              placeholder="At least 8 characters"
              required
              minlength="8"
              autocomplete="new-password"
            />
            <p class="field-help">
              The staff member can use this password to log in immediately.
            </p>
          </div>

          <p v-if="formError" class="form-message error">
            {{ formError }}
          </p>

          <p v-if="successMessage" class="form-message success">
            {{ successMessage }}
          </p>

          <button
            class="btn create-btn"
            type="submit"
            :disabled="saving"
          >
            {{ saving ? 'Creating Account...' : 'Create Staff Account' }}
          </button>

        </form>
      </section>

      <!-- Existing staff -->
      <section class="card staff-list-card">

        <div class="section-heading staff-list-heading">
          <div>
            <p class="section-eyebrow">CURRENT USERS</p>
            <h3>Existing Staff</h3>
            <p>
              Officers who can be assigned complaints.
            </p>
          </div>

          <span class="account-badge">
            {{ officers.length }}
          </span>
        </div>

        <p v-if="loadError" class="error-text">
          {{ loadError }}
        </p>

        <div v-else-if="loading" class="staff-loading">
          <div class="loading-dot"></div>
          <span>Loading staff accounts...</span>
        </div>

        <div v-else-if="officers.length === 0" class="staff-empty">
          <div class="empty-icon">+</div>
          <strong>No staff accounts yet</strong>
          <p>Create the first staff account using the form.</p>
        </div>

        <div v-else class="staff-table-wrap">
          <table class="staff-table">
            <thead>
              <tr>
                <th>Staff Member</th>
                <th>Contact</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="o in officers"
                :key="o.id"
              >
                <td>
                  <div class="staff-person">
                    <div class="staff-avatar">
                      {{ o.name?.charAt(0)?.toUpperCase() || '?' }}
                    </div>

                    <div>
                      <strong>{{ o.name }}</strong>
                      <span>{{ o.email }}</span>
                    </div>
                  </div>
                </td>

                <td>
                  <span class="phone-number">
                    {{ o.phone }}
                  </span>
                </td>

                <td>
                  <span
                    class="status-pill"
                    :class="o.is_active ? 'active' : 'inactive'"
                  >
                    <span class="status-dot"></span>
                    {{ o.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </section>

    </div>

  </div>
</template>

<style scoped>
.staff-page {
  padding-bottom: 70px;
}

.staff-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 26px;
}

.staff-eyebrow,
.section-eyebrow {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .1em;
}

.staff-header h2 {
  margin: 0 0 6px;
  color: var(--ink);
  font-size: 30px;
  font-weight: 900;
  letter-spacing: -.02em;
}

.staff-subtitle {
  margin: 0;
  color: var(--text-dim);
  font-size: 14px;
}

.staff-count span {
  color: var(--text-dim);
  font-size: 11px;
}

/* Main layout */

.staff-layout {
  display: grid;
  grid-template-columns: minmax(300px, .72fr) minmax(0, 1.28fr);
  gap: 20px;
  align-items: start;
}

.create-card,
.staff-list-card {
  margin: 0;
  padding: 24px;
  border-radius: var(--radius-lg);
}

/* Section headers */

.section-heading {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border);
}

.section-heading h3 {
  margin: 0 0 4px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
}

.section-heading p {
  margin: 0;
  color: var(--text-dim);
  font-size: 12px;
  line-height: 1.45;
}

.section-icon {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: var(--accent-glow);
  color: var(--accent-dark);
  font-size: 21px;
  font-weight: 400;
}

.section-eyebrow {
  margin-bottom: 4px !important;
}

/* Form */

.create-card .field {
  margin-bottom: 17px;
}

.create-card .field label {
  margin-bottom: 7px;
}

.field-help {
  margin: 6px 0 0;
  color: var(--text-dim);
  font-size: 11px;
  line-height: 1.4;
}

.create-btn {
  width: 100%;
  margin-top: 4px;
}

.form-message {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: var(--radius);
  font-size: 12px;
}

.form-message.error {
  color: var(--danger);
  background: rgba(192, 57, 43, .06);
  border: 1px solid rgba(192, 57, 43, .16);
}

.form-message.success {
  color: var(--ok);
  background: rgba(42, 157, 143, .07);
  border: 1px solid rgba(42, 157, 143, .18);
}

/* Staff list */

.staff-list-heading {
  align-items: center;
  margin-bottom: 0;
}

.account-badge {
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-glow);
  color: var(--accent-dark);
  font-size: 13px;
  font-weight: 800;
}

/* Table */

.staff-table-wrap {
  overflow-x: auto;
  margin: 0 -24px -24px;
}

.staff-table {
  width: 100%;
  border-collapse: collapse;
}

.staff-table th {
  padding: 11px 18px;
  background: var(--panel-alt);
  color: var(--text-dim);
  font-size: 10px;
  font-weight: 800;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: .05em;
  white-space: nowrap;
}

.staff-table td {
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.staff-table tbody tr {
  transition: background .15s ease;
}

.staff-table tbody tr:hover {
  background: var(--panel-alt);
}

.staff-table tbody tr:last-child td {
  border-bottom: none;
}

/* Person */

.staff-person {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 180px;
}

.staff-avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--accent-glow);
  color: var(--accent-dark);
  font-size: 14px;
  font-weight: 800;
}

.staff-person div:last-child {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.staff-person strong {
  color: var(--text);
  font-size: 13px;
}

.staff-person span {
  color: var(--text-dim);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.phone-number {
  color: var(--text-dim);
  font-size: 12px;
}

/* Status */

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .04em;
}

.status-pill.active {
  background: rgba(47, 143, 91, .1);
  color: var(--accent-dark);
}

.status-pill.inactive {
  background: rgba(94, 107, 90, .1);
  color: var(--text-dim);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

/* Empty/loading */

.staff-empty {
  padding: 48px 20px;
  text-align: center;
  color: var(--text-dim);
}

.empty-icon {
  width: 42px;
  height: 42px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--border);
  border-radius: 10px;
  color: var(--accent);
  font-size: 22px;
}

.staff-empty strong {
  display: block;
  margin-bottom: 4px;
  color: var(--text);
  font-size: 13px;
}

.staff-empty p {
  margin: 0;
  font-size: 12px;
}

.staff-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 50px 20px;
  color: var(--text-dim);
  font-size: 12px;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  animation: staff-pulse 1s ease-in-out infinite;
}

@keyframes staff-pulse {
  0%, 100% {
    opacity: .35;
    transform: scale(.8);
  }

  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Responsive */

@media (max-width: 900px) {
  .staff-layout {
    grid-template-columns: 1fr;
  }

  .create-card {
    max-width: none;
  }
}

@media (max-width: 620px) {
  .staff-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .staff-count {
    width: 100%;
    text-align: left;
  }

  .create-card,
  .staff-list-card {
    padding: 18px;
  }

  .staff-table-wrap {
    margin: 0 -18px -18px;
  }

  .staff-table th,
  .staff-table td {
    padding: 12px;
  }

  .staff-person {
    min-width: 150px;
  }
}
</style>

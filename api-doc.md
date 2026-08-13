# NAGRIK AI — API Documentation (Milestone 3)

## Contents

1. [Conventions](#conventions)
2. [Authentication](#1-authentication) — 11 endpoints
3. [Complaints](#2-complaints) — 9 endpoints
4. [Chat (Nagrik Saathi)](#3-chat-nagrik-saathi) — 2 endpoints
5. [ML Engine](#4-ml-engine) — 10 endpoints
6. [Dashboard](#5-dashboard) — 5 endpoints
7. [System](#6-system) — 2 endpoints
8. [Appendix A — Complaint status state machine](#appendix-a--complaint-status-state-machine)
9. [Appendix B — Error code reference](#appendix-b--error-code-reference)
10. [Appendix C — User story mapping](#appendix-c--user-story-mapping)
11. [Cross-check notes vs. the v2.0 design doc](#cross-check-notes-vs-the-v20-design-doc)

---

## Conventions

- **Base URL:** not yet fixed for prod; local dev is `http://localhost:8000`.
- **Auth:** `Authorization: Bearer <access_token>`. Access tokens expire in a short window;
  use `POST /auth/refresh` to get a new one.
- **Error envelope** — every error response has this shape:
  ```json
  { "success": false, "message": "<human readable message>", "error_code": "AUTH_001", "details": null }
  ```
  See [Appendix B](#appendix-b--error-code-reference) for the full `error_code` catalog.
- **Success envelope** — most endpoints wrap their payload the same way:
  ```json
  { "success": true, "message": "...", "data": { /* endpoint-specific */ }, "meta": null }
  ```
  A few routes (marked below) return a raw object instead of this envelope — that's a
  real inconsistency in the current build, not a typo in this doc; see the cross-check
  notes.
- **Validation errors** (422) use FastAPI's standard `HTTPValidationError` shape:
  ```json
  { "detail": [ { "loc": ["body", "email"], "msg": "field required", "type": "missing" } ] }
  ```

---

## 1. Authentication

Base path: `/auth`. Roles column shows who can call it; `Public` = no token needed.

### `POST /auth/register`
Create a new citizen account and queue an email verification OTP. Account starts
**unverified** — `POST /auth/login` will fail with `AUTH_006` until it's verified.

- **Auth:** Public
- **User story:** **US-01** — *"As a citizen, I want to create an account so I can report civic issues."*
- **Request body** (`RegisterRequest`):
  | field | type | constraints |
  |---|---|---|
  | `name` | string | 2–100 chars |
  | `phone` | string | 10–15 chars |
  | `email` | string (email) | — |
  | `password` | string | 8–128 chars |
- **Example request**
  ```json
  { "name": "Rajesh Kumar", "phone": "9876543210", "email": "rajesh@example.com", "password": "SecurePass123" }
  ```
- **Response `201`:** `SuccessResponse[None]`
  ```json
  { "success": true, "message": "Registration successful. A verification OTP has been sent.", "data": null, "meta": null }
  ```
- **Errors:** `409 AUTH_007` (email already registered & verified) · `409 AUTH_008` (phone already registered) · `422 VAL_001`

### `POST /auth/verify-otp`
Activates the account and **logs the user straight in** — returns the same
access/refresh token pair `POST /auth/login` does, so the client never needs to hold the
plaintext password just to log in right after verifying.

- **Auth:** Public
- **User story:** *"As a new user, I want to verify my email via OTP so my account is activated."* — not present as a distinct US-code in the v2.0 design doc; folds under US-01. See [cross-check notes](#cross-check-notes-vs-the-v20-design-doc).
- **Request body** (`VerifyOTPRequest`): `email` (string), `otp` (string, exactly 6 chars)
- **Example request**
  ```json
  { "email": "rajesh@example.com", "otp": "482913" }
  ```
- **Response `200`:** `SuccessResponse[TokenResponse]` — see the `TokenResponse` shape under `/auth/login` below.
- **Errors:** `404 AUTH_009` (email not registered) · `409 AUTH_011` (already verified) · `400 AUTH_010` (OTP wrong/expired)

### `POST /auth/resend-otp`
Resends the verification OTP for a pending (unverified) account.

- **Auth:** Public
- **User story:** *"As a new user, I want to request a new OTP if the first one expired or I didn't receive it."* — new, not in v2.0 design doc.
- **Request body** (`ResendOTPRequest`): `email` (string)
- **Response `200`:** `SuccessResponse[None]`
- **Errors:** `404 AUTH_009` · `409 AUTH_011` · `429 RTE_001` (rate-limited per email)

### `POST /auth/login`
Authenticate with email + password, receive an access/refresh token pair.

- **Auth:** Public
- **User story:** **US-01**
- **Request body** (`LoginRequest`): `email` (string, email), `password` (string)
- **Example request**
  ```json
  { "email": "rajesh@example.com", "password": "SecurePass123" }
  ```
- **Response `200`:** `SuccessResponse[TokenResponse]`
  ```json
  {
    "success": true,
    "message": "Login successful.",
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "user": {
        "id": "999e8877-e66b-21d3-b456-526614174999",
        "name": "Rajesh Kumar",
        "phone": "9876543210",
        "email": "rajesh@example.com",
        "role": "citizen",
        "is_active": true,
        "created_at": "2026-07-20T09:00:00Z"
      }
    },
    "meta": null
  }
  ```
- **Errors:** `401 AUTH_001` (invalid email/password) · `403 AUTH_006` (email not verified)

### `POST /auth/refresh`
Exchange a valid, unexpired, non-revoked refresh token for a new access token.

- **Auth:** Bearer (the refresh token itself, passed in the body — not the header)
- **User story:** *"As a logged-in user, I want my session refreshed without re-entering my password."* — supporting US-01, no separate design-doc code.
- **Request body** (`RefreshTokenRequest`): `refresh_token` (string)
- **Response `200`:** `SuccessResponse[TokenResponse]` (same shape as login)
- **Errors:** `401 AUTH_002` (expired) · `401 AUTH_003` (malformed / wrong type / revoked via logout) · `404 AUTH_009` · `403 AUTH_006`

### `GET /auth/me`
Return the caller's own profile. Pure passthrough of the JWT-loaded user, no extra DB call.

- **Auth:** Bearer · All roles
- **User story:** **US-01**
- **Response `200`:** `SuccessResponse[UserResponse]`
  ```json
  {
    "success": true,
    "message": "Profile fetched.",
    "data": {
      "id": "999e8877-e66b-21d3-b456-526614174999",
      "name": "Rajesh Kumar",
      "phone": "9876543210",
      "email": "rajesh@example.com",
      "role": "citizen",
      "is_active": true,
      "created_at": "2026-07-20T09:00:00Z"
    },
    "meta": null
  }
  ```
- **Errors:** `401 AUTH_003` (no/invalid token)

### `PUT /auth/me`
Update the caller's own `name` and/or `phone`. **Email and address are not editable
here** — changing email would invalidate verification status and needs its own
re-verification flow; address isn't part of the current `User` model at all.

- **Auth:** Bearer · All roles
- **User story:** **US-01**
- **Request body** (`UpdateProfileRequest`) — both fields optional, at least one expected:
  | field | type | constraints |
  |---|---|---|
  | `name` | string \| null | 2–100 chars |
  | `phone` | string \| null | 10–15 chars |
- **Example request**
  ```json
  { "phone": "9123456780" }
  ```
- **Response `200`:** `SuccessResponse[UserResponse]`
- **Errors:** `409 AUTH_008` (new phone already registered to a different account) · `422 VAL_001`

### `POST /auth/change-password`
Change the current (already logged-in) user's password. Distinct from the OTP-based
forgot/reset flow below.

- **Auth:** Bearer · All roles
- **User story:** *"As a logged-in user, I want to change my password."* — no design-doc US code.
- **Request body** (`ChangePasswordRequest`): `current_password` (string), `new_password` (string, 8–128 chars)
- **Response `200`:** `SuccessResponse[None]`
- **Errors:** `401 AUTH_001` (current password wrong, or new == old)

### `POST /auth/forgot-password`
Send a password-reset OTP to a **verified** user's email.

- **Auth:** Public
- **User story:** *"As a user who forgot their password, I want to request a reset OTP."* — no design-doc US code.
- **Request body** (`ForgotPasswordRequest`): `email` (string)
- **Response `200`:** `SuccessResponse[None]`
- **Errors:** `429 RTE_001` (>3 requests/hour for this email) · `404 AUTH_009` · `403 AUTH_006`

### `POST /auth/reset-password`
Set a new password after verifying the reset OTP.

- **Auth:** Public
- **User story:** *"As a user resetting my password, I want to set a new one using my reset OTP."* — no design-doc US code.
- **Request body** (`ResetPasswordRequest`): `email` (string), `otp` (string, 6 chars), `new_password` (string, 8–128 chars)
- **Response `200`:** `SuccessResponse[None]`
- **Errors:** `404 AUTH_009` · `403 AUTH_006` · `400 AUTH_010` (bad/expired OTP) · `400 AUTH_001` (new password same as current)

### `POST /auth/logout`
Revoke the current session's tokens via a Redis blacklist. The access token (taken from
the `Authorization` header) is always revoked; the refresh token is also revoked if
supplied in the body.

- **Auth:** Bearer · All roles
- **User story:** *"As a logged-in user, I want to log out so my session token is revoked."* — no design-doc US code.
- **Request body** (`LogoutRequest`): `refresh_token` (string \| null, optional)
- **Response `200`:** `SuccessResponse[None]`

---

## 2. Complaints

Base path: `/complaints`.

### `POST /complaints`
File a new complaint. Immediately scored and routed by the ML pipeline (priority score,
department, high-risk flag) — the same services the `/ml/*` endpoints expose individually.

- **Auth:** Bearer · Citizen
- **User story:** **US-02**
- **Request body** (`ComplaintCreate`):
  | field | type | constraints |
  |---|---|---|
  | `title` | string | 5–100 chars |
  | `description` | string | 20–1000 chars |
  | `category` | enum | `road`, `pothole`, `streetlight`, `drainage`, `garbage`, `water_supply`, `sewage`, `traffic`, `electricity`, `other` |
  | `location` | `ComplaintLocation` | either `address`, or `latitude`+`longitude`, must be provided |
- **Example request**
  ```json
  {
    "title": "Large pothole on main road",
    "description": "There is a dangerous pothole near the school gate causing accidents.",
    "category": "pothole",
    "location": { "address": "Near Patel Chowk, Patan", "latitude": 23.0225, "longitude": 72.5714 }
  }
  ```
- **Response `201`** (untyped `dict` in the current build — real values below, from M3 test case 7):
  ```json
  { "id": "123e4567-e89b-12d3-a456-426614174000", "status": "submitted", "priority_score": 74, "category": "streetlight" }
  ```
- **Errors:** `422 VAL_001` (description under 20 chars, or location missing both address and coordinates) · `422 VAL_002` (lat/long given without the other)

### `GET /complaints/whoami`
Confirm which account the caller is authenticated as. Debug/utility endpoint, not tied
to a citizen-facing user story.

- **Auth:** Bearer · All roles
- **User story:** *"As a logged-in user, I want to confirm which account I'm authenticated as."* — new, not in v2.0 design doc.
- **Response `200`:** untyped `dict`, echoes the caller's id/role.

### `PATCH /complaints/{complaint_id}/assign`
Assign a complaint to a staff member. **Does not change status** — "who's responsible"
and "what stage it's at" are deliberately separate; see `/start` for the actual
approved → in_progress transition, which requires the complaint to already be assigned.

- **Auth:** Bearer · **Admin only**
- **User story:** **US-04 / US-05** (loosely — the v2.0 design doc doesn't have a literal `/complaints/{id}/assign` mapping; it lists a `/admin/assign` under US-04 that doesn't exist as a real path in this build)
- **Request body** (`ComplaintAssignRequest`): `assigned_to` (UUID, required), `notes` (string ≤500, optional)
- **Example request**
  ```json
  { "assigned_to": "550e8400-e29b-41d4-a716-446655440000", "notes": "High priority, assign senior staff" }
  ```
- **Response `200`:** `SuccessResponse[ComplaintAssignResponse]`
  ```json
  {
    "success": true,
    "message": "Complaint assigned.",
    "data": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Large pothole on main road",
      "description": "There is a dangerous pothole near the school gate causing accidents.",
      "category": "pothole",
      "status": "approved",
      "priority_score": 85,
      "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
      "staff_details": { "id": "550e8400-e29b-41d4-a716-446655440000", "name": "Rajesh Kumar", "role": "staff", "department": "Roads Department" },
      "citizen_id": "999e8877-e66b-21d3-b456-526614174999",
      "created_at": "2026-07-23T21:00:00Z",
      "updated_at": "2026-07-24T00:30:00Z"
    },
    "meta": null
  }
  ```
- **Errors:** `403 AUTH_004` (caller isn't admin) · `404 COMP_001` · `409 COMP_003` (complaint already terminal) · `422 COMP_002` (`assigned_to` isn't an existing user with role `staff`)

### `POST /complaints/{complaint_id}/updates`
Add an internal note to a complaint. **Never visible to the citizen** who filed it. The
author is derived from the JWT, never accepted from the client.

- **Auth:** Bearer · Staff, Admin
- **User story:** **US-12**
- **Request body** (`ComplaintNoteCreateRequest`): `note_text` (string, 1–2000 chars)
- **Example request**
  ```json
  { "note_text": "Spoke with resident and scheduled a follow-up inspection for tomorrow." }
  ```
- **Response `201`:** `SuccessResponse[ComplaintNote]`
  ```json
  {
    "success": true,
    "message": "Note added.",
    "data": {
      "id": "7c1e2f3a-9b4d-4e5f-8a6b-1c2d3e4f5a6b",
      "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
      "note_text": "Spoke with resident and scheduled a follow-up inspection for tomorrow.",
      "author": { "id": "550e8400-e29b-41d4-a716-446655440000", "name": "Rajesh Kumar", "role": "staff" },
      "created_at": "2026-07-24T10:15:00Z",
      "visibility": "internal"
    },
    "meta": null
  }
  ```
- **Errors:** `404 COMP_001`

### `GET /complaints/{complaint_id}/updates`
List every internal note on a complaint, oldest first. Same visibility rule as above.

- **Auth:** Bearer · Staff, Admin
- **User story:** **US-12**
- **Response `200`:** `SuccessResponse[ComplaintNoteListResponse]` — `data.notes` is an array of the `ComplaintNote` object shown above.
- **Errors:** `404 COMP_001`

### `PATCH /complaints/{complaint_id}/approve`
`submitted` → `approved`.

- **Auth:** Bearer · **Admin only**
- **User story:** **US-05**
- **Request body** (`ComplaintTransitionRequest`): `notes` (string ≤500, optional)
- **Example request**
  ```json
  { "notes": "Confirmed with the ward office, proceeding." }
  ```
- **Response `200`:** `SuccessResponse[ComplaintStatusResponse]`
  ```json
  { "success": true, "message": "Complaint approved.", "data": { "id": "123e4567-e89b-12d3-a456-426614174000", "status": "approved", "assigned_to": null, "reject_reason": null, "updated_at": "2026-07-24T10:15:00Z" }, "meta": null }
  ```
- **Errors:** `404 COMP_001` · `409 COMP_004` (not currently `submitted`)

### `PATCH /complaints/{complaint_id}/reject`
`submitted` or `approved` → `rejected`. Unlike approve/start/resolve, a **reason is
required**, stored on `reject_reason` and logged.

- **Auth:** Bearer · **Admin only**
- **User story:** **US-05**
- **Request body** (`ComplaintRejectRequest`): `reason` (string, 5–500 chars, required)
- **Example request**
  ```json
  { "reason": "Duplicate of an already-filed complaint in this ward." }
  ```
- **Response `200`:** `SuccessResponse[ComplaintStatusResponse]`
- **Errors:** `404 COMP_001` · `409 COMP_004` (not currently `submitted` or `approved`)

### `PATCH /complaints/{complaint_id}/start`
`approved` → `in_progress`. The complaint must already be assigned (via `/assign`
first) — a staff caller can only start their own assigned work; an admin can start any.

- **Auth:** Bearer · Staff, Admin
- **User story:** **US-05**
- **Request body** (`ComplaintTransitionRequest`): `notes` (optional)
- **Response `200`:** `SuccessResponse[ComplaintStatusResponse]`
- **Errors:** `404 COMP_001` · `409 COMP_004` (not `approved`, or unassigned) · `403 COMP_005` (staff caller isn't the assignee)

### `PATCH /complaints/{complaint_id}/resolve`
`in_progress` → `resolved`. Same assignment rule as `/start`.

- **Auth:** Bearer · Staff, Admin
- **User story:** **US-05**
- **Request body** (`ComplaintTransitionRequest`): `notes` (optional)
- **Response `200`:** `SuccessResponse[ComplaintStatusResponse]`
- **Errors:** `404 COMP_001` · `409 COMP_004` (not `in_progress`) · `403 COMP_005`

---

## 3. Chat (Nagrik Saathi)

Base path: `/chat`.

### `POST /chat/message`
Sends a message to Nagrik Saathi and returns its reply, logging both to
`chat_sessions`. **Not read-only** — the chatbot can file a real complaint directly from
the conversation (see [cross-check notes](#cross-check-notes-vs-the-v20-design-doc)).

- **Auth:** Bearer (citizen)
- **User story:** **US-07**
- **Request body** (`ChatMessageRequest`): `session_id` (string, 1–100 chars), `message` (string, 1–2000 chars)
- **Example request**
  ```json
  { "session_id": "8f14e45f-ceea-4d6b-9d8c-2f1a3b4c5d6e", "message": "There's a broken streetlight outside my building on Linking Road" }
  ```
- **Response `200`** (untyped `dict` — example from M3 test case 18):
  ```json
  { "session_id": "8f14e45f-ceea-4d6b-9d8c-2f1a3b4c5d6e", "reply": "I've noted the streetlight issue and filed it as a complaint. For anything more specific, the BMC helpline can also assist.", "complaint_filed": true }
  ```
- **Errors:** `422 VAL_001`

### `GET /chat/history/{session_id}`
Returns every message in a chat session, in order, scoped to the caller's own sessions.

- **Auth:** Bearer
- **User story:** **US-07**
- **Path param:** `session_id` (string)
- **Response `200`** (untyped `dict` — example from M3 test case 19):
  ```json
  {
    "session_id": "8f14e45f-ceea-4d6b-9d8c-2f1a3b4c5d6e",
    "messages": [
      { "role": "user", "text": "There's a broken streetlight outside my building on Linking Road", "timestamp": "2026-07-24T11:00:00Z" },
      { "role": "assistant", "text": "I've noted the streetlight issue and filed it as a complaint.", "timestamp": "2026-07-24T11:00:03Z" }
    ]
  }
  ```
- **Errors:** `403 AUTH_012` (session belongs to a different user) · `422 VAL_001`

---

## 4. ML Engine

Base path: `/ml`. All ML endpoints operate on an **existing complaint by ID** (not
arbitrary free text) except `/check-duplicate`, which is the one pre-submission,
text-in-body check. See [cross-check notes](#cross-check-notes-vs-the-v20-design-doc)
for how this differs from the v2.0 design doc.

### `GET /ml/priority/{complaint_id}`
Returns the complaint's current **stored** `priority_score`, without recomputing it.

- **Auth:** Bearer
- **User story:** **US-03**
- **Response `200`** (untyped `dict` — example from M3 test case 20): `{ "priority_score": 74 }`
- **Errors:** `404 COMP_001`

### `POST /ml/priority/{complaint_id}`
Recomputes and saves `priority_score` for one complaint, flagging it high-risk if applicable.

- **Auth:** Bearer
- **User story:** **US-03**
- **Response `200`:** untyped `dict`, same shape as the GET above.
- **Errors:** `404 COMP_001` · `503 ML_001` (model not loaded) · `500 ML_002` (scoring failed)

### `POST /ml/rescore-all`
Recomputes `priority_score` for **every** complaint. Also runs nightly via Celery Beat.

- **Auth:** Bearer
- **User story:** **US-03** (batch extension — no distinct design-doc code)
- **Response `200`:** untyped `dict` (job/summary info).

### `GET /ml/categorize/{complaint_id}`
Returns the complaint's current category, without recomputing it.

- **Auth:** Bearer
- **User story:** **US-03**
- **Response `200`:** untyped `dict`, e.g. `{ "category": "streetlight" }`
- **Errors:** `404 COMP_001`

### `POST /ml/categorize/{complaint_id}`
Re-predicts and **overwrites** the category from the complaint's own title/description.

- **Auth:** Bearer
- **User story:** **US-03**
- **Response `200`:** untyped `dict`, same shape as the GET above.
- **Errors:** `404 COMP_001` · `503 ML_001` · `500 ML_002`

### `GET /ml/route-department/{complaint_id}`
Returns the complaint's current department assignment, without recomputing it.

- **Auth:** Bearer
- **User story:** **US-04**
- **Response `200`** (untyped `dict` — example from M3 test case 21): `{ "department_name": "Water Supply Department" }`
- **Errors:** `404 COMP_001`

### `POST /ml/route-department/{complaint_id}`
Re-routes the complaint to a department based on its current category and description.

- **Auth:** Bearer
- **User story:** **US-04**
- **Response `200`:** untyped `dict`, same shape as the GET above.
- **Errors:** `404 COMP_001` · `503 ML_001` · `500 ML_002`

### `GET /ml/high-risk`
Lists every complaint currently at or above the high-risk priority threshold.

- **Auth:** Bearer
- **User story:** *"As an admin, I want to see which complaints have been flagged high-risk so I can prioritize them."* — new, not in v2.0 design doc.
- **Response `200`:** untyped `dict` — list of complaint summaries.

### `POST /ml/check-duplicate`
Checks a **not-yet-submitted** complaint (title + description) against existing ones,
so a citizen can be warned before filing a duplicate. The only ML endpoint that takes
free text in the body rather than a complaint ID.

- **Auth:** Bearer
- **User story:** **US-11**
- **Request body** (`DuplicateCheckRequest`): `title` (string, 5–200 chars), `description` (string, 20–1000 chars)
- **Response `200`** (untyped `dict` — example from M3 test case 22): `{ "count": 0, "matches": [] }`
- **Errors:** `422 VAL_001`

### `GET /ml/duplicates/{complaint_id}`
Lists existing complaints that look like duplicates of this already-filed complaint.

- **Auth:** Bearer
- **User story:** **US-11**
- **Response `200`:** untyped `dict`, similarity-ranked complaint list.
- **Errors:** `404 COMP_001`

---

## 5. Dashboard

Base path: `/dashboard`. **All five of these are explicitly documented as placeholders**
in the generated spec — they don't yet read from the (now-complete) Complaint module.
See M3 report §3.5, test case 23.

### `GET /dashboard`
Tells the caller which role-specific dashboard endpoint to route to. Any authenticated
user can call this — the role-specific endpoints below enforce actual access.

- **Auth:** Bearer · All roles
- **User story:** *"As a user, I want a role-appropriate summary dashboard when I log in."*

### `GET /dashboard/citizen`
**Placeholder.** Will show the citizen's own complaints, statuses, and notifications.

- **Auth:** Bearer · Citizen
- **User story:** **US-06** (partial — real data pending)
- **Response `200`** (actual, from M3 test case 23):
  ```json
  { "success": true, "message": "...", "data": { "name": "Rajesh Kumar", "note": "Placeholder, real complaint/notification data lands here once the Complaint module is built." }, "meta": null }
  ```

### `GET /dashboard/staff`
**Placeholder.** Will show complaints assigned to this staff member and ward-level views.

- **Auth:** Bearer · Staff
- **User story:** no direct design-doc mapping.

### `GET /dashboard/admin`
**Placeholder.** Will show platform-wide analytics, user management, department management.

- **Auth:** Bearer · Admin
- **User story:** **US-08** (partial — real data pending)

### `GET /dashboard/internal`
**Placeholder.** Exists to prove a route can accept multiple roles — Staff or Admin only, not Citizen.

- **Auth:** Bearer · Staff, Admin
- **User story:** no direct design-doc mapping.

---

## 6. System

### `GET /`
Root — confirms the API is reachable.

- **Auth:** Public
- **Response `200`:** `SuccessResponse[None]`

### `GET /health`
Health check endpoint for uptime monitoring.

- **Auth:** Public
- **Response `200`:** `SuccessResponse[dict]` (actual shape not enumerated by the generated spec — likely `{status, timestamp}` based on typical FastAPI health checks; **confirm exact fields with Akshit/Amit before treating this as final**).

---

## Appendix A — Complaint status state machine

Built from the transition endpoints' own descriptions in the generated spec (note: these
state names — `submitted`, `approved`, `in_progress`, `resolved`, `rejected` — differ
from the v2.0 design doc's `PENDING_APPROVAL` / `IN_PROGRESS` / etc.; see cross-check notes).

| From | To | Trigger | Who |
|---|---|---|---|
| `submitted` | `approved` | `PATCH /complaints/{id}/approve` | Admin |
| `submitted` or `approved` | `rejected` | `PATCH /complaints/{id}/reject` | Admin |
| `approved` (+ assigned) | `in_progress` | `PATCH /complaints/{id}/start` | Staff (own), Admin (any) |
| `in_progress` | `resolved` | `PATCH /complaints/{id}/resolve` | Staff (own), Admin (any) |

`resolved`, `rejected`, `closed`, and `withdrawn` are referenced as terminal /
non-assignable states in `ComplaintAssignResponse`'s description, but **no endpoint in
Milestone 3 currently transitions a complaint to `closed` or `withdrawn`** — those exist
in the data model but not yet in the API surface.

---

## Appendix B — Error code reference

Pulled verbatim from the generated spec's `x-error-codes` extension — this is the
authoritative list, not the v2.0 design doc's (which is stale in several places).

| Code | HTTP | Meaning |
|---|---|---|
| `AUTH_000` | 400 | Unmapped authentication error (fallback) |
| `AUTH_001` | 401 | Invalid email or password |
| `AUTH_002` | 401 | JWT token expired |
| `AUTH_003` | 401 | JWT token invalid/malformed |
| `AUTH_004` | 403 | Authenticated user's role isn't allowed to access this route |
| `AUTH_005` | 403 | Account deactivated by an admin (reserved, not yet issued) |
| `AUTH_006` | 403 | Email not verified |
| `AUTH_007` | 409 | Email already registered |
| `AUTH_008` | 409 | Phone number already registered |
| `AUTH_009` | 404 | User not found |
| `AUTH_010` | 400 | OTP invalid or expired |
| `AUTH_011` | 409 | Account already verified |
| `AUTH_012` | 403 | Chat session belongs to a different user |
| `COMP_000` | 400 | Unmapped complaint-domain error (fallback) |
| `COMP_001` | 404 | Complaint not found |
| `COMP_002` | 422 | `assigned_to` is not an existing user with role `staff` |
| `COMP_003` | 409 | Complaint is already in a terminal state, can no longer be assigned |
| `COMP_004` | 409 | Status transition not valid from the complaint's current status |
| `COMP_005` | 403 | Staff caller is not the complaint's assigned staff member |
| `RTE_001` | 429 | Rate limit exceeded |
| `VAL_001` | 422 | Request validation failed (generic) / location missing both address and coordinates |
| `VAL_002` | 422 | Latitude and longitude must be provided together |
| `ML_001` | 503 | ML model not initialised at startup |
| `ML_002` | 500 | Priority scoring threw an exception |
| `ML_003` | 503 | Vector index not built yet |

---

## Appendix C — User story mapping

| Story | Description | Milestone 3 endpoints |
|---|---|---|
| US-01 | Citizen registers and logs in | `/auth/register`, `/auth/verify-otp`*, `/auth/resend-otp`*, `/auth/login`, `/auth/refresh`*, `/auth/me` (GET/PUT) |
| US-02 | Citizen files a complaint | `POST /complaints` (attachments not yet built — see Milestone 3 report §5 item 6) |
| US-03 | System auto-categorizes + scores priority | `/ml/priority/{id}`, `/ml/categorize/{id}`, `/ml/rescore-all` |
| US-04 | Complaint routed to correct department | `/ml/route-department/{id}`, `PATCH /complaints/{id}/assign`* |
| US-05 | Officer reviews and updates complaint status | `/complaints/{id}/approve`, `/reject`, `/start`, `/resolve` |
| US-06 | Citizen tracks complaint status in real time | `GET /dashboard/citizen` (placeholder only — see Appendix in M3 report) |
| US-07 | Citizen interacts with the chatbot | `/chat/message`, `/chat/history/{id}` |
| US-08 | Admin views analytics dashboard | `GET /dashboard/admin` (placeholder only) |
| US-11 | Duplicate complaint detection | `/ml/check-duplicate`, `/ml/duplicates/{id}` |
| US-12 | Officer adds internal notes | `POST/GET /complaints/{id}/updates` |

\* = mapped here by inference; not a literal 1:1 match to the v2.0 design doc's original
endpoint list for that story (see below).

Design-doc stories with **no Milestone 3 endpoint yet**: US-09 (notifications), US-10
(photo evidence upload — table exists, no upload endpoint), US-13 (department
management APIs).

---

## Cross-check notes vs. the v2.0 design doc

These are differences found while building this doc directly from `Backend/openapi.yaml`
rather than by re-describing the design doc. Flagging them here since "cross-check for
accuracy" was explicitly part of the issue.

1. **Endpoint count.** The Milestone 3 report's summary says "34 backend API endpoints,"
   but its own six module tables sum to **39** (11+9+2+10+5+2). Worth fixing the
   headline number in a report erratum, or clarifying which 5 were meant to be excluded.
2. **Login is email-based, not phone-based.** The v2.0 design doc's error table and
   rate-limit note describe `AUTH_001` and password reset in terms of phone number; the
   real implementation is entirely email-based for login. Doc-only issue, already
   flagged to Amit separately.
3. **`AUTH_003` changed meaning.** Design doc: `TOKEN_INVALID` (bad signature). Real
   spec: any missing/invalid/malformed/revoked token collapses into `AUTH_003`, with
   `AUTH_002` reserved specifically for expiry. Not wrong, just narrower than documented.
4. **`COMP_002` changed meaning entirely.** Design doc: `COMP_002 = INVALID_STATUS_TRANSITION`.
   Real spec: `COMP_002` is now the `assigned_to`-not-staff validation error, and
   `INVALID_STATUS_TRANSITION` moved to `COMP_004`. Any old references to `COMP_002` in
   frontend error-handling code should be checked against this.
5. **ML endpoints operate on complaint IDs, not raw text.** The design doc has
   `POST /ml/categorize` and `POST /ml/route-department` as stateless predictors taking
   raw text/category in the body. The real endpoints are ID-scoped
   (`/ml/categorize/{complaint_id}`, `/ml/route-department/{complaint_id}`) and operate
   on an already-existing complaint. The "check before submitting" use case only exists
   for duplicates (`/ml/check-duplicate`), not category or routing.
6. **Chatbot is not read-only.** Design doc: *"It does NOT modify any data — read-only
   assistant only."* Real spec + M3 report: `/chat/message` can file a real complaint
   from the conversation. This is the most significant doc/behavior mismatch found.
7. **Complaint state names differ.** Design doc uses `PENDING_APPROVAL`, `IN_PROGRESS`,
   etc. (upper snake case). Real implementation uses `submitted`, `in_progress`, etc.
   (lower snake case, and `PENDING_APPROVAL` → `submitted`).
8. **New endpoints not in the v2.0 design doc at all:** `/auth/verify-otp`,
   `/auth/resend-otp`, `/complaints/whoami`, `/ml/high-risk`.
9. **Design-doc endpoints not present in Milestone 3:** `GET /ml/model-info`,
   `GET /ml/feature-importance`, `POST /ml/merge-duplicates`, `GET /ml/duplicate-groups`,
   `GET /health/ml`, all Attachment/Notification/Reminder/Feedback/Department/Admin
   analytics groups, and 7 of the 9 designed chatbot endpoints (KB management,
   `/chat/status/{id}`, `/chat/feedback`, `DELETE /chat/history/{id}`).

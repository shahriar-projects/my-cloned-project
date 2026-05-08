# Streamlit UI Plan — Student Enrollment App

## App Goal

Build a two-page student-facing Streamlit app on top of the Session 1 backend. The student is already logged in before opening the app. The app uses the seeded student (Maya Patel, user_id: u100) as the simulated current user. No login, registration, password handling, or authentication system is needed.

---

## User Assumptions

- The student is already authenticated before the app loads.
- The simulated student is Maya Patel (user_id: u100, email: maya.patel@example.edu) from the seeded database.
- Role is set to "student" in st.session_state on load. Only students can access the app.
- No admin or instructor views are needed in this session.

---

## Backend Structure (Session 1)

- File: `enrollment_starter.py`
- Classes: `DatabaseLayer`, `EnrollmentService`
- Key service methods used by the UI:
  - `service.get_student_enrollments(user_id)` — returns currently enrolled courses
  - `service.enroll_with_key(user_id, email, key)` — validates key and enrolls
  - `service.soft_unenroll_student(user_id, course_id)` — marks status as unenrolled
  - `service.get_student_summary(user_id)` — returns count summary
- The UI calls the service layer only. No direct SQL in the UI file.

---

## Routing and Session State

Pages are controlled by `st.session_state.page`:
- `"dashboard"` → Page 1: Student Dashboard
- `"class"` → Page 2: Selected Class Page

Other session state keys:
- `st.session_state.selected_course` — the full course dict for the class page
- `st.session_state.role` — set to `"student"` on load; checked before rendering
- `st.session_state.feedback` — stores a `(type, message)` tuple shown at top of dashboard after an action, then cleared

---

## Page 1: Student Dashboard

**Layout:** `st.title`, `st.caption` for student identity, `st.divider`

**Feedback banner:** If `st.session_state.feedback` is set, show `st.success`, `st.warning`, or `st.error` at the top, then clear it.

**Enrolled Classes section:**
- `st.subheader("My Enrolled Classes")`
- Loop through `service.get_student_enrollments(user_id)`
- Each course in a `st.container` with `st.columns([3, 1, 1])`
  - Column 1: course ID, name, instructor via `st.markdown` and `st.caption`
  - Column 2: `st.button("Go to Class")` → sets `selected_course` and navigates to class page
  - Column 3: `st.button("Unenroll")` → calls `soft_unenroll_student`, sets feedback, reruns
- If no enrollments: `st.info` message

**Enrollment Key section:**
- `st.subheader("Enroll in a New Class")`
- `st.form` with `st.text_input` for the key and `st.form_submit_button("Enroll")`
- On submit: call `service.enroll_with_key`. If valid → set success feedback and navigate to class page. If invalid → set error feedback.

**Summary section:**
- `st.subheader("Enrollment Summary")`
- `st.columns(3)` with `st.metric` for total records, enrolled count, unenrolled count

---

## Page 2: Selected Class Page

**Layout:** Back button → `st.title` with course ID, `st.subheader` with course name, `st.divider`

**Class details in `st.columns(2)`:**
- Column 1: Instructor name
- Column 2: Status — `st.success` if enrolled, `st.warning` otherwise

**Enrollment key display:** `st.code` block

**Unenroll button:** `st.button("Unenroll from this class")` → calls `soft_unenroll_student`, sets feedback, navigates back to dashboard

---

## Actions and Feedback

| Action | Feedback |
|--------|----------|
| Valid enrollment key | st.success — "Successfully enrolled in [course]!" |
| Invalid enrollment key | st.error — "Invalid enrollment key. Please check and try again." |
| Unenroll from dashboard | st.warning — "You have been unenrolled from [course]." |
| Unenroll from class page | st.warning — same, then navigate back |
| Empty key submitted | st.error — "Please enter an enrollment key." |

Feedback is stored in `st.session_state.feedback` as `(type, message)`, displayed on next render, then cleared.

---

## Files Changed

| File | Layer | Change |
|------|-------|--------|
| enrollment_app.py | UI layer | New file — entire Streamlit app |
| enrollment_starter.py | Backend (unchanged) | No changes needed |
| student_enrollment_practice.db | Database | Recreated on first run if missing |

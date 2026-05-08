"""
Session 2: Student Enrollment Streamlit UI
Builds on the Session 1 backend (enrollment_starter.py).
Run with: streamlit run enrollment_app.py
"""

import streamlit as st
from enrollment_starter import DatabaseLayer, EnrollmentService, DB_PATH, CURRENT_STUDENT

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Student Enrollment", page_icon="🎓", layout="centered")

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "selected_course" not in st.session_state:
    st.session_state.selected_course = None
if "role" not in st.session_state:
    st.session_state.role = "student"
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# ---------------------------------------------------------------------------
# Backend setup (student is already logged in — no login/auth needed)
# ---------------------------------------------------------------------------
db = DatabaseLayer(DB_PATH)
service = EnrollmentService(db)
service.initialize_database()

STUDENT = CURRENT_STUDENT
user_id = STUDENT["user_id"]
email = STUDENT["email"]

# ---------------------------------------------------------------------------
# Role check — only students can use this app
# ---------------------------------------------------------------------------
if st.session_state.role != "student":
    st.error("Access denied. This app is for students only.")
    st.stop()

# ---------------------------------------------------------------------------
# Helper: go back to dashboard
# ---------------------------------------------------------------------------
def go_to_dashboard():
    st.session_state.page = "dashboard"
    st.session_state.selected_course = None

# ---------------------------------------------------------------------------
# PAGE 1: Student Dashboard
# ---------------------------------------------------------------------------
def show_dashboard():
    st.title("🎓 My Enrollment Dashboard")
    st.caption(f"Logged in as: **{STUDENT['name']}** ({STUDENT['email']})")
    st.divider()

    # -- Feedback message from previous action --
    if st.session_state.feedback:
        msg_type, msg_text = st.session_state.feedback
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)
        elif msg_type == "error":
            st.error(msg_text)
        st.session_state.feedback = None

    # -- Enrolled classes --
    st.subheader("📚 My Enrolled Classes")
    enrollments = service.get_student_enrollments(user_id)

    if not enrollments:
        st.info("You are not currently enrolled in any classes.")
    else:
        for course in enrollments:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{course['course_id']}** — {course['course_name']}")
                    st.caption(f"Instructor: {course['instructor']}")
                with col2:
                    if st.button("Go to Class", key=f"goto_{course['course_id']}"):
                        st.session_state.selected_course = course
                        st.session_state.page = "class"
                        st.rerun()
                with col3:
                    if st.button("Unenroll", key=f"unenroll_{course['course_id']}"):
                        success = service.soft_unenroll_student(user_id, course["course_id"])
                        if success:
                            st.session_state.feedback = ("warning", f"You have been unenrolled from {course['course_name']}.")
                        else:
                            st.session_state.feedback = ("error", "Unenrollment failed. Please try again.")
                        st.rerun()
            st.divider()

    # -- Enrollment key entry --
    st.subheader("🔑 Enroll in a New Class")
    with st.form("enroll_form"):
        key_input = st.text_input("Enter enrollment key", placeholder="e.g. MISY350-SPRING")
        submitted = st.form_submit_button("Enroll")
        if submitted:
            if not key_input.strip():
                st.session_state.feedback = ("error", "Please enter an enrollment key.")
            else:
                result = service.enroll_with_key(user_id, email, key_input.strip())
                if result:
                    course_id = result["course_id"]
                    enrolled = next((c for c in service.get_student_enrollments(user_id) if c["course_id"] == course_id), None)
                    st.session_state.feedback = ("success", f"Successfully enrolled in {course_id}!")
                    if enrolled:
                        st.session_state.selected_course = enrolled
                        st.session_state.page = "class"
                else:
                    st.session_state.feedback = ("error", "Invalid enrollment key. Please check and try again.")
            st.rerun()

    # -- Summary --
    st.divider()
    st.subheader("📊 Enrollment Summary")
    summary = service.get_student_summary(user_id)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", summary["total_records"])
    col2.metric("Currently Enrolled", summary.get("enrolled", 0))
    col3.metric("Unenrolled", summary.get("unenrolled", 0))


# ---------------------------------------------------------------------------
# PAGE 2: Selected Class Page
# ---------------------------------------------------------------------------
def show_class_page():
    course = st.session_state.selected_course

    if not course:
        go_to_dashboard()
        st.rerun()
        return

    if st.button("← Back to Dashboard"):
        go_to_dashboard()
        st.rerun()

    st.title(f"📖 {course['course_id']}")
    st.subheader(course["course_name"])
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Instructor**")
        st.write(course["instructor"])
    with col2:
        st.markdown("**Your Status**")
        status = course.get("status", "enrolled")
        if status == "enrolled":
            st.success("Enrolled")
        else:
            st.warning(status.capitalize())

    st.divider()
    st.markdown("**Enrollment Key**")
    st.code(course.get("enrollment_key", "N/A"))

    st.divider()
    if st.button("Unenroll from this class", type="secondary"):
        success = service.soft_unenroll_student(user_id, course["course_id"])
        if success:
            st.session_state.feedback = ("warning", f"You have been unenrolled from {course['course_name']}.")
        else:
            st.session_state.feedback = ("error", "Unenrollment failed. Please try again.")
        go_to_dashboard()
        st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if st.session_state.page == "dashboard":
    show_dashboard()
elif st.session_state.page == "class":
    show_class_page()

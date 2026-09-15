"""
services/attendance_service.py - Attendance Business Logic

Handles:
  - Marking attendance (with duplicate prevention)
  - Querying today's attendance
  - Dashboard statistics
"""

from datetime import datetime, date
from sqlalchemy.exc import IntegrityError

from utils.database import db
from models.student import Student
from models.attendance import Attendance
from config import ATTENDANCE_STATUS_PRESENT


# ─── Mark Attendance ──────────────────────────────────────────────────────────

def mark_attendance(student: Student, confidence: float = 0.0) -> dict:
    """
    Mark a student present for today.
    Prevents duplicate attendance using both DB constraint and app-level check.

    Returns:
        dict with 'success' (bool), 'message' (str), 'record' (Attendance or None)
    """
    today = date.today().strftime('%Y-%m-%d')
    now   = datetime.now().strftime('%H:%M:%S')

    # ── Application-level duplicate check (fast path) ─────────────────────────
    existing = Attendance.query.filter_by(
        student_id=student.id,
        date=today
    ).first()

    if existing:
        return {
            'success': False,
            'message': f'Attendance already marked for {student.name} today.',
            'record':  existing,
            'duplicate': True
        }

    # ── Create new attendance record ──────────────────────────────────────────
    record = Attendance(
        student_id=student.id,
        date=today,
        time=now,
        status=ATTENDANCE_STATUS_PRESENT,
        confidence=round(confidence, 2)
    )

    try:
        db.session.add(record)
        db.session.commit()
        return {
            'success': True,
            'message': f'Attendance marked for {student.name}.',
            'record':  record,
            'duplicate': False
        }
    except IntegrityError:
        # DB-level unique constraint triggered (race condition safety net)
        db.session.rollback()
        return {
            'success': False,
            'message': f'Attendance already marked for {student.name} today.',
            'record':  None,
            'duplicate': True
        }


# ─── Dashboard Statistics ─────────────────────────────────────────────────────

def get_today_stats() -> dict:
    """
    Compute today's attendance statistics for the dashboard.

    Returns:
        dict with total, present, absent, percentage, records list
    """
    today = date.today().strftime('%Y-%m-%d')

    total_students = Student.query.count()
    present_today  = Attendance.query.filter_by(date=today, status=ATTENDANCE_STATUS_PRESENT).count()
    absent_today   = total_students - present_today
    percentage     = round((present_today / total_students * 100), 2) if total_students > 0 else 0.0

    # Today's detailed records for the dashboard table
    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .filter(Attendance.date == today)
        .order_by(Attendance.time.desc())
        .all()
    )

    return {
        'total':      total_students,
        'present':    present_today,
        'absent':     absent_today,
        'percentage': percentage,
        'records':    records,
        'date':       today
    }


# ─── Attendance Records Query (with filters) ──────────────────────────────────

def get_attendance_records(date_filter=None, student_filter=None,
                            dept_filter=None, status_filter=None,
                            page=1, per_page=20):
    """
    Retrieve paginated attendance records with optional filters.

    Returns:
        SQLAlchemy Pagination object
    """
    query = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
    )

    if date_filter:
        query = query.filter(Attendance.date == date_filter)
    if student_filter:
        query = query.filter(
            (Student.name.ilike(f'%{student_filter}%')) |
            (Student.student_id.ilike(f'%{student_filter}%'))
        )
    if dept_filter:
        query = query.filter(Student.department == dept_filter)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)

    return query.order_by(Attendance.date.desc(), Attendance.time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


# ─── Student Attendance Summary ───────────────────────────────────────────────

def get_student_summary(student: Student) -> dict:
    """Return attendance summary for a single student."""
    records = Attendance.query.filter_by(student_id=student.id).all()
    present = sum(1 for r in records if r.status == ATTENDANCE_STATUS_PRESENT)
    total   = len(records)
    absent  = total - present
    pct     = round((present / total * 100), 2) if total > 0 else 0.0
    return {
        'total':      total,
        'present':    present,
        'absent':     absent,
        'percentage': pct,
        'records':    records
    }


# ─── Monthly Stats ────────────────────────────────────────────────────────────

def get_monthly_stats(year: int, month: int) -> list:
    """
    Return per-student attendance stats for a given month.
    Result: list of dicts with student info and attendance counts.
    """
    import calendar
    month_str   = f'{year}-{month:02d}'

    students = Student.query.order_by(Student.name).all()
    results  = []

    # Count working days in that month (Mon–Sat, simple count)
    _, days_in_month = calendar.monthrange(year, month)

    for student in students:
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.date.like(f'{month_str}-%'),
            Attendance.status == ATTENDANCE_STATUS_PRESENT
        ).count()

        absent  = days_in_month - present
        pct     = round((present / days_in_month * 100), 2)

        results.append({
            'student':    student,
            'present':    present,
            'absent':     absent,
            'total_days': days_in_month,
            'percentage': pct
        })

    return results


# ─── Department Stats (for charts) ───────────────────────────────────────────

def get_department_stats(date_str: str = None) -> list:
    """Return present/total counts per department for chart data."""
    from sqlalchemy import func

    if date_str is None:
        date_str = date.today().strftime('%Y-%m-%d')

    departments = db.session.query(Student.department).distinct().all()
    results = []

    for (dept,) in departments:
        total = Student.query.filter_by(department=dept).count()
        present = (
            db.session.query(func.count(Attendance.id))
            .join(Student, Attendance.student_id == Student.id)
            .filter(Student.department == dept, Attendance.date == date_str)
            .scalar()
        )
        results.append({'department': dept, 'present': present, 'total': total})

    return results


# ─── Weekly Trend (last 7 days) ───────────────────────────────────────────────

def get_weekly_trend() -> list:
    """Return attendance percentage for each of the last 7 days."""
    from datetime import timedelta
    today  = date.today()
    total  = Student.query.count()
    trend  = []

    for i in range(6, -1, -1):
        d       = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        present = Attendance.query.filter_by(date=d, status=ATTENDANCE_STATUS_PRESENT).count()
        pct     = round((present / total * 100), 2) if total > 0 else 0.0
        trend.append({'date': d, 'present': present, 'percentage': pct})

    return trend

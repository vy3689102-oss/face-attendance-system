"""
routes/records.py - Attendance Records Browser
"""

from flask import Blueprint, render_template, request
from utils.helpers import login_required
from utils.database import db
from models.student import Student
from services.attendance_service import get_attendance_records

records_bp = Blueprint('records', __name__)


@records_bp.route('/records')
@login_required
def records():
    date_filter   = request.args.get('date', '').strip()
    student_filter = request.args.get('student', '').strip()
    dept_filter   = request.args.get('dept', '').strip()
    status_filter = request.args.get('status', '').strip()
    page          = request.args.get('page', 1, type=int)

    pagination = get_attendance_records(
        date_filter=date_filter or None,
        student_filter=student_filter or None,
        dept_filter=dept_filter or None,
        status_filter=status_filter or None,
        page=page,
        per_page=20
    )

    departments = [r[0] for r in db.session.query(Student.department).distinct().all()]

    return render_template(
        'records.html',
        pagination=pagination,
        departments=departments,
        filters={
            'date':    date_filter,
            'student': student_filter,
            'dept':    dept_filter,
            'status':  status_filter
        }
    )

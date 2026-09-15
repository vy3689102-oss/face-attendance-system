"""
routes/reports.py - Reports & Export Routes
"""

from datetime import date
from flask import Blueprint, render_template, request, jsonify
from utils.helpers import login_required
from utils.database import db
from models.student import Student
from services.attendance_service import get_monthly_stats
from services.report_service import (
    build_attendance_dataframe, build_daily_summary_df,
    build_monthly_summary_df, export_csv, export_excel,
    daily_filename, monthly_filename, student_filename
)

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def reports():
    students    = Student.query.order_by(Student.name).all()
    today       = date.today().strftime('%Y-%m-%d')
    curr_year   = date.today().year
    curr_month  = date.today().month
    return render_template('reports.html', students=students,
                           today=today, curr_year=curr_year, curr_month=curr_month)


# ── Daily Report ──────────────────────────────────────────────────────────────

@reports_bp.route('/reports/daily')
@login_required
def daily_report():
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    df       = build_daily_summary_df(date_str)
    total    = len(df)
    present  = int((df['Status'] == 'Present').sum()) if not df.empty else 0
    absent   = total - present
    pct      = round((present / total * 100), 2) if total > 0 else 0.0
    records  = df.to_dict('records')
    return jsonify({'date': date_str, 'total': total, 'present': present,
                    'absent': absent, 'percentage': pct, 'records': records})


# ── Monthly Report ────────────────────────────────────────────────────────────

@reports_bp.route('/reports/monthly')
@login_required
def monthly_report():
    year  = request.args.get('year',  date.today().year,  type=int)
    month = request.args.get('month', date.today().month, type=int)
    data  = get_monthly_stats(year, month)
    rows  = [{'student_id': r['student'].student_id,
               'name': r['student'].name,
               'department': r['student'].department,
               'present': r['present'], 'absent': r['absent'],
               'total_days': r['total_days'], 'percentage': r['percentage']}
             for r in data]
    return jsonify({'year': year, 'month': month, 'records': rows})


# ── Student Report ────────────────────────────────────────────────────────────

@reports_bp.route('/reports/student')
@login_required
def student_report():
    sid     = request.args.get('student_id', '')
    student = Student.query.filter_by(student_id=sid).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    from services.attendance_service import get_student_summary
    summary = get_student_summary(student)
    records = [{'date': r.date, 'time': r.time, 'status': r.status,
                'confidence': r.confidence} for r in summary['records']]
    return jsonify({'student': {'id': student.student_id, 'name': student.name,
                                'department': student.department},
                    'total': summary['total'], 'present': summary['present'],
                    'absent': summary['absent'], 'percentage': summary['percentage'],
                    'records': records})


# ── CSV Exports ───────────────────────────────────────────────────────────────

@reports_bp.route('/reports/export/daily/csv')
@login_required
def export_daily_csv():
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    df       = build_daily_summary_df(date_str)
    return export_csv(df, daily_filename(date_str, 'csv'))


@reports_bp.route('/reports/export/daily/excel')
@login_required
def export_daily_excel():
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    df       = build_daily_summary_df(date_str)
    return export_excel(df, daily_filename(date_str, 'xlsx'), sheet_name='Daily Report')


@reports_bp.route('/reports/export/monthly/csv')
@login_required
def export_monthly_csv():
    year  = request.args.get('year',  date.today().year,  type=int)
    month = request.args.get('month', date.today().month, type=int)
    df    = build_monthly_summary_df(year, month)
    return export_csv(df, monthly_filename(year, month, 'csv'))


@reports_bp.route('/reports/export/monthly/excel')
@login_required
def export_monthly_excel():
    year  = request.args.get('year',  date.today().year,  type=int)
    month = request.args.get('month', date.today().month, type=int)
    df    = build_monthly_summary_df(year, month)
    return export_excel(df, monthly_filename(year, month, 'xlsx'), sheet_name='Monthly Report')


@reports_bp.route('/reports/export/student/csv')
@login_required
def export_student_csv():
    sid     = request.args.get('student_id', '')
    student = db.first_or_404(db.select(Student).filter_by(student_id=sid))
    df      = build_attendance_dataframe(student_id_filter=sid)
    return export_csv(df, student_filename(sid, 'csv'))


@reports_bp.route('/reports/export/student/excel')
@login_required
def export_student_excel():
    sid     = request.args.get('student_id', '')
    student = db.first_or_404(db.select(Student).filter_by(student_id=sid))
    df      = build_attendance_dataframe(student_id_filter=sid)
    return export_excel(df, student_filename(sid, 'xlsx'), sheet_name='Student Report')

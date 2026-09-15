"""
routes/students.py - Student Management Routes
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.helpers import login_required, validate_email, sanitize_student_id
from utils.database import db
from models.student import Student
from services.face_recognition_service import delete_embedding
from config import FACES_DIR

students_bp = Blueprint('students', __name__)


@students_bp.route('/students')
@login_required
def list_students():
    search = request.args.get('search', '').strip()
    dept   = request.args.get('dept', '').strip()

    query = Student.query
    if search:
        query = query.filter(
            Student.name.ilike(f'%{search}%') |
            Student.student_id.ilike(f'%{search}%')
        )
    if dept:
        query = query.filter_by(department=dept)

    students    = query.order_by(Student.name).all()
    departments = [r[0] for r in db.session.query(Student.department).distinct().all()]

    return render_template('students.html', students=students,
                           departments=departments, search=search, dept=dept)


@students_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        student_id = sanitize_student_id(request.form.get('student_id', '').strip())
        name       = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        year       = request.form.get('year', '').strip()
        email      = request.form.get('email', '').strip().lower()

        # ── Validation ────────────────────────────────────────────────────────
        errors = []
        if not student_id:
            errors.append('Student ID is required.')
        if not name:
            errors.append('Full name is required.')
        if not department:
            errors.append('Department is required.')
        if not year:
            errors.append('Year is required.')
        if not email or not validate_email(email):
            errors.append('A valid email address is required.')
        if Student.query.filter_by(student_id=student_id).first():
            errors.append(f'Student ID "{student_id}" already exists.')
        if Student.query.filter_by(email=email).first():
            errors.append(f'Email "{email}" is already registered.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('add_student.html', form=request.form)

        # ── Save ──────────────────────────────────────────────────────────────
        student = Student(
            student_id=student_id,
            name=name,
            department=department,
            year=year,
            email=email
        )
        db.session.add(student)
        db.session.commit()
        flash(f'Student "{name}" registered successfully. Now capture their face.', 'success')
        return redirect(url_for('capture.capture_page', student_id=student.student_id))

    return render_template('add_student.html', form={})


@students_bp.route('/students/edit/<int:sid>', methods=['GET', 'POST'])
@login_required
def edit_student(sid):
    student = db.get_or_404(Student, sid)

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        year       = request.form.get('year', '').strip()
        email      = request.form.get('email', '').strip().lower()

        errors = []
        if not name:       errors.append('Name is required.')
        if not department: errors.append('Department is required.')
        if not year:       errors.append('Year is required.')
        if not email or not validate_email(email):
            errors.append('Valid email required.')
        # Check email uniqueness (allow same student to keep their email)
        existing = Student.query.filter_by(email=email).first()
        if existing and existing.id != student.id:
            errors.append('Email already used by another student.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('add_student.html', form=request.form, student=student, edit=True)

        student.name       = name
        student.department = department
        student.year       = year
        student.email      = email
        db.session.commit()
        flash('Student updated successfully.', 'success')
        return redirect(url_for('students.list_students'))

    return render_template('add_student.html', form=student, student=student, edit=True)


@students_bp.route('/students/delete/<int:sid>', methods=['POST'])
@login_required
def delete_student(sid):
    student = db.get_or_404(Student, sid)
    name    = student.name
    sid_str = student.student_id

    # Delete face data from disk
    delete_embedding(sid_str)
    face_dir = os.path.join(FACES_DIR, sid_str)
    if os.path.isdir(face_dir):
        import shutil
        shutil.rmtree(face_dir, ignore_errors=True)

    # Delete student (cascades attendance records)
    db.session.delete(student)
    db.session.commit()
    flash(f'Student "{name}" and all related data have been deleted.', 'success')
    return redirect(url_for('students.list_students'))

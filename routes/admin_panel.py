"""
routes/admin_panel.py - Admin Panel Routes

Provides admin-only operations:
  - GET/POST /admin/change-password  ? change the admin login password
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.helpers import login_required
from utils.database import db
from models.admin import Admin

admin_panel_bp = Blueprint('admin_panel', __name__)


@admin_panel_bp.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow the logged-in admin to change their password."""
    admin = db.get_or_404(Admin, session['admin_id'])

    if request.method == 'POST':
        current_pw  = request.form.get('current_password', '')
        new_pw      = request.form.get('new_password', '')
        confirm_pw  = request.form.get('confirm_password', '')

        errors = []
        if not admin.check_password(current_pw):
            errors.append('Current password is incorrect.')
        if len(new_pw) < 6:
            errors.append('New password must be at least 6 characters.')
        if new_pw != confirm_pw:
            errors.append('New password and confirmation do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/change_password.html')

        admin.set_password(new_pw)
        db.session.commit()
        flash('Password changed successfully. Please log in again.', 'success')
        session.clear()
        return redirect(url_for('auth.login'))

    return render_template('admin/change_password.html')

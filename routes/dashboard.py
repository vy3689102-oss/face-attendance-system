"""
routes/dashboard.py - Dashboard Route
"""

from flask import Blueprint, render_template
from utils.helpers import login_required
from services.attendance_service import get_today_stats, get_weekly_trend, get_department_stats

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    stats       = get_today_stats()
    trend       = get_weekly_trend()
    dept_stats  = get_department_stats()

    return render_template(
        'dashboard.html',
        stats=stats,
        trend=trend,
        dept_stats=dept_stats
    )

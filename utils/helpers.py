"""
utils/helpers.py - Common Decorators and Utility Functions
"""

import os
import re
from functools import wraps
from datetime import datetime

from flask import session, redirect, url_for, flash


# ─── Auth Decorator ───────────────────────────────────────────────────────────

def login_required(f):
    """Redirect unauthenticated users to the login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ─── Input Validation ─────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    """Basic email format check."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return bool(re.match(pattern, email))


def sanitize_student_id(student_id: str) -> str:
    """Remove characters that could cause path-traversal issues."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '', student_id)


# ─── File Helpers ─────────────────────────────────────────────────────────────

def ensure_dirs(*paths):
    """Create directories if they do not already exist."""
    for path in paths:
        os.makedirs(path, exist_ok=True)


def safe_filename(name: str) -> str:
    """Convert a name to a filesystem-safe string."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)


# ─── Date/Time Helpers ────────────────────────────────────────────────────────

def today_str() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now().strftime('%Y-%m-%d')


def now_time_str() -> str:
    """Return current time as HH:MM:SS."""
    return datetime.now().strftime('%H:%M:%S')


def format_datetime(dt: datetime) -> str:
    """Human-readable date-time string."""
    if dt is None:
        return 'N/A'
    return dt.strftime('%d %b %Y, %I:%M %p')


def format_date(dt) -> str:
    """Human-readable date string."""
    if dt is None:
        return 'N/A'
    if isinstance(dt, str):
        return dt
    return dt.strftime('%d %b %Y')


# ─── Percentage Helper ────────────────────────────────────────────────────────

def calc_percentage(present: int, total: int) -> float:
    """Calculate attendance percentage safely."""
    if total == 0:
        return 0.0
    return round((present / total) * 100, 2)

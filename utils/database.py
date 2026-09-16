"""
utils/database.py - Database Initialization and Helpers
Sets up SQLAlchemy, creates tables, and seeds the default admin account.
"""

import os
from flask_sqlalchemy import SQLAlchemy

# Single shared SQLAlchemy instance (imported by all models)
db = SQLAlchemy()


def init_db(app):
    """
    Initialize the database:
    1. Ensure the database directory exists.
    2. Create all tables if they don't already exist.
    3. Seed the default admin account if none exists.
    """
    from config import DATABASE_DIR
    os.makedirs(DATABASE_DIR, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        from models.admin import Admin
        from models.student import Student
        from models.attendance import Attendance
        db.create_all()
        _seed_admin(app)


def _seed_admin(app):
    """Create the default admin account if the admin table is empty."""
    from models.admin import Admin
    from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

    if Admin.query.count() == 0:
        admin = Admin(username=DEFAULT_ADMIN_USERNAME)
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f"[DB] Default admin account created: username='{DEFAULT_ADMIN_USERNAME}'")

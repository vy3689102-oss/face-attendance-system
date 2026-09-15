"""
app.py - Main Flask Application

Registers all blueprints (auth, students, attendance, reports)
and starts the development server.

Routes overview:
  /               → dashboard
  /login          → admin login
  /logout         → admin logout
  /students       → student list
  /students/add   → add student
  /students/<id>  → edit / delete student
  /capture/<id>   → face capture page (AJAX stream)
  /attendance     → take attendance (live camera)
  /records        → attendance record browser
  /reports        → reports page
  /api/*          → JSON endpoints for webcam AJAX calls
  /stream/*       → MJPEG video streams
"""

import os
from flask import Flask, render_template

from config import (
    SECRET_KEY, SESSION_LIFETIME,
    SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS,
    FACES_DIR, EMBEDDINGS_DIR, EXPORT_DIR
)
from utils.database import db, init_db


def create_app():
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────────
    app.secret_key                        = SECRET_KEY
    app.permanent_session_lifetime        = SESSION_LIFETIME
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ── Ensure required directories exist ─────────────────────────────────────
    for d in [FACES_DIR, EMBEDDINGS_DIR, EXPORT_DIR]:
        os.makedirs(d, exist_ok=True)

    # ── Database ───────────────────────────────────────────────────────────────
    init_db(app)

    # ── Register Blueprints ────────────────────────────────────────────────────
    from routes.auth      import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.students  import students_bp
    from routes.capture   import capture_bp
    from routes.attendance import attendance_bp
    from routes.records   import records_bp
    from routes.reports   import reports_bp
    from routes.admin_panel import admin_panel_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(capture_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_panel_bp)

    # ── Error Handlers ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app


# ── Entry point ────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    print('=' * 60)
    print('  AI Smart Attendance System')
    print('  Running at: http://127.0.0.1:5000')
    print('  Default login — username: admin  |  password: admin123')
    print('=' * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)

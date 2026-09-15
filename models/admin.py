"""
models/admin.py - Admin User Model
Stores admin credentials with bcrypt-style password hashing via Werkzeug.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database import db


class Admin(db.Model):
    __tablename__ = 'admin'

    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Password helpers ──────────────────────────────────────────────────────

    def set_password(self, plain_password: str):
        """Hash and store the password. Never store plain text."""
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        """Verify a plain password against the stored hash."""
        return check_password_hash(self.password_hash, plain_password)

    def __repr__(self):
        return f'<Admin {self.username}>'

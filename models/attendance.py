"""
models/attendance.py - Attendance Record Model
Each row represents one attendance event (student present on a date).
Database-level uniqueness constraint prevents duplicate same-day attendance.
"""

from datetime import datetime
from utils.database import db


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(
        db.Integer,
        db.ForeignKey('student.id', ondelete='CASCADE'),
        nullable=False
    )
    date        = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    time        = db.Column(db.String(8),  nullable=False)   # HH:MM:SS
    status      = db.Column(db.String(20), nullable=False, default='Present')
    confidence  = db.Column(db.Float, default=0.0)           # Recognition confidence %
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Database-level constraint: one student can only be marked once per day ─
    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='uq_student_date'),
    )

    def __repr__(self):
        return f'<Attendance student_id={self.student_id} date={self.date} status={self.status}>'

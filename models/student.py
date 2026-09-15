"""
models/student.py - Student Model
Stores student registration details and tracks face registration status.
Face embeddings are stored as .npy files referenced by student_id, not as blobs.
"""

from datetime import datetime
from utils.database import db


class Student(db.Model):
    __tablename__ = 'student'

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name        = db.Column(db.String(120), nullable=False)
    department  = db.Column(db.String(100), nullable=False)
    year        = db.Column(db.String(20), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    face_registered = db.Column(db.Boolean, default=False, nullable=False)
    sample_count    = db.Column(db.Integer, default=0)   # How many face samples captured
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: one student → many attendance records
    attendance_records = db.relationship(
        'Attendance',
        backref='student',
        lazy='dynamic',
        cascade='all, delete-orphan'   # Delete attendance when student deleted
    )

    # ── Convenience Properties ────────────────────────────────────────────────

    @property
    def face_status(self) -> str:
        return 'Registered' if self.face_registered else 'Not Registered'

    def total_attendance(self) -> int:
        return self.attendance_records.count()

    def __repr__(self):
        return f'<Student {self.student_id} - {self.name}>'

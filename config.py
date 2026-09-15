"""
config.py - Application Configuration
All important constants in one place for easy modification.
"""

import os
from datetime import timedelta

# ─── Base Directories ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Flask Secret Key ─────────────────────────────────────────────────────────
# In production, set this via environment variable SECRET_KEY
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-before-deployment-2026')
SESSION_LIFETIME = timedelta(hours=8)

# ─── Database ─────────────────────────────────────────────────────────────────
if os.environ.get('VERCEL'):
    DATABASE_DIR = '/tmp/database'
else:
    DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'attendance.db')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ─── Data Storage ─────────────────────────────────────────────────────────────
if os.environ.get('VERCEL'):
    DATA_DIR      = '/tmp/data'
else:
    DATA_DIR      = os.path.join(BASE_DIR, 'data')
FACES_DIR     = os.path.join(DATA_DIR, 'faces')
EMBEDDINGS_DIR = os.path.join(DATA_DIR, 'embeddings')

# ─── Face Capture Settings ───────────────────────────────────────────────────
MIN_FACE_SAMPLES = 10          # Minimum samples required to register
MAX_FACE_SAMPLES = 20          # Maximum samples to capture
FACE_SAMPLE_INTERVAL = 0.5    # Seconds between captures (avoid duplicates)

# ─── Face Detection ───────────────────────────────────────────────────────────
# Haar cascade scale factor and minimum neighbours
HAAR_SCALE_FACTOR   = 1.1
HAAR_MIN_NEIGHBORS  = 5
HAAR_MIN_SIZE       = (80, 80)   # Minimum face size in pixels

# ─── Face Recognition ─────────────────────────────────────────────────────────
# Cosine similarity threshold (0.0 = identical, 1.0 = completely different)
# Lower value = stricter matching
FACE_MATCH_THRESHOLD = 0.45   # Faces with distance <= this are recognized
RECOGNITION_MODEL    = 'opencv'  # 'opencv' uses LBPH; future: 'deepface'

# ─── Liveness Detection ───────────────────────────────────────────────────────
# Eye Aspect Ratio (EAR) below this value → eye is closed (blink detected)
EAR_THRESHOLD        = 0.25
# Consecutive frames below EAR_THRESHOLD to count as a blink
EAR_CONSEC_FRAMES    = 2
# Number of blinks required to pass liveness check
REQUIRED_BLINKS      = 2
# Seconds to complete liveness check before timeout
LIVENESS_TIMEOUT     = 15

# ─── Default Admin ────────────────────────────────────────────────────────────
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'   # Hashed on first run; change in production

# ─── Upload / Export ──────────────────────────────────────────────────────────
if os.environ.get('VERCEL'):
    EXPORT_DIR = '/tmp/exports'
else:
    EXPORT_DIR = os.path.join(BASE_DIR, 'static', 'exports')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# ─── Attendance ───────────────────────────────────────────────────────────────
ATTENDANCE_STATUS_PRESENT = 'Present'
ATTENDANCE_STATUS_ABSENT  = 'Absent'

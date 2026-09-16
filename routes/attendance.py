"""
routes/attendance.py - Live Attendance Routes

Flow (browser-side):
  1. User opens /attendance page.
  2. JS clicks Start → POST /attendance/start (creates a liveness session).
  3. JS sends frames to POST /attendance/frame (base64 JPEG every ~500ms).
  4. Server runs: face_detection → liveness → face_recognition → mark_attendance.
  5. Returns JSON with recognition result and attendance status.
  6. On liveness timeout or unknown face, JS calls POST /attendance/reset to retry.

Liveness state is stored server-side in a dict keyed by admin session ID.
Memory is cleaned up automatically (old sessions older than 10 minutes are pruned).
"""

import base64
import time
import numpy as np
import cv2

from flask import Blueprint, render_template, request, jsonify, session

from utils.helpers import login_required
from models.student import Student
from services.face_detection import detect_faces, crop_face
from services.face_recognition_service import recognize_face
from services.liveness import LivenessChecker
from services.attendance_service import mark_attendance, get_today_stats

attendance_bp = Blueprint('attendance', __name__)

# Per-session liveness checker store:
#   { admin_id: {'checker': LivenessChecker, 'created_at': float} }
_liveness_checkers: dict = {}

# How long (seconds) before an idle liveness session is garbage-collected
_SESSION_TTL = 600   # 10 minutes


# ─── Helper: get or create liveness checker ───────────────────────────────────

def _get_checker(admin_id) -> LivenessChecker:
    """Return the current liveness checker for this admin, or create a new one."""
    entry = _liveness_checkers.get(admin_id)
    if entry is None:
        entry = {'checker': LivenessChecker(), 'created_at': time.time()}
        _liveness_checkers[admin_id] = entry
    return entry['checker']


def _reset_checker(admin_id):
    """Replace the liveness checker with a fresh one."""
    _liveness_checkers[admin_id] = {
        'checker':    LivenessChecker(),
        'created_at': time.time()
    }


def _prune_old_sessions():
    """Remove liveness sessions that haven't been used in _SESSION_TTL seconds."""
    cutoff = time.time() - _SESSION_TTL
    stale  = [k for k, v in _liveness_checkers.items() if v['created_at'] < cutoff]
    for k in stale:
        del _liveness_checkers[k]


# ─── Routes ───────────────────────────────────────────────────────────────────

@attendance_bp.route('/attendance')
@login_required
def attendance_page():
    stats = get_today_stats()
    return render_template('attendance.html', stats=stats)


@attendance_bp.route('/attendance/start', methods=['POST'])
@login_required
def start_session():
    """Reset the liveness checker for a new attendance attempt."""
    admin_id = session.get('admin_id', 'default')
    _prune_old_sessions()
    _reset_checker(admin_id)
    return jsonify({'status': 'started', 'message': 'Session started. Show your face and blink.'})


@attendance_bp.route('/attendance/reset', methods=['POST'])
@login_required
def reset_session():
    """
    Reset the liveness checker without re-initialising everything.
    Called by the frontend after a timeout, unknown face, or manual retry.
    """
    admin_id = session.get('admin_id', 'default')
    _reset_checker(admin_id)
    return jsonify({'status': 'reset', 'message': 'Session reset. Show your face and blink again.'})


@attendance_bp.route('/attendance/frame', methods=['POST'])
@login_required
def process_frame():
    """
    Receive one webcam frame and run the full pipeline:
      detect → liveness → recognize → mark attendance

    States returned in JSON:
      no_face         → no face in frame
      multiple        → multiple faces detected
      liveness_check  → waiting for blink
      liveness_failed → timeout reached
      recognizing     → liveness passed, recognising
      recognized      → student identified, attendance marked
      duplicate       → already marked today
      unknown         → face not recognised
      error           → processing error
    """
    admin_id = session.get('admin_id', 'default')

    # ── Decode frame ──────────────────────────────────────────────────────────
    data = request.get_json(silent=True)
    if not data or 'frame' not in data:
        return jsonify({'state': 'error', 'message': 'No frame received.'})

    try:
        img_bytes = base64.b64decode(data['frame'].split(',')[-1])
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'state': 'error', 'message': f'Frame decode error: {str(e)}'})

    if frame is None:
        return jsonify({'state': 'error', 'message': 'Invalid image data.'})

    # ── Step 1: Detect face ───────────────────────────────────────────────────
    faces, status, _ = detect_faces(frame)

    if status == 'none':
        return jsonify({'state': 'no_face',
                        'message': 'No face detected. Please look at the camera.'})
    if status == 'multiple':
        return jsonify({'state': 'multiple',
                        'message': 'Multiple faces detected. Only one person in frame.'})

    face_bbox = faces[0]

    # ── Step 2: Liveness check ────────────────────────────────────────────────
    checker        = _get_checker(admin_id)
    liveness_result = checker.process_frame(frame, face_bbox)

    # Handle timeout
    if liveness_result['timed_out']:
        _reset_checker(admin_id)   # Auto-reset for next attempt
        return jsonify({
            'state':   'liveness_failed',
            'message': liveness_result['message']
        })

    if not liveness_result['passed']:
        return jsonify({
            'state':       'liveness_check',
            'message':     liveness_result['message'],
            'blink_count': liveness_result['blink_count'],
            'required':    liveness_result['required'],
            'remaining':   liveness_result['remaining']
        })

    # ── Step 3: Face recognition ──────────────────────────────────────────────
    face_crop = crop_face(frame, face_bbox)
    if face_crop is None:
        return jsonify({'state': 'error', 'message': 'Could not crop face region.'})

    registered_students = Student.query.filter_by(face_registered=True).all()

    if not registered_students:
        return jsonify({
            'state':   'error',
            'message': 'No registered students in system. Please register students first.'
        })

    result = recognize_face(face_crop, registered_students)

    if not result['recognized']:
        # Reset liveness for next attempt
        _reset_checker(admin_id)
        return jsonify({
            'state':      'unknown',
            'message':    '⚠ Unknown Face. This person is not registered. Attendance was not marked.',
            'confidence': result['confidence']
        })

    # ── Step 4: Mark attendance ───────────────────────────────────────────────
    student    = result['student']
    att_result = mark_attendance(student, confidence=result['confidence'])

    # Reset liveness for the next person
    _reset_checker(admin_id)

    if att_result['duplicate']:
        return jsonify({
            'state':      'duplicate',
            'message':    att_result['message'],
            'student':    _student_dict(student, result),
            'confidence': result['confidence']
        })

    return jsonify({
        'state':      'recognized',
        'message':    att_result['message'],
        'student':    _student_dict(student, result),
        'confidence': result['confidence'],
        'time':       att_result['record'].time if att_result['record'] else '',
        'date':       att_result['record'].date if att_result['record'] else ''
    })


@attendance_bp.route('/attendance/stats')
@login_required
def live_stats():
    """
    Return today's attendance statistics as JSON.
    Called by the frontend to refresh the stat counters without a full page reload.
    """
    stats = get_today_stats()
    return jsonify({
        'total':      stats['total'],
        'present':    stats['present'],
        'absent':     stats['absent'],
        'percentage': stats['percentage'],
        'date':       stats['date']
    })


# ─── Private ─────────────────────────────────────────────────────────────────

def _student_dict(student: Student, result: dict) -> dict:
    return {
        'id':         student.student_id,
        'name':       student.name,
        'department': student.department,
        'year':       student.year,
        'confidence': result['confidence']
    }

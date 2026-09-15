"""
routes/capture.py - Face Capture Routes (Registration)

Flow:
  1. GET  /capture/<student_id>  → show capture page (HTML + webcam UI)
  2. POST /capture/frame/<sid>   → receive a base64 frame, detect face,
                                   save sample, return JSON progress
  3. POST /capture/finish/<sid>  → compute average embedding & save, mark student
"""

import os
import base64
import json
import numpy as np
import cv2

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

from utils.helpers import login_required
from models.student import Student
from utils.database import db
from services.face_detection import detect_faces, crop_face, check_image_quality
from services.face_recognition_service import (
    compute_embedding, average_embeddings, save_embedding
)
from config import FACES_DIR, MIN_FACE_SAMPLES, MAX_FACE_SAMPLES

capture_bp = Blueprint('capture', __name__)

# In-memory store: student_id → list of embeddings collected so far
# (This is fine for a single-process dev server)
_capture_sessions: dict[str, list] = {}


@capture_bp.route('/capture/<student_id>')
@login_required
def capture_page(student_id):
    student = db.first_or_404(db.select(Student).filter_by(student_id=student_id))
    _capture_sessions[student_id] = []   # Reset session
    return render_template('capture_face.html', student=student,
                           min_samples=MIN_FACE_SAMPLES,
                           max_samples=MAX_FACE_SAMPLES)


@capture_bp.route('/capture/frame/<student_id>', methods=['POST'])
@login_required
def process_frame(student_id):
    """
    Receive one webcam frame (base64 JPEG), detect the face,
    check quality, compute embedding, and store it.
    Returns JSON with progress info.
    """
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    data = request.get_json()
    if not data or 'frame' not in data:
        return jsonify({'error': 'No frame data received'}), 400

    # ── Decode base64 frame ───────────────────────────────────────────────────
    try:
        img_data = base64.b64decode(data['frame'].split(',')[-1])
        np_arr   = np.frombuffer(img_data, np.uint8)
        frame    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'error': f'Frame decode error: {str(e)}'}), 400

    if frame is None:
        return jsonify({'error': 'Could not decode image'}), 400

    # ── Detect face ───────────────────────────────────────────────────────────
    faces, status, _ = detect_faces(frame)

    if status == 'none':
        return jsonify({'status': 'no_face', 'message': 'No face detected. Position your face in the frame.'})
    if status == 'multiple':
        return jsonify({'status': 'multiple', 'message': 'Multiple faces detected. Only one person should be in frame.'})

    # ── Crop and quality check ────────────────────────────────────────────────
    face_crop = crop_face(frame, faces[0])
    if face_crop is None:
        return jsonify({'status': 'error', 'message': 'Could not crop face region.'})

    if not check_image_quality(face_crop):
        return jsonify({'status': 'blurry', 'message': 'Image too blurry. Hold camera steady.'})

    # ── Compute and store embedding ───────────────────────────────────────────
    embedding = compute_embedding(face_crop)
    if embedding is None:
        return jsonify({'status': 'error', 'message': 'Could not compute face embedding.'})

    if student_id not in _capture_sessions:
        _capture_sessions[student_id] = []

    _capture_sessions[student_id].append(embedding)
    count = len(_capture_sessions[student_id])

    # Also save the raw face image for reference
    face_dir = os.path.join(FACES_DIR, student_id)
    os.makedirs(face_dir, exist_ok=True)
    img_path = os.path.join(face_dir, f'sample_{count:03d}.jpg')
    cv2.imwrite(img_path, face_crop)

    ready = count >= MIN_FACE_SAMPLES

    return jsonify({
        'status':    'captured',
        'message':   f'Sample {count}/{MAX_FACE_SAMPLES} captured.',
        'count':     count,
        'min':       MIN_FACE_SAMPLES,
        'max':       MAX_FACE_SAMPLES,
        'ready':     ready,
        'progress':  int((count / MAX_FACE_SAMPLES) * 100)
    })


@capture_bp.route('/capture/finish/<student_id>', methods=['POST'])
@login_required
def finish_capture(student_id):
    """
    Average all collected embeddings into one representative embedding,
    save it to disk, and mark the student as face-registered.
    """
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    embeddings = _capture_sessions.get(student_id, [])

    if len(embeddings) < MIN_FACE_SAMPLES:
        return jsonify({
            'error': f'Not enough samples. Need {MIN_FACE_SAMPLES}, have {len(embeddings)}.'
        }), 400

    # Average all embeddings → one compact representation
    avg_embedding = average_embeddings(embeddings)
    save_embedding(student_id, avg_embedding)

    # Update database
    student.face_registered = True
    student.sample_count    = len(embeddings)
    db.session.commit()

    # Clear session data
    _capture_sessions.pop(student_id, None)

    return jsonify({
        'status':  'success',
        'message': f'Face registered successfully with {len(embeddings)} samples!',
        'redirect': url_for('students.list_students')
    })


@capture_bp.route('/capture/reset/<student_id>', methods=['POST'])
@login_required
def reset_capture(student_id):
    """Reset capture session for a student (start over)."""
    _capture_sessions[student_id] = []
    return jsonify({'status': 'reset', 'message': 'Capture session reset.'})

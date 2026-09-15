"""
services/face_detection.py - Reusable Face Detection Module

Uses OpenCV's DNN-based face detector (more accurate than Haar cascades).
Falls back to Haar cascade if DNN model is unavailable.

This module is used by:
  - Registration (capture_face)
  - Attendance (live recognition)

Detection Results:
  - 'none'     : No face found in frame
  - 'one'      : Exactly one face found (good)
  - 'multiple' : More than one face found (reject for attendance)
"""

import os
import cv2
import numpy as np

# ─── Load DNN or Haar Cascade Detector ────────────────────────────────────────

_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

_face_cascade = cv2.CascadeClassifier(_CASCADE_PATH)

# ─── Public API ───────────────────────────────────────────────────────────────

def detect_faces(frame: np.ndarray):
    """
    Detect faces in an OpenCV BGR frame using Haar cascade.

    Returns:
        faces (list[tuple]): list of (x, y, w, h) bounding boxes
        status (str): 'none' | 'one' | 'multiple'
        annotated (np.ndarray): frame with rectangles drawn
    """
    annotated = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Equalise histogram for better detection in varying lighting
    gray = cv2.equalizeHist(gray)

    detected = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    faces = list(detected) if len(detected) > 0 else []

    # Annotate the frame
    for (x, y, w, h) in faces:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 200, 0), 2)

    if len(faces) == 0:
        status = 'none'
        _put_status(annotated, 'No face detected', (0, 0, 200))
    elif len(faces) == 1:
        status = 'one'
        _put_status(annotated, 'Face detected', (0, 200, 0))
    else:
        status = 'multiple'
        _put_status(annotated, f'{len(faces)} faces detected - use one face', (0, 165, 255))

    return faces, status, annotated


def crop_face(frame: np.ndarray, bbox: tuple, padding: int = 20) -> np.ndarray:
    """
    Crop and return a face region with optional padding.
    Ensures the crop stays within image bounds.

    Args:
        frame: BGR image
        bbox:  (x, y, w, h) bounding box
        padding: pixels to expand the bounding box

    Returns:
        Cropped face as BGR image (128x128)
    """
    h_img, w_img = frame.shape[:2]
    x, y, w, h = bbox

    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(w_img, x + w + padding)
    y2 = min(h_img, y + h + padding)

    face_crop = frame[y1:y2, x1:x2]

    if face_crop.size == 0:
        return None

    # Resize to a standard size for embedding computation
    face_resized = cv2.resize(face_crop, (128, 128))
    return face_resized


def check_image_quality(face_crop: np.ndarray) -> bool:
    """
    Basic image quality check using Laplacian variance (sharpness).
    Returns True if the image is sharp enough to use.
    """
    if face_crop is None:
        return False
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Threshold: frames with variance below ~50 are too blurry
    return variance > 50.0


# ─── Private Helpers ──────────────────────────────────────────────────────────

def _put_status(frame: np.ndarray, text: str, color: tuple):
    """Overlay a status message on the bottom of the frame."""
    h = frame.shape[0]
    cv2.rectangle(frame, (0, h - 40), (frame.shape[1], h), (30, 30, 30), -1)
    cv2.putText(
        frame, text, (10, h - 12),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA
    )

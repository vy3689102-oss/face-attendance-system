"""
services/liveness.py - Basic Liveness Detection

PURPOSE:
  Prevent simple spoofing attacks where someone shows a static photograph
  to the camera instead of their real face.

METHOD:
  Eye Aspect Ratio (EAR) Blink Detection
  - Compute the ratio of eye height to eye width using facial landmarks.
  - When a person blinks, the EAR drops sharply then recovers.
  - A photograph cannot blink → liveness fails.

IMPORTANT DISCLAIMER:
  This is BASIC liveness detection suitable for a college project.
  It is NOT certified anti-spoofing. Determined attackers with video
  loops or 3D masks may defeat it. Do not use in high-security systems
  without additional certified anti-spoofing measures.

EAR Formula (Soukupova & Cech, 2016):
  EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
  Where p1..p6 are the six eye landmark points.
  EAR ≈ 0.3 when open, drops to ~0.0 when closed.
"""

import time
import cv2
import numpy as np
from config import EAR_THRESHOLD, EAR_CONSEC_FRAMES, REQUIRED_BLINKS, LIVENESS_TIMEOUT


# ─── Facial Landmark Detection ────────────────────────────────────────────────
# We use dlib's 68-point predictor if available,
# otherwise fall back to a simplified eye-region analysis via Haar cascade.

try:
    import dlib
    _DLIB_AVAILABLE = True
    _detector  = dlib.get_frontal_face_detector()
    import os
    _PREDICTOR_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'shape_predictor_68_face_landmarks.dat'
    )
    if os.path.exists(_PREDICTOR_PATH):
        _predictor = dlib.shape_predictor(_PREDICTOR_PATH)
        _PREDICTOR_AVAILABLE = True
    else:
        _PREDICTOR_AVAILABLE = False
        _DLIB_AVAILABLE = False
except ImportError:
    _DLIB_AVAILABLE = False
    _PREDICTOR_AVAILABLE = False


# ─── LivenessChecker Class ────────────────────────────────────────────────────

CHALLENGE_TYPES = ['blink', 'turn_left', 'turn_right', 'look_up']

class LivenessChecker:
    def __init__(self):
        self.passed        = False
        self.timed_out     = False
        self._start_time   = time.time()
        
        # State for current challenge
        self.consec_below  = 0
        self.current_blink_count = 0

        # Generate 2 random challenges, ensuring 'blink' is often first but not always
        import random
        if _PREDICTOR_AVAILABLE:
            self.challenges = random.sample(CHALLENGE_TYPES, 2)
            # Make sure blink is one of them if possible for better UX
            if 'blink' not in self.challenges:
                self.challenges[0] = 'blink'
        else:
            self.challenges = ['blink', 'blink'] # Fallback if no dlib
            
        self.current_challenge_idx = 0
        self.message = ""
        self._update_message()

    def reset(self):
        self.__init__()

    @property
    def elapsed(self) -> float:
        return time.time() - self._start_time

    @property
    def remaining(self) -> float:
        return max(0.0, LIVENESS_TIMEOUT - self.elapsed)
        
    def _update_message(self):
        if self.current_challenge_idx >= len(self.challenges):
            self.message = 'Liveness Verified ✓ — Recognising face…'
            return
            
        c_type = self.challenges[self.current_challenge_idx]
        if c_type == 'blink':
            self.message = f'Challenge {self.current_challenge_idx+1}: Please blink twice'
        elif c_type == 'turn_left':
            self.message = f'Challenge {self.current_challenge_idx+1}: Turn your head LEFT'
        elif c_type == 'turn_right':
            self.message = f'Challenge {self.current_challenge_idx+1}: Turn your head RIGHT'
        elif c_type == 'look_up':
            self.message = f'Challenge {self.current_challenge_idx+1}: Look UP slightly'

    def process_frame(self, frame: np.ndarray, face_bbox: tuple = None) -> dict:
        annotated = frame.copy()

        if self.passed:
            _draw_overlay(annotated, 'Liveness Verified ✓', (0, 200, 0))
            return self._result(annotated, 1.0)

        if self.elapsed > LIVENESS_TIMEOUT:
            self.timed_out = True
            self.message   = f'Timeout! Try again in {LIVENESS_TIMEOUT}s.'
            _draw_overlay(annotated, self.message, (0, 0, 200))
            return self._result(annotated, 0.0)
            
        # Get Landmarks
        pts = None
        if _PREDICTOR_AVAILABLE:
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = _detector(gray, 0)
            if len(rects) > 0:
                shape = _predictor(gray, rects[0])
                pts   = [(shape.part(i).x, shape.part(i).y) for i in range(68)]

        if pts is None and _PREDICTOR_AVAILABLE:
            self.message = 'Position your face clearly in the camera'
            _draw_overlay(annotated, self.message, (0, 165, 255))
            return self._result(annotated, 0.0)

        c_type = self.challenges[self.current_challenge_idx]
        challenge_passed = False
        ear = 0.0
        
        if c_type == 'blink':
            if pts:
                left_ear  = _eye_aspect_ratio(pts[36:42])
                right_ear = _eye_aspect_ratio(pts[42:48])
                ear = (left_ear + right_ear) / 2.0
            else:
                ear = _ear_opencv_fallback(frame, face_bbox) or 0.3
                
            if ear < EAR_THRESHOLD:
                self.consec_below += 1
            else:
                if self.consec_below >= EAR_CONSEC_FRAMES:
                    self.current_blink_count += 1
                self.consec_below = 0
                
            if self.current_blink_count >= REQUIRED_BLINKS:
                challenge_passed = True
                
        elif c_type == 'turn_left':
            # Turn left from user's perspective means looking towards right side of the screen
            if pts:
                nose_x = pts[30][0]
                left_x = pts[0][0]
                right_x = pts[16][0]
                dist_left = nose_x - left_x
                dist_right = right_x - nose_x
                if dist_left > 1.8 * dist_right:
                    challenge_passed = True
                    
        elif c_type == 'turn_right':
            if pts:
                nose_x = pts[30][0]
                left_x = pts[0][0]
                right_x = pts[16][0]
                dist_left = nose_x - left_x
                dist_right = right_x - nose_x
                if dist_right > 1.8 * dist_left:
                    challenge_passed = True
                    
        elif c_type == 'look_up':
            if pts:
                nose_y = pts[30][1]
                eye_y = (pts[36][1] + pts[45][1]) / 2.0
                chin_y = pts[8][1]
                # Ratio of nose-to-eye vs chin-to-nose
                dist_top = nose_y - eye_y
                dist_bottom = chin_y - nose_y
                if dist_bottom > 2.0 * dist_top:
                    challenge_passed = True

        if challenge_passed:
            self.current_challenge_idx += 1
            self.current_blink_count = 0
            self.consec_below = 0
            if self.current_challenge_idx >= len(self.challenges):
                self.passed = True
            self._update_message()

        color = (0, 200, 0) if self.passed else (0, 200, 255)
        
        secs_left = int(self.remaining)
        display_msg = self.message + f" [{secs_left}s left]"
        _draw_overlay(annotated, display_msg, color)

        return self._result(annotated, ear)

    def _result(self, annotated, ear):
        # We dummy out blink_count for the frontend since it might not be a blink challenge
        return {
            'passed':      self.passed,
            'timed_out':   self.timed_out,
            'blink_count': self.current_challenge_idx, # Use idx as progress
            'required':    len(self.challenges),
            'remaining':   round(self.remaining, 1),
            'ear':         ear if ear is not None else 0.0,
            'message':     self.message,
            'annotated':   annotated
        }

    def _compute_ear(self, frame: np.ndarray, face_bbox: tuple = None) -> float | None:
        """Dummy method since logic is now inside process_frame"""
        pass


# ─── dlib-based EAR ───────────────────────────────────────────────────────────

def _ear_dlib(frame: np.ndarray) -> float | None:
    """Compute EAR using dlib 68-point facial landmarks."""
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = _detector(gray, 0)
    if len(rects) == 0:
        return None

    shape = _predictor(gray, rects[0])
    pts   = [(shape.part(i).x, shape.part(i).y) for i in range(68)]

    # Left eye:  landmarks 36-41
    # Right eye: landmarks 42-47
    left_ear  = _eye_aspect_ratio(pts[36:42])
    right_ear = _eye_aspect_ratio(pts[42:48])
    return (left_ear + right_ear) / 2.0


def _eye_aspect_ratio(eye_pts: list) -> float:
    """
    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    eye_pts: list of 6 (x, y) points
    """
    p1, p2, p3, p4, p5, p6 = [np.array(p) for p in eye_pts]
    A = np.linalg.norm(p2 - p6)
    B = np.linalg.norm(p3 - p5)
    C = np.linalg.norm(p1 - p4)
    if C == 0:
        return 0.0
    return (A + B) / (2.0 * C)


# ─── OpenCV Fallback EAR ──────────────────────────────────────────────────────

_eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)

def _ear_opencv_fallback(frame: np.ndarray, face_bbox: tuple = None) -> float | None:
    """
    Fallback when dlib/predictor is unavailable.
    Detects eyes using Haar cascade and estimates EAR from bounding box ratio.
    Less accurate than dlib but works without installing dlib.

    Logic:
    - If 0 eyes detected → eye is fully closed → return low EAR (blink signal)
    - If 1 eye detected → half-blink or occlusion → marginal EAR
    - If 2+ eyes detected → eyes open → compute height/width ratio as proxy EAR
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if face_bbox is not None:
        x, y, w, h = face_bbox
        # Search for eyes only in the upper half of the face (faster + more accurate)
        roi_gray = gray[y:y + h // 2, x:x + w]
    else:
        roi_gray = gray

    eyes = _eye_cascade.detectMultiScale(roi_gray, 1.1, 4, minSize=(20, 20))

    if len(eyes) == 0:
        return 0.10   # Both eyes closed → definite blink
    if len(eyes) == 1:
        return 0.22   # One eye — could be partial blink

    # Two eyes detected → estimate EAR from bounding box aspect ratio
    ears = []
    for (ex, ey, ew, eh) in eyes[:2]:
        ear_approx = eh / max(ew, 1)   # height/width ratio ≈ EAR proxy
        ears.append(ear_approx)

    return float(np.mean(ears))


# ─── Annotation Helper ────────────────────────────────────────────────────────

def _draw_overlay(frame: np.ndarray, text: str, color: tuple):
    """Draw a semi-transparent overlay bar at the bottom of the frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 50), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, text, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

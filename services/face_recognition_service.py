"""
services/face_recognition_service.py - Face Embedding & Recognition

How it works:
1. REGISTRATION:
   - Capture 10-20 face crops for a student.
   - Compute a 128-dimensional LBP histogram for each crop (the "embedding").
   - Average all embeddings into one representative embedding.
   - Save it as data/embeddings/<student_id>.npy

2. RECOGNITION:
   - Capture a live face crop.
   - Compute its embedding.
   - Compare against every stored embedding using cosine distance.
   - If best distance <= FACE_MATCH_THRESHOLD → recognized.

Why LBP histograms?
   - Works fully offline, no GPU needed.
   - Runs on any student laptop.
   - Fast enough for real-time webcam (vectorized NumPy implementation).
   - Well-understood for viva explanations.

Face Embeddings Explained (for viva):
   A face embedding is a compact numerical representation (vector) of a face.
   Similar faces produce similar vectors. We measure similarity using cosine distance.
   Cosine distance 0 = identical, 1 = completely different.

LBP (Local Binary Pattern) Explained:
   For each pixel, compare it with its N circular neighbours.
   If neighbour >= center pixel → 1, else → 0.
   The resulting binary string is the LBP code for that pixel.
   A histogram of all LBP codes describes the texture of a region.
   We compute this on an 8×8 grid of sub-regions for spatial accuracy.
"""

import os
import cv2
import numpy as np
from config import EMBEDDINGS_DIR, FACE_MATCH_THRESHOLD


# ─── Embedding Computation ────────────────────────────────────────────────────

def compute_embedding(face_bgr: np.ndarray) -> np.ndarray:
    """
    Compute a Local Binary Pattern (LBP) histogram embedding from a face image.

    Steps:
      1. Convert to grayscale.
      2. Resize to 64x64 for consistent embedding size.
      3. Compute vectorised LBP on 8x8 sub-regions (gives spatial info).
      4. Concatenate all region histograms → 1-D embedding vector.
      5. L2-normalise the vector so cosine distance = 1 - dot(a, b).

    Args:
        face_bgr: BGR face crop (any size; will be resized internally)

    Returns:
        1-D numpy float32 array (the embedding / feature vector), or None on error.
    """
    if face_bgr is None or face_bgr.size == 0:
        return None

    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (64, 64))

    # Compute LBP on grid of sub-regions for spatial information
    hist = _lbp_histogram_grid_fast(gray, grid_x=8, grid_y=8, num_points=8, radius=1)

    # L2-normalise so cosine distance = 1 - dot product
    norm = np.linalg.norm(hist)
    if norm == 0:
        return hist.astype(np.float32)
    return (hist / norm).astype(np.float32)


# ─── Save / Load Embeddings ───────────────────────────────────────────────────

def save_embedding(student_id: str, embedding: np.ndarray):
    """Save a student's embedding to disk as a .npy file."""
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
    path = _embedding_path(student_id)
    np.save(path, embedding)


def load_embedding(student_id: str) -> np.ndarray | None:
    """Load a student's embedding from disk. Returns None if not found."""
    path = _embedding_path(student_id)
    if not os.path.exists(path):
        return None
    return np.load(path)


def delete_embedding(student_id: str):
    """Remove a student's embedding file (called when student is deleted)."""
    path = _embedding_path(student_id)
    if os.path.exists(path):
        os.remove(path)


# ─── Multi-Sample Averaging ───────────────────────────────────────────────────

def average_embeddings(embeddings: list[np.ndarray]) -> np.ndarray:
    """
    Average multiple embeddings into one representative embedding.
    This improves robustness against lighting/angle variation.
    Re-normalises after averaging to keep it unit-length.
    """
    stacked = np.stack(embeddings, axis=0)
    avg = np.mean(stacked, axis=0)
    norm = np.linalg.norm(avg)
    if norm == 0:
        return avg.astype(np.float32)
    return (avg / norm).astype(np.float32)


# ─── Recognition ─────────────────────────────────────────────────────────────

def recognize_face(face_bgr: np.ndarray, registered_students: list) -> dict:
    """
    Compare a live face crop against all registered student embeddings.

    Args:
        face_bgr:            BGR face crop from webcam
        registered_students: list of Student ORM objects (face_registered=True)

    Returns:
        dict with keys:
          - 'recognized' (bool)
          - 'student'    (Student object or None)
          - 'confidence' (float 0-100, higher = more confident match)
          - 'distance'   (float, raw cosine distance; lower = better match)
    """
    query_embedding = compute_embedding(face_bgr)
    if query_embedding is None:
        return {'recognized': False, 'student': None, 'confidence': 0.0, 'distance': 1.0}

    best_distance = float('inf')
    best_student  = None

    for student in registered_students:
        stored_emb = load_embedding(student.student_id)
        if stored_emb is None:
            continue  # Student registered in DB but face not captured yet

        distance = cosine_distance(query_embedding, stored_emb)

        if distance < best_distance:
            best_distance = distance
            best_student  = student

    recognized = (best_distance <= FACE_MATCH_THRESHOLD) and (best_student is not None)
    confidence = max(0.0, (1.0 - best_distance) * 100.0) if best_student else 0.0

    return {
        'recognized': recognized,
        'student':    best_student if recognized else None,
        'confidence': round(confidence, 2),
        'distance':   round(float(best_distance), 4)
    }


# ─── Math Helpers ─────────────────────────────────────────────────────────────

def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine distance between two L2-normalised vectors.
    Since both are normalised: distance = 1 - dot(a, b)
    Range: 0 (identical) to 2 (opposite); typical range 0-1 for face embeddings.
    """
    return float(1.0 - np.dot(a, b))


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _embedding_path(student_id: str) -> str:
    safe_id = student_id.replace('/', '_').replace('\\', '_')
    return os.path.join(EMBEDDINGS_DIR, f'{safe_id}.npy')


# ─── Fast Vectorised LBP (replaces slow pixel-by-pixel loop) ─────────────────

def _lbp_fast(gray: np.ndarray, num_points: int = 8, radius: int = 1) -> np.ndarray:
    """
    Compute Local Binary Pattern map for a grayscale image using fully
    vectorised NumPy operations.

    Why this is fast:
    - Old approach: nested Python for-loops → O(H * W * P) Python iterations.
    - New approach: process entire image as arrays → ~100x faster.
    - Each of the P neighbours is computed in one array operation, then OR-ed
      into the LBP map via bit-shift.

    Args:
        gray:       2-D uint8 grayscale image
        num_points: number of circular neighbours (8 is standard)
        radius:     radius of the circular neighbourhood

    Returns:
        2-D uint32 array of LBP codes, same size as gray
    """
    h, w   = gray.shape
    lbp    = np.zeros((h, w), dtype=np.uint32)
    gray_f = gray.astype(np.float64)

    for p in range(num_points):
        angle = 2.0 * np.pi * p / num_points
        # Floating-point offset of this neighbour
        dx = radius * np.cos(angle)
        dy = -radius * np.sin(angle)

        # Integer floor of the offset
        x0 = int(np.floor(dx))
        y0 = int(np.floor(dy))

        # Bilinear interpolation weights
        fx = dx - x0          # fractional part in x
        fy = dy - y0          # fractional part in y
        w00 = (1.0 - fx) * (1.0 - fy)
        w10 = fx            * (1.0 - fy)
        w01 = (1.0 - fx) * fy
        w11 = fx            * fy

        # Pad image so out-of-bound accesses are safe (edge-padding)
        pad = radius + 2
        padded = np.pad(gray_f, pad, mode='edge')

        # Base offset in padded array
        by = pad + y0
        bx = pad + x0

        # Four bilinear neighbours (all as full-image arrays)
        n = (w00 * padded[by    : by + h,     bx     : bx + w    ] +
             w10 * padded[by    : by + h,     bx + 1 : bx + w + 1] +
             w01 * padded[by + 1: by + h + 1, bx     : bx + w    ] +
             w11 * padded[by + 1: by + h + 1, bx + 1 : bx + w + 1])

        # Threshold: set bit p where neighbour >= center
        lbp |= (n >= gray_f).astype(np.uint32) << p

    return lbp


def _lbp_histogram_grid_fast(gray: np.ndarray, grid_x: int, grid_y: int,
                              num_points: int, radius: int) -> np.ndarray:
    """
    Divide the image into a grid of cells, compute a fast vectorised LBP
    histogram per cell, and concatenate all histograms into one descriptor.

    This preserves spatial information (crucial for face recognition accuracy).

    Args:
        gray:       2-D uint8 grayscale image (already resized to 64x64)
        grid_x:     number of grid columns
        grid_y:     number of grid rows
        num_points: LBP circular neighbours
        radius:     LBP circle radius

    Returns:
        1-D float32 array of concatenated histograms
    """
    h, w       = gray.shape
    cell_h     = h // grid_y
    cell_w     = w // grid_x
    bins       = 2 ** num_points
    histograms = []

    # Compute full-image LBP map once (vectorised — fast)
    lbp_map = _lbp_fast(gray, num_points=num_points, radius=radius)

    for gy in range(grid_y):
        for gx in range(grid_x):
            y_start = gy * cell_h
            y_end   = min((gy + 1) * cell_h, h)
            x_start = gx * cell_w
            x_end   = min((gx + 1) * cell_w, w)

            cell_lbp = lbp_map[y_start:y_end, x_start:x_end]

            hist, _ = np.histogram(cell_lbp.ravel(), bins=bins, range=(0, bins))
            histograms.append(hist.astype(np.float32))

    return np.concatenate(histograms)

# AI-Based Smart Attendance Management System Using Face Recognition and Liveness Detection

> **B.Tech CSE Final Year Project** | Python · Flask · OpenCV · SQLite · Bootstrap 5

---

## Project Description

This is a web-based smart attendance system that uses a webcam to automatically recognize registered students and mark their attendance. It uses computer vision and face recognition techniques to identify faces, performs a basic liveness check to reduce simple photo/video spoofing, and stores all attendance data in a database.

---

## Problem Statement

Traditional attendance systems (paper rolls, manual entry) are slow, error-prone, and open to proxy attendance (one student marking for another). A face-recognition-based system solves these problems by:
- Verifying physical presence of the student
- Automating the marking process
- Providing instant reports

---

## Objectives

1. Register students with face samples via webcam
2. Generate face embeddings for each student
3. Detect faces in real time using a live webcam feed
4. Recognize registered students using face embeddings
5. Perform basic liveness detection to reduce photo spoofing
6. Automatically mark attendance with timestamp
7. Prevent duplicate attendance on the same day
8. Store all data securely in a database
9. Provide an admin dashboard with statistics
10. Generate daily, monthly, and student-wise reports
11. Export reports to CSV and Excel

---

## Features

- Admin login with hashed password
- Student registration with face capture (10–20 samples)
- Real-time face detection using OpenCV Haar Cascade
- Face recognition using LBP (Local Binary Pattern) histogram embeddings
- Liveness detection using Eye Aspect Ratio (EAR) blink detection
- Automatic attendance marking with duplicate prevention
- Dashboard with live charts (Chart.js)
- Attendance records browser with filters and pagination
- Daily / Monthly / Student-wise reports
- CSV and Excel export (styled)
- Responsive UI with Bootstrap 5

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite, SQLAlchemy |
| Computer Vision | OpenCV, NumPy |
| Face Recognition | LBP Histogram Embeddings (custom, NumPy) |
| Liveness Detection | Eye Aspect Ratio (EAR) via OpenCV / dlib |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript |
| Charts | Chart.js |
| Reports | Pandas, openpyxl |
| Auth | Flask Session, Werkzeug password hashing |

---

## System Architecture

```
Browser (Webcam)
       │
       │ AJAX POST (base64 JPEG frame)
       ▼
Flask Web Server (app.py)
       │
       ├── routes/auth.py        ← Login / Logout
       ├── routes/dashboard.py   ← Dashboard stats
       ├── routes/students.py    ← Student CRUD
       ├── routes/capture.py     ← Face registration
       ├── routes/attendance.py  ← Live attendance pipeline
       ├── routes/records.py     ← Attendance records
       └── routes/reports.py     ← Reports & Export
       │
       ├── services/
       │   ├── face_detection.py         ← OpenCV Haar Cascade
       │   ├── face_recognition_service.py ← LBP Embedding + Cosine Distance
       │   ├── liveness.py               ← EAR Blink Detection
       │   ├── attendance_service.py     ← Mark / Query attendance
       │   └── report_service.py         ← Pandas DataFrames, CSV/Excel
       │
       └── models/
           ├── admin.py      ← Admin table (hashed password)
           ├── student.py    ← Student table
           └── attendance.py ← Attendance table (unique constraint)
               │
               SQLite Database (database/attendance.db)
```

---

## Folder Structure

```
face-attendance-system/
├── app.py                        # Main Flask application
├── config.py                     # All configuration constants
├── requirements.txt              # Python dependencies
├── README.md
├── .gitignore
├── .env.example
│
├── database/
│   └── attendance.db             # Auto-created on first run
│
├── models/
│   ├── admin.py                  # Admin ORM model
│   ├── student.py                # Student ORM model
│   └── attendance.py             # Attendance ORM model
│
├── routes/
│   ├── auth.py                   # Login / logout
│   ├── dashboard.py              # Dashboard
│   ├── students.py               # Student management
│   ├── capture.py                # Face capture (registration)
│   ├── attendance.py             # Live attendance
│   ├── records.py                # Attendance records
│   └── reports.py                # Reports & export
│
├── services/
│   ├── face_detection.py         # Face detection module
│   ├── face_recognition_service.py # Embeddings + recognition
│   ├── liveness.py               # EAR liveness detection
│   ├── attendance_service.py     # Business logic
│   └── report_service.py         # Report generation
│
├── data/
│   ├── faces/                    # Raw face images per student
│   └── embeddings/               # .npy embedding files
│
├── templates/                    # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── add_student.html
│   ├── capture_face.html
│   ├── attendance.html
│   ├── records.html
│   └── reports.html
│
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/
│
└── utils/
    ├── database.py               # DB init + seeding
    └── helpers.py                # Decorators, validators
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Webcam (built-in or USB)
- Windows / Linux / macOS

### Step 1: Clone or Extract the Project

```bash
cd face-attendance-system
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

### Step 3: Activate the Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run the Application

```bash
python app.py
```

### Step 6: Open in Browser

```
http://127.0.0.1:5000
```

---

## Default Admin Login

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

> ⚠️ **IMPORTANT:** Change the default password before deploying to any shared or production environment. The password is stored as a bcrypt hash — never in plain text.

---

## Database Structure

### Admin Table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| username | VARCHAR(80) | Unique |
| password_hash | VARCHAR(256) | Werkzeug bcrypt hash |
| created_at | DATETIME | Auto |

### Student Table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| student_id | VARCHAR(50) | Unique, indexed |
| name | VARCHAR(120) | |
| department | VARCHAR(100) | |
| year | VARCHAR(20) | |
| email | VARCHAR(120) | Unique |
| face_registered | BOOLEAN | True after face capture |
| sample_count | INTEGER | Number of face samples |
| created_at | DATETIME | Auto |

### Attendance Table
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| student_id | INTEGER | FK → student.id |
| date | VARCHAR(10) | YYYY-MM-DD |
| time | VARCHAR(8) | HH:MM:SS |
| status | VARCHAR(20) | Present / Absent |
| confidence | FLOAT | Recognition confidence % |
| created_at | DATETIME | Auto |
| | | **UNIQUE(student_id, date)** ← prevents duplicates |

---

## How Face Recognition Works

### Step 1: Registration
1. Admin opens the Capture Face page for a student.
2. Browser accesses webcam via `navigator.mediaDevices.getUserMedia`.
3. Every 600ms, a JPEG frame is sent to the server via AJAX POST.
4. Server detects the face using OpenCV Haar Cascade.
5. Face region is cropped and resized to 128×128.
6. Quality check: Laplacian variance detects blurry images.
7. LBP (Local Binary Pattern) histogram embedding is computed.
8. After 10–20 samples, all embeddings are averaged into one.
9. The average embedding is saved as `data/embeddings/<student_id>.npy`.

### Step 2: Recognition
1. Live webcam frame is captured during attendance.
2. Face is detected and cropped.
3. LBP embedding is computed for the live face.
4. The embedding is compared against every student's stored embedding.
5. Comparison uses **Cosine Distance**: `distance = 1 - dot(a, b)`.
6. The student with the smallest distance is the best match.
7. If `distance <= FACE_MATCH_THRESHOLD (0.45)` → recognized.
8. Otherwise → "Unknown Person".

### What is a Face Embedding?
A face embedding is a compact numerical vector (array of numbers) that represents the key features of a face. Similar faces produce similar vectors. Cosine distance measures how different two vectors are.

- Distance = 0.0 → identical faces
- Distance = 0.45 → recognition threshold (configurable in config.py)
- Distance > 0.45 → unknown

---

## How Liveness Detection Works

**Purpose:** Prevent simple spoofing attacks where someone shows a static photograph to the camera.

**Method: Eye Aspect Ratio (EAR) Blink Detection**

The Eye Aspect Ratio is computed from the positions of the eye landmarks:

```
EAR = (|p2-p6| + |p3-p5|) / (2 × |p1-p4|)
```

- When eyes are **open**: EAR ≈ 0.3
- When eyes are **closed** (blink): EAR drops to ≈ 0.0
- A **photograph cannot blink** → liveness fails

The system requires **2 blinks** within **15 seconds** to pass liveness.

**Two backends:**
1. **dlib** (if installed): Uses 68-point facial landmarks for accurate EAR
2. **OpenCV Haar cascade** (fallback): Uses eye region detection

> ⚠️ **Disclaimer:** This is **basic liveness detection** for a college project. It is NOT certified anti-spoofing. Video loops or advanced 3D masks may defeat it. Do not use in high-security systems.

---

## How Attendance Works

```
Start Camera
    ↓
Detect Face (OpenCV Haar Cascade)
    ↓
Liveness Check (EAR Blink Detection — must blink 2×)
    ↓
Face Recognition (LBP Embeddings + Cosine Distance)
    ↓
Check Today's Attendance (DB query)
    ↓
If not marked → Mark Present (insert record)
If already marked → Show "Already marked" message
    ↓
Display result with name, ID, department, time, confidence
```

**Duplicate Prevention:**
- Application-level check: query DB before inserting
- Database-level constraint: `UNIQUE(student_id, date)` — even race conditions are handled

---

## Testing Checklist

### Registration
- [ ] Valid student — registers correctly
- [ ] Duplicate student ID — shows error
- [ ] Missing information — validation error
- [ ] No face in frame — "No face detected"
- [ ] Multiple faces — "Multiple faces detected"
- [ ] Blurry image — rejected by quality check

### Recognition
- [ ] Registered student — recognized correctly
- [ ] Unknown person — "Unknown Person"
- [ ] Poor lighting — may reduce confidence
- [ ] Face at slight angle — still recognized (averaging helps)

### Liveness
- [ ] Real person blinking — passes after 2 blinks
- [ ] Static photograph — fails (no blink detected)
- [ ] Timeout (15s) — fails, resets

### Attendance
- [ ] First attendance of day — marked Present
- [ ] Second attempt same day — "Already marked today"
- [ ] Unknown person — not marked, shows Unknown
- [ ] Multiple people in frame — rejected

### Reports
- [ ] Daily report with date filter
- [ ] Monthly report with month/year
- [ ] Student-wise report
- [ ] CSV export — downloads correctly
- [ ] Excel export — styled file downloads

---

## Common Errors and Fixes

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'cv2'` | Run `pip install opencv-python` |
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install Flask` |
| Camera access denied in browser | Allow camera permission in browser settings |
| `sqlite3.OperationalError` | Delete `database/attendance.db` and restart |
| Webcam shows black screen | Try a different browser (Chrome recommended) |
| Low recognition accuracy | Recapture face samples in better lighting |
| `ImportError: dlib` | dlib is optional; the system uses OpenCV fallback |

---

## Limitations

1. Recognition accuracy depends on lighting quality
2. Does not handle very different hairstyles/accessories well
3. LBP embeddings are less accurate than deep learning embeddings (DeepFace, FaceNet)
4. Liveness detection can be fooled by video playback
5. Single-machine deployment only (SQLite is not for multiple servers)
6. No SSL/HTTPS (required for production webcam access on most browsers)

---

## Future Improvements

1. Replace LBP with deep learning embeddings (FaceNet, ArcFace, DeepFace)
2. Add 3D liveness detection or challenge-response
3. Deploy with HTTPS using Nginx + Let's Encrypt
4. Switch to PostgreSQL for multi-server deployment
5. Add email notifications for low attendance
6. Add mobile app (Android/iOS) interface
7. Integration with college ERP systems
8. Multi-camera support for large classrooms
9. Role-based access (teacher vs. admin vs. student)
10. Student self-service portal (view own attendance)

---

## Privacy Considerations

This system processes **biometric data** (face images and embeddings). Please note:

- **Consent:** Face data should only be collected with the student's informed consent.
- **Data Minimization:** Only store what is necessary (embeddings, not raw images in production).
- **Access Control:** Restrict access to face data to authorized administrators only.
- **Deletion:** Administrators can delete a student and all their data via the student management page.
- **Security:** Face embedding files (`.npy`) should not be shared or exposed publicly.
- **Disclaimer:** This is a **college/demo project**. It should NOT be used as a production biometric security system without additional legal, security, privacy, and compliance work (e.g., PDPA, GDPR compliance).

---

## Screenshots

> *(Add screenshots here after running the project)*

- [ ] Login page
- [ ] Dashboard
- [ ] Student list
- [ ] Face capture
- [ ] Attendance page
- [ ] Reports page

---

## Author

**Student Name:** *(Your Name)*
**Roll Number:** *(Your Roll Number)*
**Department:** Computer Science & Engineering
**Institution:** *(Your College Name)*
**Academic Year:** 2025–2026
**Project Guide:** *(Guide Name)*

---

## Viva Q&A Reference

**Q: What problem does this project solve?**
A: It automates attendance marking using face recognition, eliminates proxy attendance, and reduces manual effort for teachers.

**Q: Why face recognition?**
A: Faces are unique biometric identifiers that cannot be easily shared or forgotten like ID cards or passwords.

**Q: What is a face embedding?**
A: A face embedding is a compact numerical vector (array of numbers) that represents the key visual features of a face. Similar faces produce similar vectors.

**Q: How does face matching work?**
A: We compute embeddings for the live face and all registered students, then measure cosine distance between them. The student with the smallest distance below the threshold is the match.

**Q: What is cosine distance?**
A: `distance = 1 - dot(a, b)` where a and b are L2-normalized vectors. Range: 0 (identical) to 2 (opposite). For faces, we use threshold 0.45.

**Q: Why is liveness detection needed?**
A: To prevent someone from showing a printed photo of a student to trick the system into marking their attendance.

**Q: How does EAR liveness detection work?**
A: We measure the Eye Aspect Ratio (ratio of eye height to width). When a person blinks, EAR drops sharply. A photograph cannot blink, so it fails the check.

**Q: How is duplicate attendance prevented?**
A: Two layers: (1) Application-level DB query before inserting, (2) Database-level UNIQUE constraint on (student_id, date).

**Q: Why Flask?**
A: Flask is lightweight, easy to understand, and perfect for a college project. It does not require complex configuration unlike Django.

**Q: Why SQLite?**
A: SQLite requires no separate server installation, stores data in a single file, and is perfect for single-machine deployments like a college lab.

**Q: How is attendance percentage calculated?**
A: `percentage = (present_days / total_days) × 100`

**Q: What are the limitations?**
A: Accuracy depends on lighting, LBP is less accurate than deep learning, liveness can be fooled by video, and it runs on a single machine.

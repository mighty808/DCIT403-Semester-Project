# Attendance Tracker Agent

## DCIT 403 – Intelligent Systems | Semester Project

A terminal-based multi-agent attendance tracking system built with Python. It uses a **Goal-based Reflex Agent** to manage attendance and a **Simple Reflex Agent** to issue notifications when attendance drops below threshold.

---

### Requirements

- Python 3.8 or higher
- No external libraries needed

### How to Run

```
python main.py
```

Sample data (students, courses, attendance) is auto-created on first run.

---

### Project Structure

```
DCIT403-Semester-Project/
├── main.py                 # Entry point — main menu loop
├── attendance_agent.py     # Attendance Agent (Goal-based Reflex Agent)
├── notification_agent.py   # Notification Agent (Simple Reflex Agent)
├── data_store.py           # Data layer — JSON read/write + seed data
├── README.md
└── data/                   # Auto-created on first run
    ├── students.json
    ├── courses.json
    └── attendance.json
```

---

### Agents

| Agent | Type | Role |
|-------|------|------|
| **AttendanceAgent** | Goal-based Reflex | Perceives user input, decides action, marks attendance, calculates percentages, evaluates thresholds |
| **NotificationAgent** | Simple Reflex | Receives breach events and issues WARNING (<75%) or CRITICAL (<60%) alerts |

---

### Menu Options

| # | Option | Description |
|---|--------|-------------|
| 1 | **Mark Attendance** | Select course → find student (by ID or from list) → verify with PIN (3 attempts) → mark Present / Absent / Late |
| 2 | **View Student Attendance** | Select student from list → see attendance % per enrolled course |
| 3 | **View Class Report** | Select course → see all enrolled students sorted by attendance % |
| 4 | **View At-Risk Students** | List all students below 75% attendance with WARNING/CRITICAL level |
| 5 | **Simulate Day** | Select course → auto-generate random attendance for all enrolled students |
| 6 | **Exit** | Quit the program |

---

### Sample Students

| Student ID | Name | PIN | Enrolled Courses |
|------------|------|-----|------------------|
| 11110000 | Alice Mensah | 39201 | DCIT403, DCIT401 |
| 11120000 | Bob Asante | 58473 | DCIT403, DCIT401 |
| 11130000 | John Agyei | 71624 | DCIT403 |
| 11140000 | Mary Osei | 42958 | DCIT403, DCIT401 |
| 11150000 | Kofi Boateng | 86310 | DCIT401 |

### Sample Courses

| Course ID | Course Name |
|-----------|-------------|
| DCIT403 | Designing Intelligent Agents |
| DCIT401 | Social, Legal, Ethical & Professional Issues |

---

### Attendance Thresholds

- **≥ 75%** — ✓ OK
- **60–74%** — ⚠ WARNING (notification issued)
- **< 60%** — !! CRITICAL (notification issued)

### Scoring

| Status | Score |
|--------|-------|
| Present | 1.0 |
| Late | 0.5 |
| Absent | 0.0 |

Percentage = (total score / total sessions) × 100

---

### Reset Data

Delete the `data/` folder to start fresh. It will be recreated on next run.

```
rm -rf data/
python main.py
```

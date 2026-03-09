import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save(filename, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, filename), "w") as f:
        json.dump(data, f, indent=2)


def seed():
    """Create sample data on first run."""
    if not os.path.exists(os.path.join(DATA_DIR, "students.json")):
        students = [
            {"student_id": "11110000", "name": "Alice Mensah",  "pin": "39201", "enrolled": ["DCIT403", "DCIT401"]},
            {"student_id": "11120000", "name": "Bob Asante",    "pin": "58473", "enrolled": ["DCIT403", "DCIT401"]},
            {"student_id": "11130000", "name": "John Agyei",    "pin": "71624", "enrolled": ["DCIT403"]},
            {"student_id": "11140000", "name": "Mary Osei",     "pin": "42958", "enrolled": ["DCIT403", "DCIT401"]},
            {"student_id": "11150000", "name": "Kofi Boateng",  "pin": "86310", "enrolled": ["DCIT401"]},
        ]
        courses = [
            {"course_id": "DCIT403", "course_name": "Designing Intelligent Agents"},
            {"course_id": "DCIT401", "course_name": "Social, Legal, Ethical & Professional Issues"},
        ]
        save("students.json", students)
        save("courses.json", courses)
        save("attendance.json", [])
        print("  [✓] Sample data created in /data folder.")

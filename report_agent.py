from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import json
from datetime import datetime

students = {
    "S001": "Alice",
    "S002": "Bob",
    "S003": "Carol",
    "S004": "Dave"
}

class ReportAgent(Agent):

    class GenerateReport(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=15)
            if msg:
                try:
                    if msg.body is None:
                        raise ValueError("ReportAgent received an empty message body")

                    payload = json.loads(msg.body)
                    if not isinstance(payload, dict):
                        raise ValueError("ReportAgent expected a dictionary payload")

                    if "records" in payload:
                        records = payload.get("records", {})
                        active_students = payload.get("students", students)
                        course = payload.get("course", {})
                        course_label = f"{course.get('code', 'N/A')} {course.get('name', '')}".strip()
                    else:
                        records = payload
                        active_students = students
                        course_label = "Unknown Course"

                    if not isinstance(records, dict):
                        raise ValueError("ReportAgent records payload must be a dictionary")
                    if not isinstance(active_students, dict):
                        active_students = students

                    normalized_records = {
                        sid: str(status).strip().upper()
                        for sid, status in records.items()
                    }

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    present = [sid for sid, s in normalized_records.items() if s == "PRESENT"]
                    late    = [sid for sid, s in normalized_records.items() if s == "LATE"]
                    absent  = [sid for sid, s in normalized_records.items() if s == "ABSENT"]

                    total = len(normalized_records)
                    attendance_rate = ((len(present) + len(late)) / total * 100) if total else 0.0

                    present_names = [active_students.get(s, s) for s in present]
                    late_names = [active_students.get(s, s) for s in late]
                    absent_names = [active_students.get(s, s) for s in absent]

                    report = f"""
╔══════════════════════════════════════╗
║       ATTENDANCE SUMMARY REPORT      ║
╠══════════════════════════════════════╣
    Course    : {course_label}
  Generated : {timestamp}
  Total     : {total} students

  ✅ Present : {len(present)} → {present_names}
  ⚠️  Late    : {len(late)}    → {late_names}
  ❌ Absent  : {len(absent)}  → {absent_names}

  Attendance Rate: {attendance_rate:.1f}%
╚══════════════════════════════════════╝"""

                    print(report)

                    with open("attendance_report.txt", "a") as f:
                        f.write(report + "\n")
                    print("📁 ReportAgent: Report saved to attendance_report.txt")

                except Exception as e:
                    print(f"ReportAgent error: {e}")
                    with open("report_fallback.log", "a", encoding="utf-8") as f:
                        f.write(f"Failed to generate report: {msg.body} | error: {e}\n")

    async def setup(self):
        print("ReportAgent started")
        self.add_behaviour(self.GenerateReport())
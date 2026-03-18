from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import json
from datetime import datetime
from config import DEFAULT_STUDENTS

# Default mapping used when payload does not include a roster.
students = DEFAULT_STUDENTS


class ReportAgent(Agent):

    # Cyclic behaviour continuously listens and generates attendance reports.
    class GenerateReport(CyclicBehaviour):
        async def run(self):
            # Wait for incoming attendance payload.
            msg = await self.receive(timeout=15)
            if msg:
                try:
                    # Validate and decode message body.
                    if msg.body is None:
                        raise ValueError("ReportAgent received an empty message body")

                    payload = json.loads(msg.body)
                    if not isinstance(payload, dict):
                        raise ValueError("ReportAgent expected a dictionary payload")

                    # Support full payload and backward-compatible records-only payload.
                    if "records" in payload:
                        records = payload.get("records", {})
                        active_students = payload.get("students", students)
                        course = payload.get("course", {})
                        course_label = f"{course.get('code', 'N/A')} {course.get('name', '')}".strip()
                    else:
                        records = payload
                        active_students = students
                        course_label = "Unknown Course"

                    # Validate expected data structures.
                    if not isinstance(records, dict):
                        raise ValueError("ReportAgent records payload must be a dictionary")
                    if not isinstance(active_students, dict):
                        active_students = students

                    # Normalize status values so summary counts are consistent.
                    normalized_records = {
                        sid: str(status).strip().upper()
                        for sid, status in records.items()
                    }

                    # Build timestamp for the report header.
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Group students by attendance status.
                    present = [sid for sid, s in normalized_records.items() if s == "PRESENT"]
                    late    = [sid for sid, s in normalized_records.items() if s == "LATE"]
                    absent  = [sid for sid, s in normalized_records.items() if s == "ABSENT"]

                    # Compute class attendance rate.
                    total = len(normalized_records)
                    attendance_rate = ((len(present) + len(late)) / total * 100) if total else 0.0

                    # Convert IDs to student names for a readable report.
                    present_names = [active_students.get(s, s) for s in present]
                    late_names = [active_students.get(s, s) for s in late]
                    absent_names = [active_students.get(s, s) for s in absent]

                    # Create formatted multi-line report for terminal and file output.
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

                    # Print report to terminal.
                    print(report)

                    # Persist report history to text file.
                    with open("attendance_report.txt", "a") as f:
                        f.write(report + "\n")
                    print("📁 ReportAgent: Report saved to attendance_report.txt")

                except Exception as e:
                    # Log report generation failures for debugging.
                    print(f"ReportAgent error: {e}")
                    with open("report_fallback.log", "a", encoding="utf-8") as f:
                        f.write(f"Failed to generate report: {msg.body} | error: {e}\n")

    async def setup(self):
        # Attach continuous report-generation behaviour.
        print("ReportAgent started")
        self.add_behaviour(self.GenerateReport())
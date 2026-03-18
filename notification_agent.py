from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import json
from config import DEFAULT_STUDENTS

# Default student mapping used only if incoming payload omits roster data.
students = DEFAULT_STUDENTS

# Alert triggers when class attendance drops below this percentage.
LOW_ATTENDANCE_THRESHOLD = 70.0


class NotificationAgent(Agent):

    # Cyclic behaviour listens continuously for attendance messages.
    class ListenAndAlert(CyclicBehaviour):
        async def run(self):
            # Wait for one message; timeout keeps loop responsive.
            msg = await self.receive(timeout=15)
            if msg:
                try:
                    # Validate incoming message content.
                    if msg.body is None:
                        raise ValueError("NotificationAgent received an empty message body")

                    payload = json.loads(msg.body)
                    if not isinstance(payload, dict):
                        raise ValueError("NotificationAgent expected a dictionary payload")

                    # Support both full payload format and legacy records-only format.
                    if "records" in payload:
                        records = payload.get("records", {})
                        active_students = payload.get("students", students)
                        course = payload.get("course", {})
                        course_label = f"{course.get('code', 'N/A')} {course.get('name', '')}".strip()
                    else:
                        records = payload
                        active_students = students
                        course_label = "Unknown Course"

                    # Final type checks before processing.
                    if not isinstance(records, dict):
                        raise ValueError("NotificationAgent records payload must be a dictionary")
                    if not isinstance(active_students, dict):
                        active_students = students

                    # Normalize statuses to uppercase for reliable comparisons.
                    normalized_records = {
                        sid: str(status).strip().upper()
                        for sid, status in records.items()
                    }

                    print(f"\n NotificationAgent processing alerts for {course_label}...")

                    # Compute overall attendance percentage for the class.
                    absent_count = sum(1 for s in normalized_records.values() if s == "ABSENT")
                    total = len(normalized_records)
                    attendance_rate = ((total - absent_count) / total) * 100 if total else 0.0

                    # Send student-level alerts for absent/late statuses.
                    for sid, status in normalized_records.items():
                        name = active_students.get(sid, sid)
                        if status == "ABSENT":
                            print(f"   Notifying {name}: You were marked ABSENT today.")
                        elif status == "LATE":
                            print(f"    {name} was marked LATE.")

                    # Send class-level warning if attendance is too low.
                    if attendance_rate < LOW_ATTENDANCE_THRESHOLD:
                        print(f"\n🚨 ALERT: Class attendance is {attendance_rate:.1f}% — below threshold!")
                    else:
                        print(f"\n Attendance rate: {attendance_rate:.1f}% — within acceptable range.")

                except Exception as e:
                    # Log malformed payloads/errors without crashing the behaviour loop.
                    print(f"NotificationAgent error: {e}")
                    with open("notification_fallback.log", "a", encoding="utf-8") as f:
                        f.write(f"Failed to process message: {msg.body} | error: {e}\n")

    async def setup(self):
        # Attach long-running listener behaviour at agent startup.
        print("NotificationAgent started")
        self.add_behaviour(self.ListenAndAlert())
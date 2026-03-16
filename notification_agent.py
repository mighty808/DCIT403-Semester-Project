from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import json

students = {
    "S001": "Alice",
    "S002": "Bob",
    "S003": "Carol",
    "S004": "Dave"
}

LOW_ATTENDANCE_THRESHOLD = 70.0

class NotificationAgent(Agent):

    class ListenAndAlert(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=15)
            if msg:
                try:
                    if msg.body is None:
                        raise ValueError("NotificationAgent received an empty message body")

                    payload = json.loads(msg.body)
                    if not isinstance(payload, dict):
                        raise ValueError("NotificationAgent expected a dictionary payload")

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
                        raise ValueError("NotificationAgent records payload must be a dictionary")
                    if not isinstance(active_students, dict):
                        active_students = students

                    normalized_records = {
                        sid: str(status).strip().upper()
                        for sid, status in records.items()
                    }

                    print(f"\n🔔 NotificationAgent processing alerts for {course_label}...")

                    absent_count = sum(1 for s in normalized_records.values() if s == "ABSENT")
                    total = len(normalized_records)
                    attendance_rate = ((total - absent_count) / total) * 100 if total else 0.0

                    for sid, status in normalized_records.items():
                        name = active_students.get(sid, sid)
                        if status == "ABSENT":
                            print(f"  📧 Notifying {name}: You were marked ABSENT today.")
                        elif status == "LATE":
                            print(f"  ⚠️  {name} was marked LATE.")

                    if attendance_rate < LOW_ATTENDANCE_THRESHOLD:
                        print(f"\n🚨 ALERT: Class attendance is {attendance_rate:.1f}% — below threshold!")
                    else:
                        print(f"\n✅ Attendance rate: {attendance_rate:.1f}% — within acceptable range.")

                except Exception as e:
                    print(f"NotificationAgent error: {e}")
                    with open("notification_fallback.log", "a", encoding="utf-8") as f:
                        f.write(f"Failed to process message: {msg.body} | error: {e}\n")

    async def setup(self):
        print("NotificationAgent started")
        self.add_behaviour(self.ListenAndAlert())
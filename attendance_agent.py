import spade
import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message
import json
from datetime import datetime

XMPP_SERVER = "xmpp.jp"
CLASS_START = "07:30 AM"
LATE_THRESHOLD = 15

students = {
    "11110000": "Alice",
    "11110001": "Bob",
    "11110002": "Carol",
    "11110003": "Dave",
}

checkins = {}


def normalize_student_id(raw_sid: str, roster: dict[str, str]) -> str:
    sid = raw_sid.strip().upper()

    candidates = [sid]

    if sid.isdigit():
        if len(sid) <= 3:
            candidates.append(f"S{int(sid):03d}")
        if len(sid) >= 3:
            candidates.append(f"S{int(sid[-3:]):03d}")

    if sid.startswith("S") and sid[1:].isdigit() and len(sid[1:]) <= 3:
        candidates.append(f"S{int(sid[1:]):03d}")

    for candidate in candidates:
        if candidate in roster:
            return candidate

    return sid

class AttendanceAgent(Agent):

    class ProcessAttendance(OneShotBehaviour):
        async def collect_terminal_checkins(self):
            entered_checkins = dict(checkins)
            roster = self.agent.course_students
            course_label = f"{self.agent.course_code} {self.agent.course_name}"
            class_start = self.agent.class_start_time

            print(f"\n📝 Course: {course_label}")
            print(f"🕒 Class starts at: {class_start} (late after +{LATE_THRESHOLD} mins)")
            print("📝 Enter check-ins (leave Student ID blank to finish):")
            print("   Format: Student ID (as listed in roster), student name, time HH:MM AM/PM")

            while True:
                try:
                    sid = normalize_student_id(await asyncio.to_thread(input, "Student ID: "), roster)
                except EOFError:
                    print("\nℹ️  Input stream closed. Finishing sign-in.")
                    break

                if not sid:
                    break

                if sid not in roster:
                    print("  ❌ Unknown Student ID. Try one of:", ", ".join(roster.keys()))
                    print("     Tip: Enter the ID exactly as shown in the selected course roster.")
                    continue

                try:
                    entered_name = (await asyncio.to_thread(input, "Student name: ")).strip()
                except EOFError:
                    entered_name = ""

                expected_name = roster[sid]
                if not entered_name:
                    print("  ❌ Student name is required.")
                    continue
                if entered_name.lower() != expected_name.lower():
                    print(f"  ❌ Name does not match ID {sid}. Expected: {expected_name}")
                    continue

                try:
                    raw_time = (await asyncio.to_thread(input, "Check-in time (HH:MM AM/PM, blank = now): ")).strip()
                except EOFError:
                    raw_time = ""

                checkin_time = (raw_time or datetime.now().strftime("%I:%M %p")).upper()
                try:
                    datetime.strptime(checkin_time, "%I:%M %p")
                except ValueError:
                    print("  ❌ Invalid time format. Use HH:MM AM/PM, e.g., 08:05 AM")
                    continue

                entered_checkins[sid] = checkin_time
                print(f"  ✅ Recorded {sid} ({expected_name}) at {checkin_time}")

                while True:
                    try:
                        action = (await asyncio.to_thread(input, "Enter another details? (y = continue / n = exit): ")).strip().lower()
                    except EOFError:
                        action = "n"

                    if action in ("", "y", "yes"):
                        break
                    if action in ("n", "no", "exit"):
                        return entered_checkins
                    print("  ❌ Invalid choice. Type y to continue or n to exit.")

            return entered_checkins

        async def run(self):
            entered_checkins = await self.collect_terminal_checkins()
            roster = self.agent.course_students
            class_start = self.agent.class_start_time.upper()
            class_start_dt = datetime.strptime(class_start, "%I:%M %p")

            records = {}
            for sid, name in roster.items():
                if sid in entered_checkins:
                    t = datetime.strptime(entered_checkins[sid], "%I:%M %p")
                    diff = int((t - class_start_dt).total_seconds() // 60)
                    records[sid] = "LATE" if diff > LATE_THRESHOLD else "PRESENT"
                else:
                    records[sid] = "ABSENT"

            print("\n📋 Attendance Records:")
            for sid, status in records.items():
                print(f"  {roster[sid]:10} → {status}")

            payload = {
                "course": {
                    "code": self.agent.course_code,
                    "name": self.agent.course_name,
                },
                "class_start": class_start,
                "late_threshold": LATE_THRESHOLD,
                "students": roster,
                "records": records,
            }

            # Send to NotificationAgent
            msg = Message(to=f"notif_agent@{XMPP_SERVER}")
            msg.set_metadata("performative", "inform")
            msg.set_metadata("ontology", "attendance-system")
            msg.body = json.dumps(payload)
            await self.send(msg)
            print("\n✅ AttendanceAgent: Records sent to NotificationAgent")

            # Send to ReportAgent
            msg2 = Message(to=f"report_agent@{XMPP_SERVER}")
            msg2.set_metadata("performative", "inform")
            msg2.set_metadata("ontology", "attendance-system")
            msg2.body = json.dumps(payload)
            await self.send(msg2)
            print("✅ AttendanceAgent: Records sent to ReportAgent")
            self.agent.process_complete.set()

    async def setup(self):
        print("AttendanceAgent started")
        self.course_code = getattr(self, "course_code", "DCIT403")
        self.course_name = getattr(self, "course_name", "Designing Intelligent Agents")
        self.course_students = getattr(self, "course_students", students)
        self.class_start_time = getattr(self, "class_start_time", CLASS_START)
        self.process_complete = asyncio.Event()
        self.add_behaviour(self.ProcessAttendance())
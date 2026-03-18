import spade
import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message
import json
from datetime import datetime
from config import DEFAULT_STUDENTS

# Shared constants for message routing and attendance logic.
XMPP_SERVER = "xmpp.jp"
CLASS_START = "07:30 AM"
LATE_THRESHOLD = 15

# Default roster used when no course-specific roster is injected from main.py.
students = DEFAULT_STUDENTS

# Temporary in-memory store for check-ins during one run.
checkins = {}


def normalize_student_id(raw_sid: str, roster: dict[str, str]) -> str:
    # Normalize input so IDs like "1" or "001" can map to expected roster keys.
    sid = raw_sid.strip().upper()

    candidates = [sid]

    # Try common shorthand numeric formats.
    if sid.isdigit():
        if len(sid) <= 3:
            candidates.append(f"S{int(sid):03d}")
        if len(sid) >= 3:
            candidates.append(f"S{int(sid[-3:]):03d}")

    # Try normalizing values that already start with "S".
    if sid.startswith("S") and sid[1:].isdigit() and len(sid[1:]) <= 3:
        candidates.append(f"S{int(sid[1:]):03d}")

    # Return the first candidate that exists in the active roster.
    for candidate in candidates:
        if candidate in roster:
            return candidate

    # Fall back to original cleaned value if no candidate matches.
    return sid


class AttendanceAgent(Agent):

    # One-shot behaviour runs once: collects check-ins and broadcasts final records.
    class ProcessAttendance(OneShotBehaviour):
        async def collect_terminal_checkins(self):
            # Start with any existing check-in data copied from module state.
            entered_checkins = dict(checkins)
            roster = self.agent.course_students
            course_label = f"{self.agent.course_code} {self.agent.course_name}"
            class_start = self.agent.class_start_time

            # Print instructions for the user input session.
            print(f"\n Course: {course_label}")
            print(f" Class starts at: {class_start} (late after +{LATE_THRESHOLD} mins)")
            print(" Enter check-ins (leave Student ID blank to finish):")
            print("   Format: Student ID (as listed in roster), student name")

            # Loop until user finishes entering student records.
            while True:
                try:
                    sid = normalize_student_id(await asyncio.to_thread(input, "Student ID: "), roster)
                except EOFError:
                    # Allows graceful exit when input stream is closed.
                    print("\n  Input stream closed. Finishing sign-in.")
                    break

                if not sid:
                    break

                # Validate that entered ID exists in the selected course roster.
                if sid not in roster:
                    print("  ❌ Unknown Student ID. Try one of:", ", ".join(roster.keys()))
                    print("     Tip: Enter the ID exactly as shown in the selected course roster.")
                    continue

                # Ask for student name and verify it matches the ID.
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

                # Always stamp check-in with current local time.
                checkin_time = datetime.now().strftime("%I:%M %p").upper()

                # Save valid check-in for this student.
                entered_checkins[sid] = checkin_time
                print(f"  ✅ Recorded {sid} ({expected_name}) at {checkin_time}")

                # Let user continue entering more records or finish early.
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
            # Collect user-entered check-ins, then evaluate attendance status.
            entered_checkins = await self.collect_terminal_checkins()
            roster = self.agent.course_students
            class_start = self.agent.class_start_time.upper()
            class_start_dt = datetime.strptime(class_start, "%I:%M %p")

            records = {}
            # Every roster student is marked PRESENT, LATE, or ABSENT.
            for sid, name in roster.items():
                if sid in entered_checkins:
                    t = datetime.strptime(entered_checkins[sid], "%I:%M %p")
                    diff = int((t - class_start_dt).total_seconds() // 60)
                    records[sid] = "LATE" if diff > LATE_THRESHOLD else "PRESENT"
                else:
                    records[sid] = "ABSENT"

            # Display computed attendance in terminal.
            print("\n Attendance Records:")
            for sid, status in records.items():
                print(f"  {roster[sid]:10} → {status}")

            # Build one shared payload consumed by NotificationAgent and ReportAgent.
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

            # Send attendance results to NotificationAgent.
            msg = Message(to=f"notif_agent@{XMPP_SERVER}")
            msg.set_metadata("performative", "inform")
            msg.set_metadata("ontology", "attendance-system")
            msg.body = json.dumps(payload)
            await self.send(msg)
            print("\n AttendanceAgent: Records sent to NotificationAgent")

            # Send the same results to ReportAgent for report generation.
            msg2 = Message(to=f"report_agent@{XMPP_SERVER}")
            msg2.set_metadata("performative", "inform")
            msg2.set_metadata("ontology", "attendance-system")
            msg2.body = json.dumps(payload)
            await self.send(msg2)
            print("AttendanceAgent: Records sent to ReportAgent")

            # Signal main.py that processing is complete.
            self.agent.process_complete.set()

    async def setup(self):
        # Initialize agent state and attach one-shot processing behaviour.
        print("AttendanceAgent started")
        self.course_code = getattr(self, "course_code", "DCIT403")
        self.course_name = getattr(self, "course_name", "Designing Intelligent Agents")
        self.course_students = getattr(self, "course_students", students)
        self.class_start_time = getattr(self, "class_start_time", CLASS_START)
        self.process_complete = asyncio.Event()
        self.add_behaviour(self.ProcessAttendance())
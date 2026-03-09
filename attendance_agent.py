import random
from datetime import date

import data_store
from notification_agent import NotificationAgent


class AttendanceAgent:
    """
    Goal-based Reflex Agent.
    Percepts : student_id, course_id, status, date, menu_choice
    Actions  : mark, view student, view class, view at-risk, simulate, menu
    """

    def __init__(self):
        self.notifier = NotificationAgent()

    # ── PERCEIVE ──────────────────────────────────────────────
    def perceive(self):
        return input("\n  Enter choice: ").strip()

    # ── DECIDE ────────────────────────────────────────────────
    def decide(self, choice):
        actions = {
            "1": self.mark_attendance,
            "2": self.view_student,
            "3": self.view_class_report,
            "4": self.view_at_risk,
            "5": self.simulate_day,
        }
        return actions.get(choice, self._invalid)

    # ── ACT ───────────────────────────────────────────────────
    def act(self, action):
        action()

    # ── ACTION 1: Mark Attendance ─────────────────────────────
    def mark_attendance(self):
        print("\n  ── Mark Attendance ──")
        courses  = data_store.load("courses.json")
        students = data_store.load("students.json")

        # 1) List courses
        print("  Available courses:")
        for i, c in enumerate(courses, 1):
            print(f"    {i}. {c['course_id']} – {c['course_name']}")

        pick = input("  Select course: ").strip()
        if not pick.isdigit() or int(pick) < 1 or int(pick) > len(courses):
            print("  [!] Invalid selection.")
            return
        cid = courses[int(pick) - 1]["course_id"]

        # 2) Choose how to pick a student
        enrolled = [s for s in students if cid in s["enrolled"]]
        if not enrolled:
            print(f"  [!] No students enrolled in {cid}.")
            return

        print("\n  Find student by:")
        print("    1. Enter Student ID")
        print("    2. Pick from list")
        method = input("  Select option: ").strip()

        if method == "1":
            sid = input("  Student ID: ").strip().upper()
            student = next((s for s in enrolled if s["student_id"] == sid), None)
            if not student:
                print(f"  [!] Student not found or not enrolled in {cid}.")
                return
        elif method == "2":
            print(f"\n  Students enrolled in {cid}:")
            for i, s in enumerate(enrolled, 1):
                print(f"    {i}. {s['student_id']} – {s['name']}")
            pick = input("  Select student: ").strip()
            if not pick.isdigit() or int(pick) < 1 or int(pick) > len(enrolled):
                print("  [!] Invalid selection.")
                return
            student = enrolled[int(pick) - 1]
            sid = student["student_id"]
        else:
            print("  [!] Invalid option.")
            return

        # Verify identity with PIN (3 attempts)
        for attempt in range(1, 4):
            pin = input(f"  Enter PIN to verify ({attempt}/3): ").strip()
            if pin == student.get("pin", ""):
                print("  [✓] Identity verified.")
                break
            remaining = 3 - attempt
            if remaining > 0:
                print(f"  [!] Incorrect PIN. {remaining} attempt(s) remaining.")
            else:
                print("  [!] Verification failed. No attempts remaining.")
                return

        # 3) Ask for status
        print("\n  Status:")
        print("    1. Present")
        print("    2. Absent")
        print("    3. Late")
        status_pick = input("  Select status: ").strip()
        status_map = {"1": "Present", "2": "Absent", "3": "Late"}
        if status_pick not in status_map:
            print("  [!] Invalid selection.")
            return
        status = status_map[status_pick]

        records = data_store.load("attendance.json")
        records.append({
            "student_id": sid,
            "course_id":  cid,
            "date":       str(date.today()),
            "status":     status,
        })
        data_store.save("attendance.json", records)
        print(f"  [✓] Recorded: {sid} ({student['name']}) → {status} in {cid}")

        self._evaluate(sid, cid)

    # ── ACTION 2: View Student ────────────────────────────────
    def view_student(self):
        print("\n  ── Student Attendance ──")
        students = data_store.load("students.json")

        print("  Select a student:")
        for i, s in enumerate(students, 1):
            print(f"    {i}. {s['student_id']} – {s['name']}")

        pick = input("  Select student: ").strip()
        if not pick.isdigit() or int(pick) < 1 or int(pick) > len(students):
            print("  [!] Invalid selection.")
            return
        student = students[int(pick) - 1]
        sid = student["student_id"]

        print(f"\n  Student : {student['name']} ({sid})")
        print(f"  {'Course':<10} {'Sessions':>9} {'Score':>7} {'%':>7}  Status")
        print("  " + "─" * 52)
        for cid in student["enrolled"]:
            pct, score, total = self._calc(sid, cid)
            if total == 0:
                print(f"  {cid:<10} {total:>9} {score:>7.1f} {'—':>7}  —  N/A")
            else:
                print(f"  {cid:<10} {total:>9} {score:>7.1f} {pct:>6.1f}%  {self._flag(pct)}")

    # ── ACTION 3: View Class Report ───────────────────────────
    def view_class_report(self):
        print("\n  ── Class Report ──")
        courses = data_store.load("courses.json")
        print("  Available courses:")
        for i, c in enumerate(courses, 1):
            print(f"    {i}. {c['course_id']} – {c['course_name']}")

        pick = input("  Select course: ").strip()
        if not pick.isdigit() or int(pick) < 1 or int(pick) > len(courses):
            print("  [!] Invalid selection.")
            return
        cid = courses[int(pick) - 1]["course_id"]

        students = data_store.load("students.json")
        enrolled = [s for s in students if cid in s["enrolled"]]
        if not enrolled:
            print("  [!] No students enrolled in that course.")
            return

        print(f"\n  Course: {cid}")
        print(f"  {'ID':<10} {'Name':<20} {'Sessions':>9} {'%':>7}  Status")
        print("  " + "─" * 58)
        for s in sorted(enrolled, key=lambda x: self._calc(x["student_id"], cid)[0]):
            pct, _, total = self._calc(s["student_id"], cid)
            if total == 0:
                print(f"  {s['student_id']:<10} {s['name']:<20} {total:>9} {'—':>7}  —  N/A")
            else:
                print(f"  {s['student_id']:<10} {s['name']:<20} {total:>9} {pct:>6.1f}%  {self._flag(pct)}")

    # ── ACTION 4: View At-Risk ────────────────────────────────
    def view_at_risk(self):
        print("\n  ── At-Risk Students (below 75%) ──")
        students = data_store.load("students.json")
        found = False
        print(f"  {'ID':<10} {'Name':<20} {'Course':<8} {'%':>7}  Level")
        print("  " + "─" * 55)
        for s in students:
            for cid in s["enrolled"]:
                pct, _, total = self._calc(s["student_id"], cid)
                if total > 0 and pct < 75:
                    lvl = "CRITICAL" if pct < 60 else "WARNING"
                    print(f"  {s['student_id']:<10} {s['name']:<20} {cid:<8} {pct:>6.1f}%  {lvl}")
                    found = True
        if not found:
            print("  [✓] No at-risk students at this time.")

    # ── ACTION 5: Simulate Day ────────────────────────────────
    def simulate_day(self):
        print("\n  ── Simulate Day ──")
        courses = data_store.load("courses.json")
        print("  Available courses:")
        for i, c in enumerate(courses, 1):
            print(f"    {i}. {c['course_id']} – {c['course_name']}")

        pick = input("  Select course: ").strip()
        if not pick.isdigit() or int(pick) < 1 or int(pick) > len(courses):
            print("  [!] Invalid selection.")
            return
        cid = courses[int(pick) - 1]["course_id"]

        students = data_store.load("students.json")
        enrolled = [s for s in students if cid in s["enrolled"]]
        if not enrolled:
            print("  [!] No students enrolled.")
            return

        records = data_store.load("attendance.json")
        today   = str(date.today())
        print(f"\n  Simulating {cid} on {today}...\n")

        for s in enrolled:
            status = random.choices(["P", "A", "L"], weights=[70, 20, 10])[0]
            records.append({
                "student_id": s["student_id"],
                "course_id":  cid,
                "date":       today,
                "status":     status,
            })
            label = {"P": "Present", "A": "Absent", "L": "Late"}[status]
            print(f"  {s['student_id']} ({s['name']:<18}) → {label}")

        data_store.save("attendance.json", records)

        print("\n  Rechecking thresholds...")
        for s in enrolled:
            self._evaluate(s["student_id"], cid)
        print("\n  [✓] Simulation complete.")

    # ── INTERNAL HELPERS ──────────────────────────────────────

    def _calc(self, sid, cid):
        """Calculate attendance percentage for a student in a course."""
        records = [r for r in data_store.load("attendance.json")
                   if r["student_id"] == sid and r["course_id"] == cid]
        total = len(records)
        score = sum(
            1.0 if r["status"] == "P" else
            0.5 if r["status"] == "L" else 0.0
            for r in records
        )
        pct = (score / total * 100) if total > 0 else 0.0
        return pct, score, total

    def _evaluate(self, sid, cid):
        """Check thresholds and send breach_event to Notification Agent if needed."""
        pct, _, total = self._calc(sid, cid)
        if total == 0:
            return
        if pct < 60:
            self.notifier.handle_breach(
                {"student_id": sid, "course_id": cid, "percentage": pct, "level": "CRITICAL"})
        elif pct < 75:
            self.notifier.handle_breach(
                {"student_id": sid, "course_id": cid, "percentage": pct, "level": "WARNING"})

    def _flag(self, pct):
        if pct < 60:  return "!! CRITICAL"
        if pct < 75:  return "⚠  WARNING"
        return               "✓  OK"

    def _invalid(self):
        print("  [!] Invalid option. Please try again.")

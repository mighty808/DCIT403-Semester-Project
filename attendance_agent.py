import random
from datetime import date

import data_store
from notification_agent import NotificationAgent
from reasoning_engine import BeliefModel, explain, parse_query, NLP_HELP_TEXT


class AttendanceAgent:
    """
    Intelligent Goal-Based Agent with:
      • Internal environment model (BeliefModel)
      • Trend analysis & prediction (linear extrapolation)
      • Explanation generation (human-readable reasoning)
      • Natural-language query interface
      • Proactive monitoring (autonomous threshold scanning)

    Percepts : user input (menu choice OR natural-language query)
    Actions  : mark, view, predict, explain, query, proactive scan
    Goals    : keep all students above 75 % attendance; early-warn on decline
    """

    def __init__(self):
        self.notifier = NotificationAgent()
        self.beliefs = BeliefModel()          # internal world model

    # ── PERCEIVE ──────────────────────────────────────────────
    def perceive(self):
        return input("\n  Enter choice: ").strip()

    # ── DECIDE (intelligent) ──────────────────────────────────
    def decide(self, choice):
        """
        Two-layer decision process:
          1. Check if input matches a menu number → mapped action.
          2. Otherwise treat input as a natural-language query
             and use the NLP parser to infer intent.
        """
        menu = {
            "1": self.mark_attendance,
            "2": self.view_student,
            "3": self.view_class_report,
            "4": self.view_at_risk,
            "5": self.simulate_day,
            "6": self.predict_at_risk,
            "7": self.ask_agent,
        }
        if choice in menu:
            return menu[choice]

        # Fallback: try to understand as natural language
        intent, params = parse_query(
            choice, list(self.beliefs.students.values())
        )
        if intent:
            return lambda: self._handle_nlp(intent, params)

        return self._invalid

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

        # Proactive: refresh world model and autonomously scan for issues
        self._refresh()
        self._evaluate(sid, cid)
        # Show intelligent explanation for this student
        profile = self.beliefs.get_profile(sid, cid)
        if profile:
            print()
            print(explain(profile, student['name']))

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

        # Proactive: refresh world model and run autonomous scan
        print("\n  Running intelligent analysis...")
        self.proactive_scan()
        print("\n  [✓] Simulation complete.")

    # ── ACTION 6: Predict At-Risk ─────────────────────────────
    def predict_at_risk(self):
        """
        Uses the reasoning engine's linear extrapolation to predict
        which students will fall below thresholds in upcoming sessions.
        This is PROACTIVE intelligence — warning before problems occur.
        """
        self._refresh()
        print("\n  ── Predictive Analysis (next 3 sessions) ──")
        print(f"  {'ID':<10} {'Name':<20} {'Course':<8} {'Now':>6} {'Pred':>6}  Alert")
        print("  " + "─" * 62)

        alerts_issued = False
        for profile in sorted(self.beliefs.all_profiles(),
                              key=lambda p: p.predicted_pct):
            if profile.total < 2:
                continue
            student = self.beliefs.students.get(profile.sid, {})
            name = student.get("name", profile.sid)
            now = profile.percentage
            pred = profile.predicted_pct

            # Only show students with a noteworthy prediction
            if pred < 75 or (now - pred) > 3:
                alert = ""
                if pred < 60:
                    alert = "⛔ PREDICTED CRITICAL"
                elif pred < 75:
                    alert = "⚠  PREDICTED WARNING"
                elif now - pred > 3:
                    alert = "📉 DECLINING"

                print(f"  {profile.sid:<10} {name:<20} {profile.cid:<8} "
                      f"{now:>5.1f}% {pred:>5.1f}%  {alert}")
                alerts_issued = True

        if not alerts_issued:
            print("  [✓] All students are predicted to remain above thresholds.")

    # ── ACTION 7: Natural-Language Query ──────────────────────
    def ask_agent(self):
        """Let the user ask a question in plain English."""
        print(NLP_HELP_TEXT)
        query = input("\n  Ask me anything: ").strip()
        if not query:
            return
        intent, params = parse_query(
            query, list(self.beliefs.students.values())
        )
        if intent:
            self._handle_nlp(intent, params)
        else:
            print("  [!] Sorry, I didn't understand that. Type 'help' for examples.")

    # ── NLP Intent Handler ────────────────────────────────────
    def _handle_nlp(self, intent, params):
        """Route a parsed NLP intent to the correct action."""
        self._refresh()

        if intent == "at_risk":
            self.view_at_risk()

        elif intent == "student_status":
            sid = params.get("student_id")
            if not sid:
                print(f"  [!] Could not find student '{params.get('raw', '?')}'.")
                return
            self._explain_student(sid)

        elif intent == "predict":
            sid = params.get("student_id")
            if not sid:
                print(f"  [!] Could not find student '{params.get('raw', '?')}'.")
                return
            self._predict_student(sid)

        elif intent == "explain":
            sid = params.get("student_id")
            if not sid:
                print(f"  [!] Could not find student '{params.get('raw', '?')}'.")
                return
            self._explain_student(sid)

        elif intent == "class_report":
            cid = params.get("course", "")
            if cid not in self.beliefs.courses:
                print(f"  [!] Unknown course '{cid}'.")
                return
            self.view_class_report_for(cid)

        elif intent == "trend_query":
            direction = params.get("direction", "declining")
            self._show_trend(direction)

        elif intent == "help":
            print(NLP_HELP_TEXT)

    # ── Explain one student across all courses ────────────────
    def _explain_student(self, sid):
        student = self.beliefs.students.get(sid, {})
        name = student.get("name", sid)
        print(f"\n  ── Intelligent Analysis: {name} ({sid}) ──\n")
        for cid in student.get("enrolled", []):
            profile = self.beliefs.get_profile(sid, cid)
            print(explain(profile, name))
            print()

    # ── Predict one student ───────────────────────────────────
    def _predict_student(self, sid):
        student = self.beliefs.students.get(sid, {})
        name = student.get("name", sid)
        print(f"\n  ── Prediction for {name} ({sid}) ──\n")
        for cid in student.get("enrolled", []):
            profile = self.beliefs.get_profile(sid, cid)
            if profile and profile.total >= 3:
                delta = profile.predicted_pct - profile.percentage
                arrow = "📈" if delta > 0 else "📉" if delta < 0 else "→"
                print(f"  {cid}: {profile.percentage:.1f}% now → "
                      f"{profile.predicted_pct:.1f}% predicted  {arrow}")
            elif profile:
                print(f"  {cid}: {profile.percentage:.1f}% (need ≥3 sessions to predict)")
            else:
                print(f"  {cid}: No data yet.")

    # ── Show students by trend direction ──────────────────────
    def _show_trend(self, direction):
        print(f"\n  ── Students with {direction.upper()} attendance ──\n")
        found = False
        for profile in self.beliefs.all_profiles():
            if profile.recent_trend == direction:
                student = self.beliefs.students.get(profile.sid, {})
                name = student.get("name", profile.sid)
                print(f"  {profile.sid} ({name}) in {profile.cid} — "
                      f"{profile.percentage:.1f}%  📉 declining" if direction == "declining"
                      else f"  {profile.sid} ({name}) in {profile.cid} — "
                      f"{profile.percentage:.1f}%  📈 improving")
                found = True
        if not found:
            print(f"  No students currently {direction}.")

    # ── Class report by course_id (for NLP) ───────────────────
    def view_class_report_for(self, cid):
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

    # ── PROACTIVE MONITORING ──────────────────────────────────
    def proactive_scan(self):
        """
        Autonomous behavior: scan ALL students for current AND predicted
        threshold breaches. Called automatically after data changes.
        This is what makes the agent *proactive* rather than purely reactive.
        """
        self._refresh()
        alerts = []
        for profile in self.beliefs.all_profiles():
            student = self.beliefs.students.get(profile.sid, {})
            name = student.get("name", profile.sid)

            # Current breach
            if profile.percentage < 60:
                self.notifier.handle_breach({
                    "student_id": profile.sid,
                    "course_id": profile.cid,
                    "percentage": profile.percentage,
                    "level": "CRITICAL",
                    "reason": explain(profile, name),
                })
            elif profile.percentage < 75:
                self.notifier.handle_breach({
                    "student_id": profile.sid,
                    "course_id": profile.cid,
                    "percentage": profile.percentage,
                    "level": "WARNING",
                    "reason": explain(profile, name),
                })

            # Predicted future breach (proactive early warning)
            if (profile.total >= 3 and
                    profile.predicted_pct < 75 and
                    profile.percentage >= 75):
                self.notifier.handle_predicted_breach({
                    "student_id": profile.sid,
                    "student_name": name,
                    "course_id": profile.cid,
                    "current_pct": profile.percentage,
                    "predicted_pct": profile.predicted_pct,
                    "trend": profile.recent_trend,
                })

    # ── INTERNAL HELPERS ──────────────────────────────────────

    def _refresh(self):
        """Refresh the agent's internal world model after any data change."""
        self.beliefs.refresh()

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

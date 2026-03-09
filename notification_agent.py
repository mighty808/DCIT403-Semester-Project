class NotificationAgent:
    """
    Simple Reflex Agent.
    Percept : breach_event  { student_id, course_id, percentage, level }
    Actions : issue_warning(), issue_critical()
    """

    def handle_breach(self, event):
        """Receive a breach_event and display the appropriate alert."""
        sid = event["student_id"]
        cid = event["course_id"]
        pct = event["percentage"]
        lvl = event["level"]

        print()
        if lvl == "CRITICAL":
            self.issue_critical(sid, cid, pct)
        else:
            self.issue_warning(sid, cid, pct)

    def issue_warning(self, sid, cid, pct):
        print("  ┌──────────────────────────────────────────┐")
        print(f"  │  WARNING  {sid} in {cid:<8}              │")
        print(f"  │  Attendance: {pct:.1f}%  (below 75%)         │")
        print("  └──────────────────────────────────────────┘")

    def issue_critical(self, sid, cid, pct):
        print("  ╔══════════════════════════════════════════╗")
        print(f"  ║  !! CRITICAL !!  {sid} in {cid:<8}        ║")
        print(f"  ║  Attendance: {pct:.1f}%  (below 60%)         ║")
        print("  ╚══════════════════════════════════════════╝")

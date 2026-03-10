class NotificationAgent:
    """
    Simple Reflex Agent with enhanced intelligence.
    Percept : breach_event  { student_id, course_id, percentage, level, reason? }
              predicted_breach_event { student_id, course_id, current_pct, predicted_pct, trend }
    Actions : issue_warning(), issue_critical(), issue_prediction_alert()

    Intelligence: responds to both current breaches AND predicted future
    breaches, enabling proactive intervention before problems worsen.
    """

    def handle_breach(self, event):
        """Receive a breach_event and display the appropriate alert."""
        sid = event["student_id"]
        cid = event["course_id"]
        pct = event["percentage"]
        lvl = event["level"]
        reason = event.get("reason", "")

        print()
        if lvl == "CRITICAL":
            self.issue_critical(sid, cid, pct, reason)
        else:
            self.issue_warning(sid, cid, pct, reason)

    def handle_predicted_breach(self, event):
        """Proactive alert: warn about a student predicted to breach thresholds."""
        self.issue_prediction_alert(event)

    def issue_warning(self, sid, cid, pct, reason=""):
        print("  ┌──────────────────────────────────────────┐")
        print(f"  │  WARNING  {sid} in {cid:<8}              │")
        print(f"  │  Attendance: {pct:.1f}%  (below 75%)         │")
        print("  └──────────────────────────────────────────┘")
        if reason:
            print(reason)

    def issue_critical(self, sid, cid, pct, reason=""):
        print("  ╔══════════════════════════════════════════╗")
        print(f"  ║  !! CRITICAL !!  {sid} in {cid:<8}        ║")
        print(f"  ║  Attendance: {pct:.1f}%  (below 60%)         ║")
        print("  ╚══════════════════════════════════════════╝")
        if reason:
            print(reason)

    def issue_prediction_alert(self, event):
        """Proactive alert — warns BEFORE a threshold is actually breached."""
        sid = event["student_id"]
        name = event.get("student_name", sid)
        cid = event["course_id"]
        cur = event["current_pct"]
        pred = event["predicted_pct"]
        trend = event.get("trend", "unknown")
        print("  ┌──────────────────────────────────────────────┐")
        print(f"  │  🔮 PREDICTED RISK  {name:<24}  │")
        print(f"  │  {cid}: {cur:.1f}% now → {pred:.1f}% predicted       │")
        print(f"  │  Trend: {trend:<36}│")
        print("  │  Early intervention recommended.             │")
        print("  └──────────────────────────────────────────────┘")

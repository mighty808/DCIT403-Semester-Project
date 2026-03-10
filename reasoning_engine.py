"""
Reasoning Engine – provides genuine intelligence to the Attendance Agent.

Capabilities:
  1. Belief Model    – maintains an internal representation of the environment
  2. Trend Analysis  – sliding-window analysis of recent attendance patterns
  3. Prediction      – forecasts future attendance % using linear regression
  4. Explanation      – generates human-readable reasoning for every flag
  5. NLP Query       – parses natural-language questions into structured actions
"""

import re
from datetime import date, timedelta, datetime
from collections import defaultdict

import data_store


# ── 1. BELIEF MODEL (Internal Environment Representation) ────────────

class BeliefModel:
    """
    The agent's internal model of the world, built from raw data.
    Keeps derived facts (percentages, streaks, trends) so the agent
    doesn't just read flat files — it *understands* the situation.
    """

    def __init__(self):
        self.students = {}       # sid -> student dict
        self.courses = {}        # cid -> course dict
        self.records = []        # all attendance records
        self.profiles = {}       # (sid, cid) -> StudentCourseProfile
        self.refresh()

    def refresh(self):
        """Re-derive beliefs from the data store."""
        self.students = {s["student_id"]: s for s in data_store.load("students.json")}
        self.courses = {c["course_id"]: c for c in data_store.load("courses.json")}
        self.records = data_store.load("attendance.json")
        self._build_profiles()

    def _build_profiles(self):
        """Build a rich profile for every (student, course) pair."""
        grouped = defaultdict(list)
        for r in self.records:
            key = (r["student_id"], r["course_id"])
            grouped[key].append(r)

        self.profiles = {}
        for (sid, cid), recs in grouped.items():
            sorted_recs = sorted(recs, key=lambda r: r["date"])
            self.profiles[(sid, cid)] = StudentCourseProfile(sid, cid, sorted_recs)

    def get_profile(self, sid, cid):
        return self.profiles.get((sid, cid))

    def all_profiles(self):
        return self.profiles.values()


class StudentCourseProfile:
    """Derived knowledge about one student's attendance in one course."""

    def __init__(self, sid, cid, sorted_records):
        self.sid = sid
        self.cid = cid
        self.records = sorted_records
        self.total = len(sorted_records)
        self.score = sum(
            1.0 if r["status"] in ("P", "Present") else
            0.5 if r["status"] in ("L", "Late") else 0.0
            for r in sorted_records
        )
        self.percentage = (self.score / self.total * 100) if self.total > 0 else 0.0
        self.streak = self._current_streak()
        self.recent_trend = self._recent_trend()
        self.predicted_pct = self._predict()

    # ── streak: how many consecutive absences at the tail ──
    def _current_streak(self):
        """Count consecutive absences/lates from most recent session."""
        streak = 0
        for r in reversed(self.records):
            if r["status"] in ("A", "Absent"):
                streak += 1
            else:
                break
        return streak

    # ── trend: compare first-half % vs second-half % ──
    def _recent_trend(self):
        """
        Returns a trend direction:
          'declining'  – recent performance worse than earlier
          'improving'  – recent performance better
          'stable'     – roughly the same (within 5 pp)
        """
        if self.total < 4:
            return "insufficient_data"
        mid = self.total // 2
        first_half = self.records[:mid]
        second_half = self.records[mid:]
        pct1 = self._pct_of(first_half)
        pct2 = self._pct_of(second_half)
        diff = pct2 - pct1
        if diff < -5:
            return "declining"
        if diff > 5:
            return "improving"
        return "stable"

    # ── prediction: simple linear regression on rolling window ──
    def _predict(self):
        """
        Predict what the attendance % will be after 3 more sessions,
        assuming the recent trend continues (linear extrapolation).
        """
        if self.total < 3:
            return self.percentage  # not enough data to predict

        # Use a rolling window of recent sessions (up to 5)
        window = self.records[-min(5, self.total):]
        scores = [
            1.0 if r["status"] in ("P", "Present") else
            0.5 if r["status"] in ("L", "Late") else 0.0
            for r in window
        ]
        n = len(scores)
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(scores) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, scores))
        denominator = sum((x - x_mean) ** 2 for x in xs)
        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        # Extrapolate 3 sessions into the future
        future_scores = [max(0, min(1, y_mean + slope * (n + i - x_mean))) for i in range(3)]
        combined_score = self.score + sum(future_scores)
        combined_total = self.total + 3
        return (combined_score / combined_total) * 100

    @staticmethod
    def _pct_of(records):
        if not records:
            return 0.0
        score = sum(
            1.0 if r["status"] in ("P", "Present") else
            0.5 if r["status"] in ("L", "Late") else 0.0
            for r in records
        )
        return score / len(records) * 100


# ── 2. EXPLANATION GENERATOR ─────────────────────────────────────────

def explain(profile, student_name=None):
    """
    Generate a human-readable explanation for a student's current
    attendance status, including reasoning about *why* they are flagged.
    """
    if profile is None or profile.total == 0:
        return "  No attendance data recorded yet."

    name = student_name or profile.sid
    lines = []

    # Current status
    pct = profile.percentage
    if pct < 60:
        lines.append(f"  !! {name} is in CRITICAL status ({pct:.1f}%) in {profile.cid}.")
    elif pct < 75:
        lines.append(f"  ⚠  {name} is at WARNING status ({pct:.1f}%) in {profile.cid}.")
    else:
        lines.append(f"  ✓  {name} is OK ({pct:.1f}%) in {profile.cid}.")

    # Reasoning: absences
    absences = sum(1 for r in profile.records if r["status"] in ("A", "Absent"))
    lates = sum(1 for r in profile.records if r["status"] in ("L", "Late"))
    lines.append(f"     Sessions: {profile.total} total | {absences} absent | {lates} late")

    # Reasoning: streak
    if profile.streak >= 2:
        lines.append(f"     ⚡ Consecutive absences: {profile.streak} (concerning pattern)")
    elif profile.streak == 1:
        lines.append(f"     → Missed the most recent session.")

    # Reasoning: trend
    trend = profile.recent_trend
    if trend == "declining":
        lines.append("     📉 Trend: DECLINING — recent attendance is worse than earlier sessions.")
    elif trend == "improving":
        lines.append("     📈 Trend: IMPROVING — recent attendance is better than earlier sessions.")
    elif trend == "stable":
        lines.append("     → Trend: Stable — attendance is consistent.")

    # Reasoning: prediction
    if profile.total >= 3:
        pred = profile.predicted_pct
        if pred < pct - 3:
            lines.append(f"     🔮 Prediction: likely to DROP to ~{pred:.1f}% if pattern continues.")
        elif pred > pct + 3:
            lines.append(f"     🔮 Prediction: likely to RISE to ~{pred:.1f}% if pattern continues.")
        else:
            lines.append(f"     🔮 Prediction: expected to stay around {pred:.1f}%.")

        # Actionable advice
        if pred < 60 and pct >= 60:
            lines.append("     ⛔ ACTION NEEDED: Student is predicted to fall into CRITICAL range!")
        elif pred < 75 and pct >= 75:
            lines.append("     ⚠  HEADS UP: Student is predicted to fall below the 75% threshold.")

    return "\n".join(lines)


# ── 3. NATURAL LANGUAGE QUERY PARSER ─────────────────────────────────

# Patterns the NLP parser can recognise
_PATTERNS = [
    # "who is at risk" / "at risk students" / "struggling students"
    (r"\b(at.risk|struggling|failing|danger|critical)\b", "at_risk", {}),
    # "how is Alice doing" / "status of 11110000"
    (r"\bhow\s+is\s+(.+?)\s+(doing|performing)\b", "student_status", {"name_or_id": 1}),
    (r"\bstatus\s+(?:of\s+)?(.+)", "student_status", {"name_or_id": 1}),
    # "predict 11110000" / "prediction for Alice"
    (r"\bpredict(?:ion)?\s+(?:for\s+)?(.+)", "predict", {"name_or_id": 1}),
    # "report for DCIT403" / "class report DCIT401"
    (r"\b(?:class\s+)?report\s+(?:for\s+)?(\w+)", "class_report", {"course": 1}),
    # "who is improving" / "who is declining"
    (r"\bwho\s+is\s+(improving|declining|getting\s+worse|getting\s+better)\b", "trend_query", {"direction": 1}),
    # "explain <student>"
    (r"\bexplain\s+(.+)", "explain", {"name_or_id": 1}),
    # help
    (r"\b(help|what can you do|commands)\b", "help", {}),
]


def parse_query(text, students):
    """
    Parse a natural-language query and return (intent, params) or None.
    `students` is a list of student dicts for name resolution.
    """
    text = text.strip().lower()

    for pattern, intent, groups in _PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            params = {}
            for key, group_idx in groups.items():
                val = m.group(group_idx).strip()
                # Try to resolve student name → id
                if key == "name_or_id":
                    resolved = _resolve_student(val, students)
                    if resolved:
                        params["student_id"] = resolved["student_id"]
                        params["student_name"] = resolved["name"]
                    else:
                        params["raw"] = val
                elif key == "direction":
                    if "worse" in val or "declin" in val:
                        params["direction"] = "declining"
                    else:
                        params["direction"] = "improving"
                elif key == "course":
                    params["course"] = val.upper()
                else:
                    params[key] = val
            return intent, params

    return None, {}


def _resolve_student(text, students):
    """Try to match text to a student by ID or partial name."""
    text_lower = text.lower().strip()
    # Exact ID match
    for s in students:
        if s["student_id"].lower() == text_lower:
            return s
    # Partial name match
    for s in students:
        if text_lower in s["name"].lower():
            return s
    return None


NLP_HELP_TEXT = """
  ┌─────────────────────────────────────────────────┐
  │  You can ask questions in plain English:         │
  │                                                  │
  │  • "Who is at risk?"                             │
  │  • "How is Alice doing?"                         │
  │  • "Status of 11110000"                          │
  │  • "Predict for Bob"                             │
  │  • "Who is declining?"                           │
  │  • "Who is improving?"                           │
  │  • "Explain Alice"                               │
  │  • "Report for DCIT403"                          │
  │  • "Help"                                        │
  └─────────────────────────────────────────────────┘"""

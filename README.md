# DCIT403 Semester Project

A multi-agent attendance tracking system built with SPADE (XMPP agents).

The project runs three agents:
1. AttendanceAgent: collects sign-ins and determines PRESENT/LATE/ABSENT.
2. NotificationAgent: sends attendance alerts and class-level warnings.
3. ReportAgent: generates and saves attendance summary reports.

## Features

1. Interactive terminal sign-in while the app is running.
2. Automatic attendance classification using class start time and late threshold.
3. Real-time notification output for absent and late students.
4. Report generation and persistence to a text file.
5. Fallback logging for notification/report processing errors.

## Project Structure

1. `main.py`: starts and stops all agents.
2. `attendance_agent.py`: handles sign-in input and attendance classification.
3. `notification_agent.py`: processes attendance alerts.
4. `report_agent.py`: generates and saves reports.
5. `attendance_report.txt`: saved attendance reports.
6. `notification_fallback.log`: notification processing error log.
7. `report_fallback.log`: report processing error log.

## Requirements

1. Python 3.10+ (3.12 recommended)
2. `spade` package
3. Working XMPP accounts for agents configured in the code

Install dependency:

```bash
python -m pip install spade
```

## Configuration

Agent JIDs and passwords are currently configured in `main.py`.

Course options are also configured in `main.py` under `COURSES`:
1. DCIT403 Intelligent Agent
2. DCIT401 SOCIAL, LEGAL, ETHICAL & PROFESSIONAL ISSUES

Example:

```python
notif  = NotificationAgent("notif_agent@xmpp.jp", "notif123")
report = ReportAgent("report_agent@xmpp.jp", "report")
attend = AttendanceAgent("attend_agent@xmpp.jp", "attend")
```

If authentication fails, update these values with valid XMPP credentials.

## How To Run

Start the project:

```bash
python main.py
```

When you run `main.py`:
1. Choose a course number (default is 1 for DCIT403 Intelligent Agent).
2. Enter student ID (example: `S001`, or just `1` for `S001`).
3. Enter student name (must match the selected course roster).
4. Check-in time is captured automatically using the current local time.
5. Press Enter on an empty student ID to finish input.

Then the system will:
1. Compute attendance status for all students.
2. Send notifications.
3. Print and save an attendance report.

## Sign-In Rules

1. Student must exist in the selected course roster.
2. Entered student name must match the student ID in the selected course roster.
3. If a student signs in, status is:
	1. PRESENT if on time.
	2. LATE if beyond `LATE_THRESHOLD` minutes after `CLASS_START`.
4. If a student does not sign in, status is ABSENT.

Defaults in `attendance_agent.py`:
1. `CLASS_START = "08:00"`
2. `LATE_THRESHOLD = 15`

## Sample Flow

1. App starts all agents.
2. You enter check-ins in terminal.
3. AttendanceAgent sends JSON attendance records to NotificationAgent and ReportAgent.
4. NotificationAgent prints per-student alerts and class attendance warning.
5. ReportAgent prints formatted summary and appends to `attendance_report.txt`.

## Troubleshooting

1. Import `spade` could not be resolved:
	1. Install package in the same Python interpreter used to run the app.
	2. Ensure your VS Code interpreter matches your runtime interpreter.
2. Could not authenticate agent:
	1. Check agent JID/password in `main.py`.
	2. Verify account exists on the XMPP server.
3. Connection errors:
	1. Verify network connectivity and XMPP server availability.
4. No report generated:
	1. Check `report_fallback.log` for processing failures.

## Notes

This is a learning/demo project. For production use, move credentials out of source code and load them from environment variables.
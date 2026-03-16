import spade
import asyncio
from datetime import datetime
from attendance_agent import AttendanceAgent
from notification_agent import NotificationAgent
from report_agent import ReportAgent

COURSES = {
    "1": {
        "code": "DCIT403",
        "name": "Intelligent Agent",
        "default_start": "07:30 AM",
        "students": {
            "11110000": "Alice",
            "11110001": "Bob",
            "11110002": "Carol",
            "11110003": "Dave",
        },
    },
    "2": {
        "code": "DCIT401",
        "name": "SOCIAL, LEGAL, ETHICAL & PROFESSIONAL ISSUES",
        "default_start": "09:00 AM",
        "students": {
            "11110000": "Alice",
            "11110001": "Bob",
            "11110002": "Carol",
            "11110003": "Dave",
        },
    },
}


async def choose_course():
    print("\nAvailable courses:")
    for option, course in COURSES.items():
        print(f"  {option}. {course['code']} {course['name']}")

    while True:
        choice = (await asyncio.to_thread(input, "Choose course number (default 1): ")).strip() or "1"
        if choice in COURSES:
            selected = COURSES[choice]
            print(f"\nSelected course: {selected['code']} {selected['name']}")
            return selected
        print("Invalid choice. Please choose one of:", ", ".join(COURSES.keys()))


async def choose_class_start_time(selected_course):
    default_start = selected_course.get("default_start", "08:00 AM")
    while True:
        raw_time = (await asyncio.to_thread(input, f"Class start time HH:MM AM/PM (default {default_start}): ")).strip()
        class_start = raw_time or default_start
        try:
            datetime.strptime(class_start.upper(), "%I:%M %p")
            return class_start
        except ValueError:
            print("Invalid time format. Use HH:MM AM/PM, e.g., 08:00 AM")

async def main():
    selected_course = await choose_course()
    class_start_time = await choose_class_start_time(selected_course)

    notif  = NotificationAgent("notif_agent@xmpp.jp", "notif123")
    report = ReportAgent("report_agent@xmpp.jp", "report")
    attend = AttendanceAgent("attend_agent@xmpp.jp", "attend")

    attend.course_code = selected_course["code"]
    attend.course_name = selected_course["name"]
    attend.course_students = selected_course["students"]
    attend.class_start_time = class_start_time

    await notif.start(auto_register=False)
    await report.start(auto_register=False)
    await asyncio.sleep(2)
    await attend.start(auto_register=False)

    print("\n🚀 All agents running...\n")
    await attend.process_complete.wait()

    await attend.stop()
    await notif.stop()
    await report.stop()
    print("\n🛑 All agents stopped.")

if __name__ == "__main__":
    spade.run(main())
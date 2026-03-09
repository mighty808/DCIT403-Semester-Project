import data_store
from attendance_agent import AttendanceAgent


def show_menu():
    print("""
  ┌─────────────────────────────────┐
  │  1. Mark Attendance             │
  │  2. View Student Attendance     │
  │  3. View Class Report           │
  │  4. View At-Risk Students       │
  │  5. Simulate Day                │
  │  6. Exit                        │
  └─────────────────────────────────┘""")


def main():
    data_store.seed()
    agent = AttendanceAgent()

    print("=" * 50)
    print("   ATTENDANCE TRACKER AGENT")
    print("   DCIT 403 – Intelligent Agent Project")
    print("=" * 50)

    while True:
        try:
            show_menu()
            choice = agent.perceive()

            if choice == "6":
                print("\n  Goodbye!\n")
                break

            action = agent.decide(choice)
            agent.act(action)
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!\n")
            break


if __name__ == "__main__":
    main()

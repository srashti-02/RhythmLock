
from database import get_connection


def clear_database():

    print("\nWARNING: This will permanently delete ALL Rhythmlock data.")
    confirmation = input('Type "DELETE ALL DATA" to continue: ')

    if confirmation != "DELETE ALL DATA":
        print("Operation cancelled.")
        return

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Delete child records first.
        cursor.execute("DELETE FROM keystrokes")
        cursor.execute("DELETE FROM typing_profiles")
        cursor.execute("DELETE FROM typing_samples")
        cursor.execute("DELETE FROM users")

        # Reset SQLite auto-increment counters.
        cursor.execute("""
            DELETE FROM sqlite_sequence
            WHERE name IN (
                'users',
                'typing_samples',
                'typing_profiles',
                'keystrokes'
            )
        """)

        connection.commit()

        print("\nAll old Rhythmlock data deleted successfully.")

    except Exception as error:
        connection.rollback()
        print("Database clearing failed:", error)

    finally:
        connection.close()


if __name__ == "__main__":
    clear_database()

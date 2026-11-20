
from database import get_connection


# ============================================================
# GET SAVED TYPING PROFILE
# ============================================================

def get_user_profile(user_id):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                user_id,
                average_dwell,
                average_flight,
                average_dwell_std,
                average_flight_std,
                average_duration,
                duration_std,
                sample_count,
                created_at,
                updated_at
            FROM typing_profiles
            WHERE user_id = ?
        """, (user_id,))

        profile = cursor.fetchone()

        return profile

    finally:

        connection.close()


# ============================================================
# VALIDATE SAVED PROFILE
# ============================================================

def validate_profile(profile):

    if profile is None:
        return False

    required_fields = [
        "user_id",
        "average_dwell",
        "average_flight",
        "average_dwell_std",
        "average_flight_std",
        "average_duration",
        "duration_std",
        "sample_count"
    ]

    for field in required_fields:

        if profile[field] is None:
            return False

    if profile["sample_count"] < 7:
        return False

    return True


# ============================================================
# DISPLAY SAVED TYPING PROFILE
# ============================================================

def display_profile(profile):

    print("\n========== SAVED TYPING PROFILE ==========")

    print(
        f"User ID: {profile['user_id']}"
    )

    print(
        f"Average Dwell Time: "
        f"{profile['average_dwell']:.2f} ms"
    )

    print(
        f"Average Flight Time: "
        f"{profile['average_flight']:.2f} ms"
    )

    print(
        f"Dwell Variation: "
        f"{profile['average_dwell_std']:.2f} ms"
    )

    print(
        f"Flight Variation: "
        f"{profile['average_flight_std']:.2f} ms"
    )

    print(
        f"Average Typing Duration: "
        f"{profile['average_duration']:.2f} ms"
    )

    print(
        f"Duration Variation: "
        f"{profile['duration_std']:.2f} ms"
    )

    print(
        f"Samples Used: "
        f"{profile['sample_count']}"
    )

    print(
        f"Created At: "
        f"{profile['created_at']}"
    )

    print(
        f"Updated At: "
        f"{profile['updated_at']}"
    )


# ============================================================
# TEST / COMMAND LINE
# ============================================================

if __name__ == "__main__":

    user_id = 1

    try:

        profile = get_user_profile(user_id)

        if profile is None:

            print("\nNo typing profile found.")

        elif not validate_profile(profile):

            print("\nTyping profile is incomplete or invalid.")

        else:

            display_profile(profile)

            print(
                "\nProfile verification successful!"
            )

    except Exception as error:

        print(
            "\nError while retrieving profile:",
            error
        )

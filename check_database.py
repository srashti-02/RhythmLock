
from database import get_connection


# ============================================================
# PRINT TABLE
# ============================================================

def print_table(title, headers, rows):

    print("\n" + "=" * 130)
    print(title.center(130))
    print("=" * 130)

    if not rows:
        print("No records found.".center(130))
        print("=" * 130)
        return

    widths = []

    for index, header in enumerate(headers):

        column_values = [
            str(row[index]) if row[index] is not None else "-"
            for row in rows
        ]

        width = max(
            len(str(header)),
            max(len(value) for value in column_values)
        )

        widths.append(width)

    header_line = " | ".join(
        str(header).ljust(widths[index])
        for index, header in enumerate(headers)
    )

    print(header_line)
    print("-" * len(header_line))

    for row in rows:

        print(
            " | ".join(
                str(value if value is not None else "-").ljust(
                    widths[index]
                )
                for index, value in enumerate(row)
            )
        )

    print("=" * 130)


# ============================================================
# SAFE NUMBER FORMATTING
# ============================================================

def format_number(value):

    if value is None:
        return "-"

    return f"{value:.2f}"


# ============================================================
# CHECK DATABASE
# ============================================================

def check_database():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        print("\n")
        print("=" * 130)
        print("RHYTHMLOCK DATABASE REPORT".center(130))
        print("=" * 130)


        # ====================================================
        # 1. REGISTERED USERS
        # ====================================================

        cursor.execute("""
            SELECT
                u.id,
                u.username,
                u.email,
                COUNT(DISTINCT ts.id) AS total_samples,

                CASE
                    WHEN tp.user_id IS NOT NULL
                    THEN 'Created'
                    ELSE 'Not Created'
                END AS profile_status

            FROM users u

            LEFT JOIN typing_samples ts
                ON u.id = ts.user_id

            LEFT JOIN typing_profiles tp
                ON u.id = tp.user_id

            GROUP BY
                u.id,
                u.username,
                u.email,
                tp.user_id

            ORDER BY u.id
        """)

        users = cursor.fetchall()

        user_rows = [
            (
                row["id"],
                row["username"],
                row["email"],
                row["total_samples"],
                row["profile_status"]
            )
            for row in users
        ]

        print_table(
            "1. REGISTERED USERS",
            [
                "User ID",
                "Username",
                "Email",
                "Total Samples",
                "Profile Status"
            ],
            user_rows
        )


        # ====================================================
        # 2. TYPING SAMPLES
        # ====================================================

        cursor.execute("""
            SELECT
                ts.id,
                ts.user_id,
                u.username,
                ts.sample_number,
                ts.phrase,
                ts.language,
                COUNT(k.id) AS total_keystrokes,
                ts.created_at

            FROM typing_samples ts

            JOIN users u
                ON ts.user_id = u.id

            LEFT JOIN keystrokes k
                ON ts.id = k.sample_id

            GROUP BY
                ts.id,
                ts.user_id,
                u.username,
                ts.sample_number,
                ts.phrase,
                ts.language,
                ts.created_at

            ORDER BY
                ts.user_id,
                ts.sample_number
        """)

        samples = cursor.fetchall()

        sample_rows = [
            (
                row["id"],
                row["user_id"],
                row["username"],
                row["sample_number"],
                row["phrase"],
                row["language"],
                row["total_keystrokes"],
                row["created_at"]
            )
            for row in samples
        ]

        print_table(
            "2. TYPING SAMPLES",
            [
                "Sample ID",
                "User ID",
                "Username",
                "Sample No.",
                "Phrase",
                "Language",
                "Keystrokes",
                "Created At"
            ],
            sample_rows
        )


        # ====================================================
        # 3. INDIVIDUAL KEYSTROKES
        # ====================================================

        cursor.execute("""
            SELECT
                k.sample_id,
                ts.user_id,
                u.username,
                k.sequence_number,
                k.key_label,
                k.dwell_time,
                k.flight_time

            FROM keystrokes k

            JOIN typing_samples ts
                ON k.sample_id = ts.id

            JOIN users u
                ON ts.user_id = u.id

            ORDER BY
                ts.user_id,
                k.sample_id,
                k.sequence_number
        """)

        keystrokes = cursor.fetchall()

        keystroke_rows = [
            (
                row["sample_id"],
                row["user_id"],
                row["username"],
                row["sequence_number"],
                row["key_label"],
                format_number(row["dwell_time"]),
                format_number(row["flight_time"])
            )
            for row in keystrokes
        ]

        print_table(
            "3. INDIVIDUAL KEYSTROKES",
            [
                "Sample ID",
                "User ID",
                "Username",
                "Sequence",
                "Key",
                "Dwell (ms)",
                "Flight (ms)"
            ],
            keystroke_rows
        )


        # ====================================================
        # 4. TYPING PROFILES / BASELINE
        # ====================================================

        cursor.execute("""
            SELECT
                tp.user_id,
                u.username,
                tp.sample_count,
                tp.average_dwell,
                tp.average_flight,
                tp.average_dwell_std,
                tp.average_flight_std,
                tp.average_duration,
                tp.duration_std,
                tp.updated_at

            FROM typing_profiles tp

            JOIN users u
                ON tp.user_id = u.id

            ORDER BY tp.user_id
        """)

        profiles = cursor.fetchall()

        profile_rows = [
            (
                row["user_id"],
                row["username"],
                row["sample_count"],
                format_number(row["average_dwell"]),
                format_number(row["average_flight"]),
                format_number(row["average_dwell_std"]),
                format_number(row["average_flight_std"]),
                format_number(row["average_duration"]),
                format_number(row["duration_std"]),
                row["updated_at"]
            )
            for row in profiles
        ]

        print_table(
            "4. TYPING PROFILES / BASELINE",
            [
                "User ID",
                "Username",
                "Samples",
                "Avg Dwell",
                "Avg Flight",
                "Dwell Std",
                "Flight Std",
                "Avg Duration",
                "Duration Std",
                "Updated At"
            ],
            profile_rows
        )


        # ====================================================
        # 5. DATABASE SUMMARY
        # ====================================================

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM typing_samples")
        total_samples = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM keystrokes")
        total_keystrokes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM typing_profiles")
        total_profiles = cursor.fetchone()[0]

        print("\n")
        print("=" * 65)
        print("DATABASE SUMMARY".center(65))
        print("=" * 65)

        print(f"Total Users          : {total_users}")
        print(f"Total Typing Samples : {total_samples}")
        print(f"Total Keystrokes     : {total_keystrokes}")
        print(f"Total Profiles       : {total_profiles}")

        print("=" * 65)
        print("\nDATABASE CHECK COMPLETED SUCCESSFULLY.\n")


    finally:

        connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    check_database()

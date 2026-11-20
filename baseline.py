
from database import get_connection
from feature_extraction import (
    get_user_sample_ids,
    extract_sample_features
)
from statistics import mean, stdev


# ============================================================
# BASELINE CONFIGURATION
# ============================================================

REQUIRED_SAMPLES = 7


# ============================================================
# BUILD TYPING BASELINE
# ============================================================

def build_baseline(user_id):

    # --------------------------------------------------------
    # Step 1: Get user's sample IDs
    # --------------------------------------------------------

    sample_ids = get_user_sample_ids(user_id)

    if len(sample_ids) < REQUIRED_SAMPLES:

        print(
            f"Not enough samples. "
            f"Required: {REQUIRED_SAMPLES}, "
            f"Available: {len(sample_ids)}"
        )

        return None

    # --------------------------------------------------------
    # Step 2: Use only the first 7 enrollment samples
    # --------------------------------------------------------

    enrollment_sample_ids = sample_ids[:REQUIRED_SAMPLES]

    all_features = []

    for sample_id in enrollment_sample_ids:

        features = extract_sample_features(sample_id)

        if features is None:

            print(
                f"Invalid sample detected: {sample_id}"
            )

            return None

        all_features.append(features)

    # --------------------------------------------------------
    # Step 3: Extract feature values
    # --------------------------------------------------------

    dwell_values = [
        feature["average_dwell_time"]
        for feature in all_features
    ]

    flight_values = [
        feature["average_flight_time"]
        for feature in all_features
    ]

    dwell_std_values = [
        feature["dwell_std"]
        for feature in all_features
    ]

    flight_std_values = [
        feature["flight_std"]
        for feature in all_features
    ]

    duration_values = [
        feature["total_typing_duration"]
        for feature in all_features
    ]

    # --------------------------------------------------------
    # Step 4: Calculate baseline averages
    # --------------------------------------------------------

    average_dwell = mean(dwell_values)

    average_flight = mean(flight_values)

    average_dwell_std = mean(dwell_std_values)

    average_flight_std = mean(flight_std_values)

    average_duration = mean(duration_values)

    # --------------------------------------------------------
    # Step 5: Calculate variation
    # --------------------------------------------------------

    dwell_variation = stdev(dwell_values)

    flight_variation = stdev(flight_values)

    duration_variation = stdev(duration_values)

    # --------------------------------------------------------
    # Step 6: Save / update typing profile
    # --------------------------------------------------------

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO typing_profiles
            (
                user_id,
                average_dwell,
                average_flight,
                average_dwell_std,
                average_flight_std,
                average_duration,
                duration_std,
                sample_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET

                average_dwell =
                    excluded.average_dwell,

                average_flight =
                    excluded.average_flight,

                average_dwell_std =
                    excluded.average_dwell_std,

                average_flight_std =
                    excluded.average_flight_std,

                average_duration =
                    excluded.average_duration,

                duration_std =
                    excluded.duration_std,

                sample_count =
                    excluded.sample_count,

                updated_at =
                    CURRENT_TIMESTAMP
        """, (
            user_id,
            average_dwell,
            average_flight,
            average_dwell_std,
            average_flight_std,
            average_duration,
            duration_variation,
            len(all_features)
        ))

        connection.commit()

        # ----------------------------------------------------
        # Step 7: Return baseline information
        # ----------------------------------------------------

        return {
            "user_id": user_id,
            "sample_count": len(all_features),
            "sample_ids": enrollment_sample_ids,
            "average_dwell": average_dwell,
            "average_flight": average_flight,
            "average_dwell_std": average_dwell_std,
            "average_flight_std": average_flight_std,
            "average_duration": average_duration,
            "duration_std": duration_variation
        }

    except Exception as error:

        connection.rollback()

        print("Baseline error:", error)

        raise

    finally:

        connection.close()


# ============================================================
# TEST / COMMAND LINE
# ============================================================

if __name__ == "__main__":

    # User 1 has 9 samples.
    # First 7 will be used for baseline.
    # Samples 8 and 9 remain reserved for genuine testing.

    user_id = 1

    profile = build_baseline(user_id)

    if profile is None:

        print("\nCould not create typing baseline.")

    else:

        print("\n========== TYPING BASELINE ==========")

        print(
            f"User ID: {profile['user_id']}"
        )

        print(
            f"Samples Used: {profile['sample_count']}"
        )

        print(
            f"Sample IDs: {profile['sample_ids']}"
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
            f"Average Dwell Variation: "
            f"{profile['average_dwell_std']:.2f} ms"
        )

        print(
            f"Average Flight Variation: "
            f"{profile['average_flight_std']:.2f} ms"
        )

        print(
            f"Average Typing Duration: "
            f"{profile['average_duration']:.2f} ms"
        )

        print(
            f"Typing Duration Variation: "
            f"{profile['duration_std']:.2f} ms"
        )

        print(
            "\nTyping profile created successfully!"
        )

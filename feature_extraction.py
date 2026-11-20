
from database import get_connection
from statistics import mean, stdev
import math


# ============================================================
# VALIDATE AND CONVERT TIMING VALUES
# ============================================================

def is_valid_timing(value):

    if value is None:
        return False

    try:
        number = float(value)

        return (
            math.isfinite(number)
            and number >= 0
        )

    except (TypeError, ValueError):
        return False


# ============================================================
# COMMON FEATURE CALCULATION
# ============================================================

def calculate_features(
    dwell_times,
    flight_times,
    total_keystrokes
):

    if not dwell_times or not flight_times:
        return None

    average_dwell = mean(dwell_times)

    average_flight = mean(flight_times)

    dwell_std = (
        stdev(dwell_times)
        if len(dwell_times) > 1
        else 0.0
    )

    flight_std = (
        stdev(flight_times)
        if len(flight_times) > 1
        else 0.0
    )

    # Approximate typing duration
    total_typing_duration = (
        sum(dwell_times) + sum(flight_times)
    )

    return {
        "total_keystrokes": total_keystrokes,
        "average_dwell_time": average_dwell,
        "average_flight_time": average_flight,
        "dwell_std": dwell_std,
        "flight_std": flight_std,
        "total_typing_duration": total_typing_duration
    }


# ============================================================
# EXTRACT FEATURES FROM A SAVED DATABASE SAMPLE
# ============================================================

def extract_sample_features(sample_id):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                sequence_number,
                key_label,
                dwell_time,
                flight_time
            FROM keystrokes
            WHERE sample_id = ?
            ORDER BY sequence_number
        """, (sample_id,))

        keystrokes = cursor.fetchall()

    finally:
        connection.close()

    if not keystrokes:
        return None

    dwell_times = []
    flight_times = []

    for key in keystrokes:

        dwell = key["dwell_time"]
        flight = key["flight_time"]

        if not is_valid_timing(dwell):
            return None

        dwell_times.append(float(dwell))

        if flight is not None:

            if not is_valid_timing(flight):
                return None

            flight_times.append(float(flight))

    features = calculate_features(
        dwell_times,
        flight_times,
        len(keystrokes)
    )

    if features is None:
        return None

    features["sample_id"] = sample_id

    return features


# ============================================================
# GET ALL SAMPLE IDs FOR A USER
# ============================================================

def get_user_sample_ids(user_id):

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id
            FROM typing_samples
            WHERE user_id = ?
            ORDER BY sample_number
        """, (user_id,))

        rows = cursor.fetchall()

        return [
            row["id"]
            for row in rows
        ]

    finally:
        connection.close()


# ============================================================
# EXTRACT FEATURES FROM A FRESH VERIFICATION SAMPLE
#
# This sample does not need to be saved in the database.
# ============================================================

def extract_features_from_keystrokes(keystrokes):

    if not isinstance(keystrokes, list) or not keystrokes:
        return None

    dwell_times = []
    flight_times = []

    for key in keystrokes:

        if not isinstance(key, dict):
            return None

        dwell = key.get("dwellTime")
        flight = key.get("flightTime")

        if not is_valid_timing(dwell):
            return None

        dwell_times.append(float(dwell))

        if flight is not None:

            if not is_valid_timing(flight):
                return None

            flight_times.append(float(flight))

    return calculate_features(
        dwell_times,
        flight_times,
        len(keystrokes)
    )


# ============================================================
# TEST DATABASE FEATURE EXTRACTION
# ============================================================

if __name__ == "__main__":

    user_id = 1

    sample_ids = get_user_sample_ids(user_id)

    print("\n========== ALL SAMPLE FEATURES ==========")

    for sample_id in sample_ids:

        features = extract_sample_features(sample_id)

        if features is None:

            print(f"\nSample {sample_id}: Invalid or incomplete data")
            continue

        print(f"\n--- Sample {features['sample_id']} ---")

        print(
            f"Keystrokes: "
            f"{features['total_keystrokes']}"
        )

        print(
            f"Average Dwell: "
            f"{features['average_dwell_time']:.2f} ms"
        )

        print(
            f"Average Flight: "
            f"{features['average_flight_time']:.2f} ms"
        )

        print(
            f"Dwell Std: "
            f"{features['dwell_std']:.2f} ms"
        )

        print(
            f"Flight Std: "
            f"{features['flight_std']:.2f} ms"
        )

        print(
            f"Total Duration: "
            f"{features['total_typing_duration']:.2f} ms"
        )

    print(f"\nTotal samples found: {len(sample_ids)}")

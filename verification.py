
from database import get_connection

from feature_extraction import (
    extract_sample_features
)

import math


# ============================================================
# GET SAVED USER PROFILE
# ============================================================

def get_saved_profile(user_id):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                average_dwell,
                average_flight,
                average_dwell_std,
                average_flight_std,
                average_duration,
                duration_std,
                sample_count
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

    numeric_fields = required_fields[:-1]

    for field in numeric_fields:

        try:
            value = float(profile[field])

        except (TypeError, ValueError):
            return False

        if not math.isfinite(value) or value < 0:
            return False

    return True


# ============================================================
# VALIDATE NEW SAMPLE FEATURES
# ============================================================

def validate_sample_features(sample_features):

    if not isinstance(sample_features, dict):
        return False

    required_fields = [
        "average_dwell_time",
        "average_flight_time",
        "dwell_std",
        "flight_std",
        "total_typing_duration"
    ]

    for field in required_fields:

        if field not in sample_features:
            return False

        try:
            value = float(sample_features[field])

        except (TypeError, ValueError):
            return False

        if not math.isfinite(value) or value < 0:
            return False

    return True


# ============================================================
# CALCULATE NORMALIZED DISTANCE
# ============================================================

def calculate_distance(value, baseline):

    value = float(value)

    baseline = float(baseline)

    # A 1 ms denominator floor prevents division by zero
    # and unstable distances for very small baselines.

    denominator = max(abs(baseline), 1.0)

    distance = (
        abs(value - baseline) / denominator
    )

    return distance


# ============================================================
# COMPARE SAMPLE WITH SAVED PROFILE
# ============================================================

def compare_with_profile(
    user_id,
    sample_features
):

    # Step 1: Validate new sample

    if not validate_sample_features(sample_features):
        return None

    # Step 2: Retrieve saved baseline

    profile = get_saved_profile(user_id)

    if not validate_profile(profile):
        return None

    # Step 3: Calculate individual feature distances

    dwell_distance = calculate_distance(
        sample_features["average_dwell_time"],
        profile["average_dwell"]
    )

    flight_distance = calculate_distance(
        sample_features["average_flight_time"],
        profile["average_flight"]
    )

    dwell_std_distance = calculate_distance(
        sample_features["dwell_std"],
        profile["average_dwell_std"]
    )

    flight_std_distance = calculate_distance(
        sample_features["flight_std"],
        profile["average_flight_std"]
    )

    duration_distance = calculate_distance(
        sample_features["total_typing_duration"],
        profile["average_duration"]
    )

    # Step 4: Calculate overall distance
    # All five features currently have equal weight.

    total_distance = (
        dwell_distance
        + flight_distance
        + dwell_std_distance
        + flight_std_distance
        + duration_distance
    ) / 5

    # Step 5: Return comparison results

    return {

        "dwell_distance":
            dwell_distance,

        "flight_distance":
            flight_distance,

        "dwell_std_distance":
            dwell_std_distance,

        "flight_std_distance":
            flight_std_distance,

        "duration_distance":
            duration_distance,

        "total_distance":
            total_distance
    }


# ============================================================
# TEST VERIFICATION
# ============================================================

if __name__ == "__main__":

    user_id = 1

    # Sample 8 is reserved for genuine testing.
    # It is not included in the first 7 baseline samples.

    test_sample_id = 8

    sample_features = extract_sample_features(
        test_sample_id
    )

    if sample_features is None:

        print(
            "Could not extract test sample features."
        )

    else:

        result = compare_with_profile(
            user_id,
            sample_features
        )

        if result is None:

            print(
                "Profile or sample features are invalid."
            )

        else:

            print(
                "\n========== VERIFICATION TEST =========="
            )

            print(
                f"User ID: {user_id}"
            )

            print(
                f"Test Sample ID: {test_sample_id}"
            )

            print(
                "\n--- Test Sample Features ---"
            )

            print(
                f"Average Dwell: "
                f"{sample_features['average_dwell_time']:.2f} ms"
            )

            print(
                f"Average Flight: "
                f"{sample_features['average_flight_time']:.2f} ms"
            )

            print(
                f"Dwell Std: "
                f"{sample_features['dwell_std']:.2f} ms"
            )

            print(
                f"Flight Std: "
                f"{sample_features['flight_std']:.2f} ms"
            )

            print(
                f"Total Duration: "
                f"{sample_features['total_typing_duration']:.2f} ms"
            )

            print(
                "\n--- Feature Distances ---"
            )

            print(
                f"Dwell Distance: "
                f"{result['dwell_distance']:.4f}"
            )

            print(
                f"Flight Distance: "
                f"{result['flight_distance']:.4f}"
            )

            print(
                f"Dwell Std Distance: "
                f"{result['dwell_std_distance']:.4f}"
            )

            print(
                f"Flight Std Distance: "
                f"{result['flight_std_distance']:.4f}"
            )

            print(
                f"Duration Distance: "
                f"{result['duration_distance']:.4f}"
            )

            print(
                "\nOverall Distance: "
                f"{result['total_distance']:.4f}"
            )

            print(
                "\nComparison completed successfully!"
            )

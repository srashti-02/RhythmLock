
from verification import (
    compare_with_profile,
    get_saved_profile,
    validate_profile
)

from feature_extraction import (
    extract_sample_features,
    get_user_sample_ids
)


# ============================================================
# EVALUATION CONFIGURATION
# ============================================================

USER_ID = 1

# First 7 samples are used for baseline.
# Samples 8 and 9 are reserved for genuine testing.

BASELINE_SAMPLE_COUNT = 7

TEST_SAMPLE_IDS = [8, 9]


# ============================================================
# VALIDATE EVALUATION CONFIGURATION
# ============================================================

def validate_evaluation_samples():

    all_sample_ids = get_user_sample_ids(USER_ID)

    baseline_sample_ids = all_sample_ids[
        :BASELINE_SAMPLE_COUNT
    ]

    if len(baseline_sample_ids) < BASELINE_SAMPLE_COUNT:

        print("\nNot enough enrollment samples.")

        return False

    for sample_id in TEST_SAMPLE_IDS:

        if sample_id in baseline_sample_ids:

            print(
                f"\nError: Sample {sample_id} "
                "is being used in both baseline and testing."
            )

            return False

        if sample_id not in all_sample_ids:

            print(
                f"\nError: Sample {sample_id} "
                "does not belong to this user."
            )

            return False

    return True


# ============================================================
# EVALUATE GENUINE USER SAMPLES
# ============================================================

def evaluate_genuine_samples():

    print(
        "\n========== AUTHENTICATION EVALUATION =========="
    )

    print(f"User ID: {USER_ID}")

    print(
        f"Baseline Samples: "
        f"{BASELINE_SAMPLE_COUNT}"
    )

    print(
        f"Genuine Test Samples: "
        f"{TEST_SAMPLE_IDS}"
    )

    # --------------------------------------------------------
    # Step 1: Validate saved profile
    # --------------------------------------------------------

    profile = get_saved_profile(USER_ID)

    if not validate_profile(profile):

        print("\nNo valid typing profile found.")

        return

    # --------------------------------------------------------
    # Step 2: Validate testing samples
    # --------------------------------------------------------

    if not validate_evaluation_samples():

        print("\nEvaluation stopped.")

        return

    # --------------------------------------------------------
    # Step 3: Calculate genuine scores
    # --------------------------------------------------------

    scores = []

    for sample_id in TEST_SAMPLE_IDS:

        sample_features = extract_sample_features(
            sample_id
        )

        if sample_features is None:

            print(
                f"\nSample {sample_id}: "
                "Could not extract features."
            )

            continue

        result = compare_with_profile(
            USER_ID,
            sample_features
        )

        if result is None:

            print(
                "\nCould not compare sample with profile."
            )

            return

        score = result["total_distance"]

        scores.append(score)

        print(
            f"\n--- Genuine Sample {sample_id} ---"
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
            f"Overall Distance: {score:.4f}"
        )

    # --------------------------------------------------------
    # Step 4: Calculate genuine statistics
    # --------------------------------------------------------

    if not scores:

        print("\nNo genuine scores available.")

        return

    minimum = min(scores)

    maximum = max(scores)

    average = sum(scores) / len(scores)

    print(
        "\n========== GENUINE USER STATISTICS =========="
    )

    print(
        f"Number of genuine test samples: {len(scores)}"
    )

    print(
        f"Minimum Score: {minimum:.4f}"
    )

    print(
        f"Maximum Score: {maximum:.4f}"
    )

    print(
        f"Average Score: {average:.4f}"
    )

    print(
        "\nGenuine evaluation completed successfully!"
    )

    print(
        "\nNote: These scores are experimental results."
    )

    print(
        "No authentication threshold has been applied."
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    evaluate_genuine_samples()

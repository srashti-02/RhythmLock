
import os
import math
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

from database import get_connection

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from baseline import build_baseline
from feature_extraction import extract_features_from_keystrokes
from verification import compare_with_profile



# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)

APP_ENV = os.getenv("APP_ENV", "development")
IS_PRODUCTION = APP_ENV == "production"

SECRET_KEY = os.getenv("SECRET_KEY")

if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is required in production."
    )

app.config["SECRET_KEY"] = (
    SECRET_KEY or "rhythmlock-development-secret-key"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION

TOTAL_ENROLLMENT_SAMPLES = 7

VERIFICATION_PHRASE = "my secure login"

# Provisional threshold; requires genuine and impostor testing.
BEHAVIORAL_DISTANCE_THRESHOLD = float(
    os.getenv("BEHAVIORAL_DISTANCE_THRESHOLD", "0.35")
)



# ============================================================
# HELPER: JSON ERROR RESPONSE
# ============================================================

def error_response(message, status_code=400):

    return jsonify({
        "success": False,
        "message": message
    }), status_code


# ============================================================
# HELPER: USER STATUS
# ============================================================

def get_user_status(user_id):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) AS sample_count
            FROM typing_samples
            WHERE user_id = ?
        """, (user_id,))

        sample_count = cursor.fetchone()["sample_count"]

        cursor.execute("""
            SELECT user_id
            FROM typing_profiles
            WHERE user_id = ?
        """, (user_id,))

        profile = cursor.fetchone()

        return {
            "sample_count": sample_count,
            "profile_created": profile is not None
        }

    finally:

        connection.close()


# ============================================================
# HELPER: VALIDATE KEYSTROKE DATA
# ============================================================

def validate_keystrokes(phrase, keystrokes):

    if not isinstance(phrase, str) or not phrase.strip():
        return "A valid typing phrase is required."

    if not isinstance(keystrokes, list) or not keystrokes:
        return "Keystroke data is required."

    if len(keystrokes) != len(phrase):
        return "Keystroke count does not match the typing phrase."

    for position, key_data in enumerate(keystrokes, start=1):

        if not isinstance(key_data, dict):
            return "Invalid keystroke data."

        required_fields = (
            "index",
            "key",
            "dwellTime",
            "flightTime"
        )

        if not all(field in key_data for field in required_fields):
            return "Incomplete keystroke information."

        if key_data["index"] != position:
            return "Invalid keystroke sequence."

        key_label = key_data["key"]

        if not isinstance(key_label, str) or len(key_label) != 1:
            return "Invalid key label."

        if key_label != phrase[position - 1]:
            return "Recorded key does not match the typing phrase."

        dwell_time = key_data["dwellTime"]

        if (
            isinstance(dwell_time, bool)
            or not isinstance(dwell_time, (int, float))
            or not math.isfinite(dwell_time)
            or dwell_time < 0
        ):
            return "Invalid dwell time."

        flight_time = key_data["flightTime"]

        if position == 1:

            if flight_time is not None:
                return "First keystroke must have a null flight time."

        else:

            if (
                isinstance(flight_time, bool)
                or not isinstance(flight_time, (int, float))
                or not math.isfinite(flight_time)
                or flight_time < 0
            ):
                return "Invalid flight time."

    return None


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    if "user_id" in session:

        status = get_user_status(session["user_id"])

        if status["profile_created"]:
            return redirect(url_for("dashboard"))

        return redirect(url_for("keystroke_test"))

    return render_template("index.html")


# ============================================================
# REGISTRATION PAGE
# ============================================================

@app.route("/register-page")
def register_page():

    if "user_id" in session:

        status = get_user_status(session["user_id"])

        if status["profile_created"]:
            return redirect(url_for("dashboard"))

        return redirect(url_for("keystroke_test"))

    return render_template("register.html")


# ============================================================
# LOGIN PAGE
# ============================================================

@app.route("/login-page")
def login_page():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if "pending_user_id" in session:
        session.pop("pending_user_id", None)
        session.pop("pending_username", None)

    return render_template("login.html")


# ============================================================
# KEYSTROKE ENROLLMENT PAGE
# ============================================================

@app.route("/keystroke-test")
def keystroke_test():

    if "user_id" not in session:
        return redirect(url_for("login_page"))

    status = get_user_status(session["user_id"])

    if status["profile_created"]:
        return redirect(url_for("dashboard"))

    return render_template("keystroke_test.html")


# ============================================================
# DASHBOARD PAGE
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login_page"))

    status = get_user_status(session["user_id"])

    if not status["profile_created"]:
        return redirect(url_for("keystroke_test"))

    return render_template(
        "dashboard.html",
        username=session["username"],
        sample_count=status["sample_count"]
    )


# ============================================================
# USER REGISTRATION API
# ============================================================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("Invalid request data.")

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not isinstance(username, str):
        return error_response("Username is required.")

    if not isinstance(email, str):
        return error_response("Email is required.")

    if not isinstance(password, str):
        return error_response("Password is required.")

    username = username.strip()
    email = email.strip().lower()

    if not username:
        return error_response("Username is required.")

    if not email or "@" not in email:
        return error_response("Enter a valid email address.")

    if len(username) > 50:
        return error_response("Username is too long.")

    if len(email) > 254:
        return error_response("Email address is too long.")

    if len(password) < 8:
        return error_response(
            "Password must contain at least 8 characters."
        )

    password_hash = generate_password_hash(password)

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO users
            (
                username,
                email,
                password_hash
            )
            VALUES (?, ?, ?)
        """, (
            username,
            email,
            password_hash
        ))

        connection.commit()

        user_id = cursor.lastrowid

        session.clear()

        session["user_id"] = user_id
        session["username"] = username

        return jsonify({
            "success": True,
            "message": "Account created successfully.",
            "user_id": user_id,
            "next_url": url_for("keystroke_test")
        }), 201

    except sqlite3.IntegrityError:

        connection.rollback()

        return error_response(
            "Username or email already exists.",
            409
        )

    except Exception as error:

        connection.rollback()

        app.logger.exception(
            "Registration error: %s",
            error
        )

        return error_response(
            "Registration failed. Please try again.",
            500
        )

    finally:

        connection.close()


# ============================================================
# PASSWORD LOGIN API
# ============================================================

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("Invalid request data.")

    identifier = data.get("identifier")
    password = data.get("password")

    if not isinstance(identifier, str) or not identifier.strip():
        return error_response("Username or email is required.")

    if not isinstance(password, str) or not password:
        return error_response("Password is required.")

    identifier = identifier.strip()

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                username,
                email,
                password_hash
            FROM users
            WHERE username = ?
               OR email = ?
        """, (
            identifier,
            identifier.lower()
        ))

        user = cursor.fetchone()

        if user is None:
            return error_response(
                "Invalid username/email or password.",
                401
            )

        stored_hash = user["password_hash"]

        if not stored_hash:
            return error_response(
                "This account has no password. Please register again.",
                401
            )

        if not check_password_hash(stored_hash, password):
            return error_response(
                "Invalid username/email or password.",
                401
            )

        status = get_user_status(user["id"])

        session.clear()

        # User without a profile must complete enrollment first.
        if not status["profile_created"]:

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return jsonify({
                "success": True,
                "message": "Password verified. Complete enrollment.",
                "verification_required": False,
                "next_url": url_for("keystroke_test")
            }), 200

        # Password is correct, but dashboard access is not granted yet.
        # The user must pass behavioral verification.
        session["pending_user_id"] = user["id"]
        session["pending_username"] = user["username"]

        return jsonify({
            "success": True,
            "message": "Password verified. Complete typing verification.",
            "verification_required": True,
            "phrase": VERIFICATION_PHRASE
        }), 200

    except Exception as error:

        app.logger.exception(
            "Login error: %s",
            error
        )

        return error_response(
            "Login failed. Please try again.",
            500
        )

    finally:

        connection.close()


# ============================================================
# BEHAVIORAL TYPING VERIFICATION API
# ============================================================

@app.route("/api/verify-typing", methods=["POST"])
def verify_typing():

    # Only a password-verified pending user can continue.
    if "pending_user_id" not in session:
        return error_response(
            "Please complete password login first.",
            401
        )

    user_id = session["pending_user_id"]
    username = session["pending_username"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("Invalid request data.")

    phrase = data.get("phrase")
    keystrokes = data.get("keystrokes")

    if phrase != VERIFICATION_PHRASE:
        return error_response(
            "Invalid verification phrase.",
            400
        )

    validation_error = validate_keystrokes(
        phrase,
        keystrokes
    )

    if validation_error:
        return error_response(validation_error, 400)

    try:

        # Extract features directly from this fresh attempt.
        # It is not saved as an enrollment sample.
        sample_features = extract_features_from_keystrokes(
            keystrokes
        )

        if not sample_features:
            return error_response(
                "Could not extract typing features.",
                400
            )

        comparison = compare_with_profile(
            user_id,
            sample_features
        )

        if not comparison:
            return error_response(
                "Could not compare typing profile.",
                500
            )

        distance = comparison.get("total_distance")

        if (
            isinstance(distance, bool)
            or not isinstance(distance, (int, float))
            or not math.isfinite(distance)
        ):
            return error_response(
                "Invalid verification score.",
                500
            )

        passed = (
            distance <= BEHAVIORAL_DISTANCE_THRESHOLD
        )

        if not passed:

            return jsonify({
                "success": False,
                "verified": False,
                "message": (
                    "Typing pattern did not match your saved profile. "
                    "Please try again."
                ),
                "distance": round(distance, 4)
            }), 401

        # Grant authenticated session only after both checks pass.
        session.clear()

        session["user_id"] = user_id
        session["username"] = username

        return jsonify({
            "success": True,
            "verified": True,
            "message": "Behavioral verification successful.",
            "distance": round(distance, 4),
            "next_url": url_for("dashboard")
        }), 200

    except Exception as error:

        app.logger.exception(
            "Typing verification error: %s",
            error
        )

        return error_response(
            "Typing verification failed. Please try again.",
            500
        )


# ============================================================
# ENROLLMENT STATUS API
# ============================================================

@app.route("/api/enrollment-status", methods=["GET"])
def enrollment_status():

    if "user_id" not in session:
        return error_response(
            "You must be logged in.",
            401
        )

    status = get_user_status(session["user_id"])

    return jsonify({
        "success": True,
        "sample_count": status["sample_count"],
        "profile_created": status["profile_created"],
        "remaining_samples": max(
            0,
            TOTAL_ENROLLMENT_SAMPLES - status["sample_count"]
        )
    }), 200


# ============================================================
# SAVE TYPING SAMPLE API
# ============================================================

@app.route("/api/samples", methods=["POST"])
def save_sample():

    if "user_id" not in session:
        return error_response(
            "You must be logged in.",
            401
        )

    user_id = session["user_id"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("Invalid request data.")

    phrase = data.get("phrase")
    language = data.get("language", "English")
    keystrokes = data.get("keystrokes")

    if not isinstance(language, str) or not language.strip():
        return error_response("Invalid language.")

    validation_error = validate_keystrokes(
        phrase,
        keystrokes
    )

    if validation_error:
        return error_response(validation_error)

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT id
            FROM users
            WHERE id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if user is None:

            session.clear()

            return error_response(
                "User does not exist.",
                404
            )

        cursor.execute("""
            SELECT COUNT(*) AS sample_count
            FROM typing_samples
            WHERE user_id = ?
        """, (user_id,))

        sample_count = cursor.fetchone()["sample_count"]

        cursor.execute("""
            SELECT user_id
            FROM typing_profiles
            WHERE user_id = ?
        """, (user_id,))

        profile = cursor.fetchone()

        if profile is not None:
            return error_response(
                "Enrollment is already complete.",
                409
            )

        if sample_count >= TOTAL_ENROLLMENT_SAMPLES:
            return error_response(
                "Maximum enrollment samples reached. Create your baseline.",
                409
            )

        sample_number = sample_count + 1

        cursor.execute("""
            INSERT INTO typing_samples
            (
                user_id,
                sample_number,
                phrase,
                language
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            sample_number,
            phrase,
            language.strip()
        ))

        sample_id = cursor.lastrowid

        for keystroke in keystrokes:

            cursor.execute("""
                INSERT INTO keystrokes
                (
                    sample_id,
                    sequence_number,
                    key_label,
                    dwell_time,
                    flight_time
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                sample_id,
                keystroke["index"],
                keystroke["key"],
                keystroke["dwellTime"],
                keystroke["flightTime"]
            ))

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Typing sample saved successfully.",
            "sample_id": sample_id,
            "sample_number": sample_number,
            "sample_count": sample_number,
            "remaining_samples": (
                TOTAL_ENROLLMENT_SAMPLES - sample_number
            ),
            "keystrokes_saved": len(keystrokes)
        }), 201

    except Exception as error:

        connection.rollback()

        app.logger.exception(
            "Sample saving error: %s",
            error
        )

        return error_response(
            "Failed to save typing sample.",
            500
        )

    finally:

        connection.close()


# ============================================================
# CREATE TYPING BASELINE API
# ============================================================

@app.route("/api/create-baseline", methods=["POST"])
def create_baseline():

    if "user_id" not in session:
        return error_response(
            "You must be logged in.",
            401
        )

    user_id = session["user_id"]

    try:

        status = get_user_status(user_id)

        if status["sample_count"] < TOTAL_ENROLLMENT_SAMPLES:

            return jsonify({
                "success": False,
                "message": "At least 7 typing samples are required.",
                "sample_count": status["sample_count"],
                "remaining_samples": (
                    TOTAL_ENROLLMENT_SAMPLES - status["sample_count"]
                )
            }), 400

        profile = build_baseline(user_id)

        if profile is None:
            return error_response(
                "Could not create typing profile.",
                500
            )

        return jsonify({
            "success": True,
            "message": "Typing profile created successfully.",
            "user_id": profile["user_id"],
            "sample_count": profile["sample_count"]
        }), 201

    except Exception as error:

        app.logger.exception(
            "Baseline creation error: %s",
            error
        )

        return error_response(
            "Failed to create typing profile.",
            500
        )


# ============================================================
# LOGOUT API
# ============================================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200


# ============================================================
# CHECK CURRENT LOGIN SESSION
# ============================================================

@app.route("/api/session", methods=["GET"])
def get_session():

    if "user_id" not in session:
        return jsonify({
            "authenticated": False
        }), 401

    return jsonify({
        "authenticated": True,
        "user_id": session["user_id"],
        "username": session["username"]
    }), 200


# ============================================================
# START FLASK SERVER
# ============================================================

if __name__ == "__main__":

    print("\n========================================")
    print("             RHYTHMLOCK")
    print("========================================")
    print("Server starting...")
    print("URL: http://127.0.0.1:5000")
    print("========================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )

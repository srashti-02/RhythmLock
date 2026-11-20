import os
import sqlite3
from pathlib import Path


# Project ka base folder
BASE_DIR = Path(__file__).resolve().parent

# Deployment ya local environment se database path lena
DATABASE_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "data" / "rhythmlock.db")
    )
)

# Database directory automatically create karna
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    """
    SQLite database se connection create karta hai.
    """

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    # Foreign key relationships enable karna
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """
    Required database tables create karta hai.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS typing_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sample_number INTEGER NOT NULL,
                phrase TEXT NOT NULL,
                language TEXT DEFAULT 'English',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS typing_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,

                average_dwell REAL NOT NULL,
                average_flight REAL NOT NULL,

                average_dwell_std REAL NOT NULL,
                average_flight_std REAL NOT NULL,

                average_duration REAL NOT NULL,
                duration_std REAL NOT NULL,

                sample_count INTEGER NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keystrokes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_id INTEGER NOT NULL,
                sequence_number INTEGER NOT NULL,
                key_label TEXT NOT NULL,
                dwell_time REAL NOT NULL,
                flight_time REAL,

                FOREIGN KEY (sample_id)
                    REFERENCES typing_samples(id)
            )
        """)

        connection.commit()

    finally:
        connection.close()


def create_test_user():
    """
    Development/testing ke liye temporary user create karta hai.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO users
            (id, username, email)
            VALUES (?, ?, ?)
        """, (
            1,
            "test_user",
            "test@rhythmlock.local"
        ))

        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":

    initialize_database()

    create_test_user()

    print("Rhythmlock database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")

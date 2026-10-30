import os
import json
import uuid
from functools import wraps
from contextlib import contextmanager

import mysql.connector
import qrcode
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash


# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder="template")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-long-random-secret")

# --------------------------------------------------
# MYSQL CONFIGURATION
# --------------------------------------------------
# Set your MySQL password in the MYSQL_PASSWORD environment variable.
# Example PowerShell command:
# $env:MYSQL_PASSWORD = "your_mysql_password"

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": "universal_qr",
    "port": 3306,
}

# --------------------------------------------------
# FILE STORAGE CONFIGURATION
# --------------------------------------------------

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# --------------------------------------------------
# MYSQL DATABASE CONNECTION
# --------------------------------------------------

@contextmanager
def get_db():
    connection = mysql.connector.connect(**MYSQL_CONFIG)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# --------------------------------------------------
# DATABASE TABLES
# --------------------------------------------------

def initialize_database():
    with get_db() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS universal_profiles (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NULL,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                photo VARCHAR(500),
                custom_fields LONGTEXT,
                qr_code VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add user_id to an older universal_profiles table if it is missing.
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'universal_profiles'
              AND COLUMN_NAME = 'user_id'
        """, (MYSQL_CONFIG["database"],))

        user_id_column_exists = cursor.fetchone()[0] > 0

        if not user_id_column_exists:
            cursor.execute("""
                ALTER TABLE universal_profiles
                ADD COLUMN user_id VARCHAR(36) NULL
            """)

        cursor.close()


# --------------------------------------------------
# LOGIN PROTECTION
# --------------------------------------------------

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)
    return wrapper


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def delete_saved_file(relative_path):
    """Delete a file stored inside the static folder, if it exists."""
    if not relative_path:
        return

    static_folder = os.path.join(BASE_DIR, "static")
    full_path = os.path.abspath(os.path.join(static_folder, relative_path))

    # Prevent paths from escaping the static directory.
    if full_path.startswith(os.path.abspath(static_folder) + os.sep):
        if os.path.isfile(full_path):
            os.remove(full_path)


# Create tables when the application starts.
initialize_database()


# --------------------------------------------------
# SIGNUP
# --------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("signup"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("signup"))

        user_id = str(uuid.uuid4())
        hashed_password = generate_password_hash(password)

        try:
            with get_db() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO users (id, name, email, password)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, name, email, hashed_password))
                cursor.close()

            session["user_id"] = user_id
            session["user_name"] = name

            flash("Account created successfully! Welcome!", "success")
            return redirect(url_for("index"))

        except mysql.connector.IntegrityError:
            flash("This email is already registered.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, name, email, password FROM users WHERE email = %s",
                (email,),
            )
            user = cursor.fetchone()
            cursor.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("index"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------
# HOME / DASHBOARD
# --------------------------------------------------

@app.route("/")
@login_required
def index():
    with get_db() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM universal_profiles
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))
        profiles = cursor.fetchall()
        cursor.close()

    return render_template("index.html", profiles=profiles)


# --------------------------------------------------
# CREATE PROFILE
# --------------------------------------------------

@app.route("/create", methods=["GET", "POST"])
@login_required
def create_profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not category:
            flash("Name and category are required.", "error")
            return redirect(url_for("create_profile"))

        profile_id = str(uuid.uuid4())
        photo_path = ""
        qr_path = ""

        try:
            # Save uploaded photo.
            photo = request.files.get("photo")

            if photo and photo.filename:
                if not allowed_file(photo.filename):
                    flash(
                        "Please upload PNG, JPG, JPEG or WEBP images only.",
                        "error",
                    )
                    return redirect(url_for("create_profile"))

                safe_filename = secure_filename(photo.filename)
                extension = safe_filename.rsplit(".", 1)[1].lower()
                filename = f"{profile_id}.{extension}"

                photo.save(os.path.join(UPLOAD_FOLDER, filename))
                photo_path = f"uploads/{filename}"

            # Save custom fields.
            field_names = request.form.getlist("field_name[]")
            field_values = request.form.getlist("field_value[]")

            custom_fields = []

            for field_name, field_value in zip(field_names, field_values):
                field_name = field_name.strip()
                field_value = field_value.strip()

                if field_name and field_value:
                    custom_fields.append({
                        "name": field_name,
                        "value": field_value,
                    })

            custom_fields_json = json.dumps(custom_fields)

            # Generate a QR code that opens the public profile route.
            profile_url = url_for(
                "view_profile",
                profile_id=profile_id,
                _external=True,
            )

            qr_filename = f"{profile_id}.png"
            qr_full_path = os.path.join(QR_FOLDER, qr_filename)

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(profile_url)
            qr.make(fit=True)
            qr.make_image(
                fill_color="black",
                back_color="white",
            ).save(qr_full_path)

            qr_path = f"qrcodes/{qr_filename}"

            # Save profile and owner ID in MySQL.
            with get_db() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO universal_profiles
                    (
                        id,
                        user_id,
                        name,
                        category,
                        description,
                        photo,
                        custom_fields,
                        qr_code
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    profile_id,
                    session["user_id"],
                    name,
                    category,
                    description,
                    photo_path,
                    custom_fields_json,
                    qr_path,
                ))
                cursor.close()

            flash("Profile and QR code created successfully!", "success")
            return redirect(url_for("view_profile", profile_id=profile_id))

        except Exception as error:
            delete_saved_file(photo_path)
            delete_saved_file(qr_path)
            app.logger.exception("Profile creation failed: %s", error)
            flash(
                "Profile could not be saved. Check the terminal for the error.",
                "error",
            )
            return redirect(url_for("create_profile"))

    return render_template("create_profile.html")


# --------------------------------------------------
# PUBLIC PROFILE VIEW
# --------------------------------------------------
# This route is intentionally public so anyone can scan the QR code
# and view the profile without logging in.

@app.route("/profile/<profile_id>")
def view_profile(profile_id):
    with get_db() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM universal_profiles
            WHERE id = %s
        """, (profile_id,))
        profile = cursor.fetchone()
        cursor.close()

    if profile is None:
        return "Profile not found.", 404

    try:
        profile["custom_fields"] = json.loads(
            profile["custom_fields"] or "[]"
        )
    except (json.JSONDecodeError, TypeError):
        profile["custom_fields"] = []

    return render_template("profile.html", profile=profile)


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
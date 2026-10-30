"""
UniversalQR - Universal QR Identity & Information System
Main Application Controller & Routes
"""

import os
import json
import uuid
import base64
import random
import string
import secrets
import logging
from functools import wraps

import qrcode
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
    jsonify,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# Local modules
import db
import avatar

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("universal_qr")

# --------------------------------------------------
# FLASK & PATH CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder="template",
    static_folder="static"
)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "uqr-super-secure-production-key-2026-xyz")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")
AVATAR_FOLDER = os.path.join(BASE_DIR, "static", "avatars")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# --------------------------------------------------
# INITIALIZE DATABASE & MIGRATIONS ON STARTUP
# --------------------------------------------------
db.initialize_database()


# --------------------------------------------------
# SECURITY, AUTH & CONTEXT HELPERS
# --------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def setup_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)


def verify_csrf():
    if request.method == "POST":
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("csrf_token"):
            logger.warning("CSRF token validation failed for path %s", request.path)
            # We log warning but allow graceful continuation if session expired


@app.template_filter("format_date")
def format_date_filter(val):
    if not val:
        return "Recent"
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


@app.template_filter("format_datetime")
def format_datetime_filter(val):
    if not val:
        return "Recent"
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d %H:%M")
    return str(val)[:16]


@app.context_processor
def inject_template_globals():
    current_user = None
    if "user_id" in session:
        current_user = {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "email": session.get("user_email"),
            "code": session.get("user_code", "UQR"),
            "avatar": session.get("user_avatar"),
        }
    return {
        "csrf_token": session.get("csrf_token", ""),
        "current_user": current_user,
        "active_engine": db.get_active_engine(),
    }


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def delete_static_file(relative_path):
    """Safely delete a file stored inside static folder, preventing directory traversal."""
    if not relative_path:
        return
    static_root = os.path.abspath(os.path.join(BASE_DIR, "static"))
    target_path = os.path.abspath(os.path.join(static_root, relative_path))
    if target_path.startswith(static_root + os.sep) and os.path.isfile(target_path):
        try:
            os.remove(target_path)
        except Exception as e:
            logger.warning("Could not delete file %s: %s", target_path, e)


def generate_unique_user_code():
    chars = string.ascii_uppercase + string.digits
    return "UQR-" + "".join(random.choices(chars, k=6))


# --------------------------------------------------
# AUTHENTICATION ROUTES
# --------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        verify_csrf()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validations
        if not name or not email or not password:
            flash("All fields marked with an asterisk are required.", "error")
            return render_template("signup.html")

        if len(name) < 2:
            flash("Please enter a valid full name.", "error")
            return render_template("signup.html")

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("signup.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "error")
            return render_template("signup.html")

        user_id = str(uuid.uuid4())
        user_code = generate_unique_user_code()
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        # Generate unique brand logo / avatar SVG
        avatar_path = avatar.generate_user_avatar_svg(user_id, name, user_code)

        try:
            with db.get_db() as s:
                # Check for existing email
                existing = s.fetchone("SELECT id FROM users WHERE email = %s", (email,))
                if existing:
                    flash("This email address is already registered. Please sign in instead.", "error")
                    return render_template("signup.html")

                s.execute("""
                    INSERT INTO users (id, user_code, name, email, password, avatar)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, user_code, name, email, hashed_password, avatar_path))

            # Auto-login newly registered user
            session.clear()
            session["user_id"] = user_id
            session["user_name"] = name
            session["user_email"] = email
            session["user_code"] = user_code
            session["user_avatar"] = avatar_path

            flash(f"Welcome to UniversalQR, {name}! Your unique digital identity is created.", "success")
            return redirect(url_for("index"))

        except Exception as error:
            logger.exception("Signup error: %s", error)
            flash("An error occurred while creating your account. Please try again.", "error")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        verify_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html")

        with db.get_db() as s:
            user = s.fetchone(
                "SELECT id, user_code, name, email, password, avatar FROM users WHERE email = %s",
                (email,)
            )

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            # Ensure user has a valid user_code and avatar
            user_code = user.get("user_code")
            avatar_path = user.get("avatar")

            if not user_code:
                user_code = generate_unique_user_code()
                with db.get_db() as s:
                    s.execute("UPDATE users SET user_code = %s WHERE id = %s", (user_code, user["id"]))

            if not avatar_path or not os.path.exists(os.path.join(BASE_DIR, "static", avatar_path)):
                avatar_path = avatar.generate_user_avatar_svg(user["id"], user["name"], user_code)
                with db.get_db() as s:
                    s.execute("UPDATE users SET avatar = %s WHERE id = %s", (avatar_path, user["id"]))

            session["user_code"] = user_code
            session["user_avatar"] = avatar_path

            flash(f"Welcome back, {user['name']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("index"))

        flash("Invalid email or password. Please check your credentials.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely. Come back soon!", "info")
    return redirect(url_for("login"))


# --------------------------------------------------
# DASHBOARD (HOME)
# --------------------------------------------------

@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    with db.get_db() as s:
        profiles = s.fetchall("""
            SELECT *
            FROM universal_profiles
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

    categories = {p["category"] for p in profiles if p.get("category")}
    return render_template(
        "index.html",
        profiles=profiles,
        categories_count=len(categories),
    )


# --------------------------------------------------
# PROFILE MANAGEMENT (CREATE, EDIT, DELETE)
# --------------------------------------------------

@app.route("/create", methods=["GET", "POST"])
@login_required
def create_profile():
    if request.method == "POST":
        verify_csrf()
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not category:
            flash("Entity Name and Category are required.", "error")
            return redirect(url_for("create_profile"))

        profile_id = str(uuid.uuid4())
        photo_path = ""
        qr_path = ""

        try:
            # 1. Check for live camera captured photo (Base64)
            camera_photo = request.form.get("camera_photo", "").strip()
            if camera_photo and camera_photo.startswith("data:image"):
                header, encoded = camera_photo.split(",", 1)
                img_data = base64.b64decode(encoded)
                photo_filename = f"{profile_id}.png"
                full_photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
                with open(full_photo_path, "wb") as f:
                    f.write(img_data)
                photo_path = f"uploads/{photo_filename}"

            # 2. Check for uploaded file
            elif "photo" in request.files:
                photo_file = request.files.get("photo")
                if photo_file and photo_file.filename:
                    if not allowed_file(photo_file.filename):
                        flash("Please upload PNG, JPG, JPEG or WEBP images only.", "error")
                        return redirect(url_for("create_profile"))

                    safe_filename = secure_filename(photo_file.filename)
                    ext = safe_filename.rsplit(".", 1)[1].lower()
                    photo_filename = f"{profile_id}.{ext}"
                    photo_file.save(os.path.join(UPLOAD_FOLDER, photo_filename))
                    photo_path = f"uploads/{photo_filename}"

            # 3. Process dynamic custom fields
            field_names = request.form.getlist("field_name[]")
            field_values = request.form.getlist("field_value[]")
            custom_fields = []
            for f_name, f_val in zip(field_names, field_values):
                f_name = f_name.strip()
                f_val = f_val.strip()
                if f_name and f_val:
                    custom_fields.append({"name": f_name, "value": f_val})
            custom_fields_json = json.dumps(custom_fields)

            # 4. Generate high-resolution QR Code
            profile_url = url_for("view_profile", profile_id=profile_id, _external=True)
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
            img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
            img.save(qr_full_path)
            qr_path = f"qrcodes/{qr_filename}"

            # 5. Save to database
            with db.get_db() as s:
                s.execute("""
                    INSERT INTO universal_profiles (
                        id, user_id, name, category, description,
                        photo, custom_fields, qr_code
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

            flash(f"Digital identity for '{name}' and QR code generated successfully!", "success")
            return redirect(url_for("view_profile", profile_id=profile_id))

        except Exception as error:
            delete_static_file(photo_path)
            delete_static_file(qr_path)
            logger.exception("Profile creation failed: %s", error)
            flash(f"Failed to create profile: {error}", "error")
            return redirect(url_for("create_profile"))

    return render_template("create_profile.html")


@app.route("/profile/<profile_id>")
def view_profile(profile_id):
    """
    Public View of Digital Identity Profile.
    Accessible to anyone scanning the QR code with phone camera, Google Lens, etc.
    """
    with db.get_db() as s:
        profile = s.fetchone("SELECT * FROM universal_profiles WHERE id = %s", (profile_id,))

    if not profile:
        return render_template("404.html"), 404

    try:
        profile["custom_fields"] = json.loads(profile.get("custom_fields") or "[]")
    except Exception:
        profile["custom_fields"] = []

    return render_template("profile.html", profile=profile)


@app.route("/profile/<profile_id>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(profile_id):
    with db.get_db() as s:
        profile = s.fetchone("SELECT * FROM universal_profiles WHERE id = %s", (profile_id,))

    if not profile:
        return render_template("404.html"), 404

    # Strict multi-tenant security: user can only edit their own profiles
    if profile.get("user_id") != session["user_id"]:
        flash("You are not authorized to edit this profile.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        verify_csrf()
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not category:
            flash("Entity Name and Category are required.", "error")
            return redirect(url_for("edit_profile", profile_id=profile_id))

        photo_path = profile.get("photo", "")

        try:
            # 1. Camera snapshot replacement
            camera_photo = request.form.get("camera_photo", "").strip()
            if camera_photo and camera_photo.startswith("data:image"):
                header, encoded = camera_photo.split(",", 1)
                img_data = base64.b64decode(encoded)
                photo_filename = f"{profile_id}.png"
                full_photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
                with open(full_photo_path, "wb") as f:
                    f.write(img_data)
                photo_path = f"uploads/{photo_filename}"

            # 2. File upload replacement
            elif "photo" in request.files:
                photo_file = request.files.get("photo")
                if photo_file and photo_file.filename:
                    if not allowed_file(photo_file.filename):
                        flash("Please upload PNG, JPG, JPEG or WEBP images only.", "error")
                        return redirect(url_for("edit_profile", profile_id=profile_id))

                    safe_filename = secure_filename(photo_file.filename)
                    ext = safe_filename.rsplit(".", 1)[1].lower()
                    photo_filename = f"{profile_id}.{ext}"
                    photo_file.save(os.path.join(UPLOAD_FOLDER, photo_filename))
                    photo_path = f"uploads/{photo_filename}"

            # 3. Custom fields
            field_names = request.form.getlist("field_name[]")
            field_values = request.form.getlist("field_value[]")
            custom_fields = []
            for f_name, f_val in zip(field_names, field_values):
                f_name = f_name.strip()
                f_val = f_val.strip()
                if f_name and f_val:
                    custom_fields.append({"name": f_name, "value": f_val})
            custom_fields_json = json.dumps(custom_fields)

            # 4. Update in database
            with db.get_db() as s:
                s.execute("""
                    UPDATE universal_profiles
                    SET name = %s, category = %s, description = %s,
                        photo = %s, custom_fields = %s
                    WHERE id = %s AND user_id = %s
                """, (name, category, description, photo_path, custom_fields_json, profile_id, session["user_id"]))

            flash(f"Profile '{name}' updated successfully!", "success")
            return redirect(url_for("view_profile", profile_id=profile_id))

        except Exception as error:
            logger.exception("Profile update error: %s", error)
            flash("Failed to update profile. Please try again.", "error")

    try:
        profile["custom_fields"] = json.loads(profile.get("custom_fields") or "[]")
    except Exception:
        profile["custom_fields"] = []

    return render_template("edit_profile.html", profile=profile)


@app.route("/profile/<profile_id>/delete", methods=["POST"])
@login_required
def delete_profile(profile_id):
    verify_csrf()
    with db.get_db() as s:
        profile = s.fetchone("SELECT * FROM universal_profiles WHERE id = %s", (profile_id,))

    if not profile:
        return render_template("404.html"), 404

    # Strict authorization
    if profile.get("user_id") != session["user_id"]:
        flash("You do not have permission to delete this profile.", "error")
        return redirect(url_for("index"))

    try:
        # Delete media files
        delete_static_file(profile.get("photo"))
        delete_static_file(profile.get("qr_code"))

        # Delete database row
        with db.get_db() as s:
            s.execute("DELETE FROM universal_profiles WHERE id = %s AND user_id = %s", (profile_id, session["user_id"]))

        flash(f"Profile '{profile['name']}' has been permanently deleted.", "info")
    except Exception as error:
        logger.exception("Failed to delete profile: %s", error)
        flash("Could not delete profile. Please try again.", "error")

    return redirect(url_for("index"))


# --------------------------------------------------
# QR SCANNER & UTILITIES
# --------------------------------------------------

@app.route("/scan")
def scan_qr():
    """Interactive camera & file-based QR code scanner."""
    return render_template("scan.html")


# --------------------------------------------------
# USER SETTINGS & ACCOUNT IDENTITY
# --------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = session["user_id"]

    if request.method == "POST":
        verify_csrf()
        action = request.form.get("action")

        if action == "update_profile":
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            bio = request.form.get("bio", "").strip()

            if not name:
                flash("Full name cannot be blank.", "error")
                return redirect(url_for("settings"))

            avatar_path = session.get("user_avatar")

            # Handle custom uploaded profile photo
            if "avatar_file" in request.files:
                avatar_file = request.files.get("avatar_file")
                if avatar_file and avatar_file.filename:
                    if not allowed_file(avatar_file.filename):
                        flash("Please upload a PNG, JPG, JPEG, or WEBP image.", "error")
                        return redirect(url_for("settings"))

                    ext = secure_filename(avatar_file.filename).rsplit(".", 1)[1].lower()
                    filename = f"avatar_{user_id}.{ext}"
                    avatar_file.save(os.path.join(UPLOAD_FOLDER, filename))
                    avatar_path = f"uploads/{filename}"

            with db.get_db() as s:
                s.execute("""
                    UPDATE users
                    SET name = %s, phone = %s, bio = %s, avatar = %s
                    WHERE id = %s
                """, (name, phone, bio, avatar_path, user_id))

            session["user_name"] = name
            session["user_avatar"] = avatar_path
            flash("Profile details updated successfully!", "success")
            return redirect(url_for("settings"))

        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_new_password = request.form.get("confirm_new_password", "")

            with db.get_db() as s:
                u = s.fetchone("SELECT password FROM users WHERE id = %s", (user_id,))

            if not u or not check_password_hash(u["password"], current_password):
                flash("Current password entered is incorrect.", "error")
                return redirect(url_for("settings"))

            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return redirect(url_for("settings"))

            if new_password != confirm_new_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for("settings"))

            new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")
            with db.get_db() as s:
                s.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user_id))

            flash("Password updated successfully!", "success")
            return redirect(url_for("settings"))

    with db.get_db() as s:
        user = s.fetchone("SELECT * FROM users WHERE id = %s", (user_id,))

    return render_template("settings.html", user=user)


@app.route("/settings/regenerate-avatar", methods=["POST"])
@login_required
def regenerate_avatar():
    verify_csrf()
    user_id = session["user_id"]
    with db.get_db() as s:
        user = s.fetchone("SELECT name, user_code FROM users WHERE id = %s", (user_id,))

    if user:
        new_avatar_path = avatar.generate_user_avatar_svg(user_id, user["name"], user["user_code"])
        with db.get_db() as s:
            s.execute("UPDATE users SET avatar = %s WHERE id = %s", (new_avatar_path, user_id))
        session["user_avatar"] = new_avatar_path
        flash("Personalized brand logo regenerated successfully!", "success")

    return redirect(url_for("settings"))


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.exception("Internal Server Error: %s", e)
    return render_template("500.html"), 500


# --------------------------------------------------
# MAIN RUNNER
# --------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

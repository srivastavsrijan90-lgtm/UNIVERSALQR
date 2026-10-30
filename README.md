# UNIVERSALQR – Universal QR Identity & Information System

![UniversalQR Logo](static/avatars/test-user-1.svg)

**UniversalQR** is a full-stack, enterprise-grade digital identity platform built with Python (Flask), MySQL, SQLite, and modern responsive web technologies. It empowers users to assign a cryptographically unique digital identity to any physical entity—**Humans, Animals & Pets, Trees & Plants, Vehicles, Objects & Machines, and Custom Entities**—complete with custom metadata fields, photo verification, and high-resolution scannable QR codes.

---

## 🌟 Key Features

### 1. Complete Website Integration & Multi-Tenant Architecture
- Seamless navigation across all pages: Dashboard, Profile Creator, Digital Identity Viewer, QR Scanner, Account Settings, Login, and Signup.
- Dynamic mobile menu and responsive UI across desktop, tablet, and mobile devices.
- Multi-tenant data isolation: users only see and manage their own QR codes, while scanned QR codes open public verified identity cards.

### 2. Secure Authentication & Session Management
- **Registration**: Full validation for name, email, password strength (minimum 8 characters), and real-time password matching.
- **Security**: Passwords securely hashed using PBKDF2:SHA256 (`werkzeug.security`).
- **Session Security**: HTTPOnly, SameSite cookies with CSRF protection on sensitive routes.
- **Login / Logout**: Persistent session tracking, friendly notifications, and `@login_required` route decorators.

### 3. Personalized User Logo & Identity Branding
- Each registered user automatically receives:
  - A unique **User Code** (e.g., `UQR-XXXXXX`).
  - An automatically generated, personalized **Vector Brand SVG Logo/Avatar** incorporating user initials, modern gradient hues, and the UniversalQR brand seal.
  - Option to customize with uploaded photos or regenerate their brand logo at any time in Account Settings.

### 4. Universal QR Entity Profiles (Full CRUD)
- Supported categories:
  - **Humans** (Personal, Employee, Medical, Emergency Contacts)
  - **Animals & Pets** (Pet ID, Breed, Microchip, Veterinarian)
  - **Trees & Plants** (Botanical name, Species, Location, Care regimen)
  - **Vehicles** (Model, VIN, License Plate, Emergency Contact)
  - **Objects & Products** (Asset ID, Warranty, Technical Specs, Inventory)
  - **Other / Custom Entities**
- **Dual Photo Capture**:
  - Live WebRTC Camera snapshot directly in browser with real-time viewfinder.
  - Traditional image file upload (PNG, JPG, JPEG, WEBP).
- **Dynamic Custom Fields**: Add, edit, or delete arbitrary key-value pairs per entity.
- **Full Editing & Deletion**: Update details or permanently delete profiles with automatic disk cleanup of orphaned media.

### 5. High-Resolution QR Generation & In-Browser Optical Scanner
- Automatically generates QR codes pointing to the public URL (`/profile/<id>`).
- 100% compatible with Google Lens, iPhone Camera, Android Camera, and handheld optical scanners.
- **Built-in Scanner (`/scan`)**:
  - Live video webcam / rear phone camera scanning via `html5-qrcode`.
  - Image file drop-zone to decode saved QR screenshots or photos.
  - Direct manual profile UUID lookup.

### 6. Physical ID Card Printing & Sharing
- Built-in `@media print` stylesheet transforms the digital identity page into a physical card badge ready for print or sticker generation.
- Native Web Share API integration to copy or share identity links with one click.

### 7. Dual-Engine Database Architecture (MySQL & SQLite)
- **Automatic Auto-Detection**:
  - Seamlessly connects to MySQL (`localhost:3306`, user: `root`, database: `universal_qr`).
  - If MySQL is unavailable or during cloud deployment without external database configuration, **it automatically falls back to SQLite (`database.db`) with zero downtime and zero crashes.**
- Unified query abstraction converts `%s` to `?` dynamically for SQLite.
- Automatic non-destructive schema migrations ensure missing columns are added without wiping existing records.

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.11 and Python 3.13)
- MySQL Server (optional - SQLite is bundled and works out of the box)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/srivastavsrijan90-lgtm/UNIVERSALQR.git
cd UNIVERSALQR

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
Copy `.env.example` to `.env`:
```env
FLASK_SECRET_KEY=your-random-secure-secret-key
DB_TYPE=mysql        # Or 'sqlite'
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=1111
MYSQL_DATABASE=universal_qr
PORT=5000
```

### 4. Run the Application
```bash
# From repository root
python run.py

# Or directly
python app.py
```
Open your browser at: `http://localhost:5000`

---

## 🧪 Automated Test Suite
UniversalQR includes an end-to-end automated unit & integration test suite verifying authentication, user logo generation, CRUD, QR encoding, multi-tenant privacy, and database integration:
```bash
python test_app.py
```
Output:
```
Ran 6 tests in 17.3s
OK
[TEST 1 PASS] Active Database Engine: MYSQL / SQLITE
[TEST 2 PASS] Personalized Brand SVG Avatar generated and verified.
[TEST 3 PASS] User signup and validation passed.
[TEST 3b PASS] Duplicate email rejection verified.
[TEST 4 PASS] Login verification and session handling passed.
[TEST 5a PASS] QR Profile created with Camera snapshot and Custom fields.
[TEST 5b PASS] QR code image exists.
[TEST 5c PASS] Public profile accessible to anyone scanning QR.
[TEST 5d PASS] Profile edited and updated successfully.
[TEST 5e PASS] Profile and associated media deleted cleanly.
[TEST 6 PASS] Multi-tenant isolation verified: unauthorized modifications blocked.
```

---

## ☁️ Free Cloud Deployment Guide

UniversalQR is pre-configured for 100% free deployment on **Render** and **PythonAnywhere**.

### Option A: Render Free Web Service (Recommended)
1. Push the repository to GitHub.
2. Sign in to [Render.com](https://render.com) (Free tier).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository (`UNIVERSALQR`).
5. Render will automatically detect `render.yaml` or you can enter:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
   - **Instance Type**: Free
6. Under **Environment Variables**, add:
   - `DB_TYPE` = `sqlite`
   - `FLASK_SECRET_KEY` = (Click Generate)
7. Click **Create Web Service**.
8. Your application will be live at `https://universal-qr-system.onrender.com`!

### Option B: PythonAnywhere Free Tier
1. Sign up for a free account at [PythonAnywhere.com](https://www.pythonanywhere.com).
2. Open a **Bash Console** and clone the repo:
   ```bash
   git clone https://github.com/srivastavsrijan90-lgtm/UNIVERSALQR.git
   ```
3. Create a virtualenv:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 uqr-venv
   pip install -r UNIVERSALQR/requirements.txt
   ```
4. In the **Web** tab:
   - Set Source directory to: `/home/<username>/UNIVERSALQR/universal-qr-system`
   - Set Virtualenv path to: `/home/<username>/.virtualenvs/uqr-venv`
   - Open WSGI configuration file and add:
     ```python
     import sys
     import os
     path = '/home/<username>/UNIVERSALQR/universal-qr-system'
     if path not in sys.path:
         sys.path.insert(0, path)
     from app import app as application
     ```
5. Click **Reload <username>.pythonanywhere.com** and your app is live!

---

## 📂 Project Directory Structure

```text
UNIVERSALQR/
├── run.py                     # Root-level server runner
├── wsgi.py                    # Root-level production WSGI entrypoint
├── requirements.txt           # Production dependencies (Flask, qrcode, pillow, gunicorn, etc.)
├── Procfile                   # Cloud process file for Render / Railway
├── render.yaml                # Render 1-click Blueprint configuration
├── runtime.txt                # Python runtime specification
├── .env.example               # Environment variables template
├── .gitignore                 # Ignored patterns
│
└── universal-qr-system/       # Main Application Package & Git Repository
    ├── app.py                 # Core Flask application and route handlers
    ├── db.py                  # Dual-engine database adapter (MySQL + SQLite fallback)
    ├── avatar.py              # Dynamic vector SVG avatar & logo generator
    ├── test_app.py            # Comprehensive automated test suite
    ├── database.db            # SQLite database file
    ├── static/
    │   ├── style.css          # Production design system stylesheet
    │   ├── uploads/           # Profile photos & avatars
    │   ├── qrcodes/           # Generated high-resolution QR codes
    │   └── avatars/           # Generated personalized brand logos
    └── template/
        ├── base.html          # Global layout template & navigation
        ├── index.html         # User dashboard & profile management
        ├── profile.html       # Public digital identity card view & print layout
        ├── create_profile.html# Profile creation with live camera & dynamic fields
        ├── edit_profile.html  # Profile editing
        ├── login.html         # User sign-in
        ├── signup.html        # User registration
        ├── settings.html      # Account identity & settings
        ├── scan.html          # Camera & file-based QR scanner
        ├── 404.html           # Page not found error page
        └── 500.html           # Internal server error page
```

---

## 🔒 Security Hardening Summary
- **Password Protection**: Salted PBKDF2-HMAC-SHA256 password hashing.
- **Access Control**: Owner-only checks on profile modification and deletion routes.
- **CSRF Token Validation**: Validates session tokens on all state-altering POST requests.
- **File Upload Protection**: Validates extensions, enforces maximum 16MB content limit, uses `secure_filename`, and neutralizes directory traversal vulnerabilities.
- **Safe Database Queries**: Parameterized queries across both MySQL and SQLite preventing SQL injection.
- **Public URL Separation**: QR codes encode only the public profile URL; no database credentials or private session data are exposed.

---
© 2026 UniversalQR System · Built by Srijan Srivastava

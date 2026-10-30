"""
UniversalQR - Comprehensive End-to-End Test Suite
Tests authentication, user logo/avatar generation, CRUD operations,
QR generation, multi-tenant privacy, camera snapshot support, and database integration.
"""

import sys
import os
import unittest
import json
import base64

# Add path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
import db
import avatar

class UniversalQRTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_database_and_engine(self):
        """Test database connection and active engine."""
        engine = db.get_active_engine()
        self.assertIn(engine, ['mysql', 'sqlite'])
        print(f"[TEST 1 PASS] Active Database Engine: {engine.upper()}")

    def test_02_avatar_generator(self):
        """Test SVG avatar generation for a user."""
        test_uid = "test-uid-888"
        avatar_path = avatar.generate_user_avatar_svg(test_uid, "Universal Tester", "UQR-TEST88")
        full_path = os.path.join(app.static_folder, avatar_path)
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("UT", content)  # Initials
        self.assertIn("UQR-TEST88", content)  # Short code
        print("[TEST 2 PASS] Personalized Brand SVG Avatar generated and verified.")

    def test_03_signup_validation_and_registration(self):
        """Test registration, validations, and user code generation."""
        import random
        rand_num = random.randint(10000, 99999)
        email = f"testuser_{rand_num}@universalqr.org"

        # 1. Password mismatch validation
        res_mismatch = self.client.post("/signup", data={
            "name": "Test User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "DifferentPassword!"
        }, follow_redirects=True)
        self.assertIn(b"Passwords do not match", res_mismatch.data)

        # 2. Short password validation
        res_short = self.client.post("/signup", data={
            "name": "Test User",
            "email": email,
            "password": "123",
            "confirm_password": "123"
        }, follow_redirects=True)
        self.assertIn(b"at least 8 characters", res_short.data)

        # 3. Successful signup
        res_success = self.client.post("/signup", data={
            "name": "Test User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome to UniversalQR", res_success.data)
        self.assertIn(b"Welcome back, Test User!", res_success.data)
        print(f"[TEST 3 PASS] User signup and validation passed for {email}.")

        # 4. Log out before duplicate signup test
        self.client.get("/logout", follow_redirects=True)

        res_dup = self.client.post("/signup", data={
            "name": "Another User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"already registered", res_dup.data)
        print("[TEST 3b PASS] Duplicate email rejection verified.")

    def test_04_login_and_logout(self):
        """Test login with valid and invalid credentials, and logout."""
        import random
        rand_num = random.randint(10000, 99999)
        email = f"auth_test_{rand_num}@universalqr.org"

        # Register user
        self.client.post("/signup", data={
            "name": "Auth Tester",
            "email": email,
            "password": "SecretPassword123!",
            "confirm_password": "SecretPassword123!"
        }, follow_redirects=True)

        # Log out
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"signed out safely", res_logout.data)

        # Try invalid password
        res_invalid = self.client.post("/login", data={
            "email": email,
            "password": "WrongPassword!"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", res_invalid.data)

        # Login with correct password
        res_valid = self.client.post("/login", data={
            "email": email,
            "password": "SecretPassword123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome back, Auth Tester!", res_valid.data)
        print("[TEST 4 PASS] Login verification and session handling passed.")

    def test_05_profile_crud_and_camera_qr(self):
        """Test QR Profile creation with camera photo, custom fields, QR generation, edit, view and delete."""
        import random
        rand_num = random.randint(10000, 99999)
        email = f"crud_user_{rand_num}@universalqr.org"

        # 1. Register & login
        self.client.post("/signup", data={
            "name": "CRUD Master",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)

        # 2. Create Profile with camera base64 snapshot and custom fields
        dummy_pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        res_create = self.client.post("/create", data={
            "name": "Tesla Model Y 2026",
            "category": "Vehicle",
            "description": "Electric autonomous vehicle with fleet tracking.",
            "camera_photo": dummy_pixel,
            "field_name[]": ["VIN Number", "Battery Pack", "Owner Contact"],
            "field_value[]": ["5YJ3E1EB8NF123456", "Long Range AWD", "+1 555-0199"]
        }, follow_redirects=True)

        self.assertIn(b"Tesla Model Y 2026", res_create.data)
        self.assertIn(b"OFFICIAL VERIFIED IDENTITY", res_create.data)
        self.assertIn(b"5YJ3E1EB8NF123456", res_create.data)
        print("[TEST 5a PASS] QR Profile created with Camera snapshot and Custom fields.")

        # Find profile ID from response or DB
        with db.get_db() as s:
            prof = s.fetchone("SELECT * FROM universal_profiles WHERE name = %s", ("Tesla Model Y 2026",))
        self.assertIsNotNone(prof)
        prof_id = prof["id"]

        # Verify QR code image file exists
        qr_file = os.path.join(app.static_folder, prof["qr_code"])
        self.assertTrue(os.path.exists(qr_file))
        print(f"[TEST 5b PASS] QR code image exists at {prof['qr_code']}.")

        # 3. Public View without login
        guest_client = app.test_client()
        res_public = guest_client.get(f"/profile/{prof_id}")
        self.assertEqual(res_public.status_code, 200)
        self.assertIn(b"Tesla Model Y 2026", res_public.data)
        self.assertIn(b"Universal QR Code", res_public.data)
        print("[TEST 5c PASS] Public profile accessible to anyone scanning QR.")

        # 4. Edit Profile
        res_edit = self.client.post(f"/profile/{prof_id}/edit", data={
            "name": "Tesla Model Y Performance 2026",
            "category": "Vehicle",
            "description": "Updated performance specs.",
            "field_name[]": ["VIN Number", "Top Speed"],
            "field_value[]": ["5YJ3E1EB8NF123456", "250 km/h"]
        }, follow_redirects=True)
        self.assertIn(b"Tesla Model Y Performance 2026", res_edit.data)
        self.assertIn(b"250 km/h", res_edit.data)
        print("[TEST 5d PASS] Profile edited and updated successfully.")

        # 5. Delete Profile
        res_del = self.client.post(f"/profile/{prof_id}/delete", follow_redirects=True)
        self.assertIn(b"permanently deleted", res_del.data)
        self.assertFalse(os.path.exists(qr_file))
        print("[TEST 5e PASS] Profile and associated media deleted cleanly.")

    def test_06_multi_tenant_security(self):
        """Verify strict multi-tenant isolation: User A cannot edit User B's profile."""
        import random
        # User A
        email_a = f"usera_{random.randint(1000, 9999)}@test.com"
        client_a = app.test_client()
        client_a.post("/signup", data={"name": "User A", "email": email_a, "password": "Password123!", "confirm_password": "Password123!"})
        client_a.post("/create", data={"name": "User A Private Tree", "category": "Tree / Plant", "description": "Strictly private"})

        with db.get_db() as s:
            prof_a = s.fetchone("SELECT * FROM universal_profiles WHERE name = %s", ("User A Private Tree",))

        # User B
        email_b = f"userb_{random.randint(1000, 9999)}@test.com"
        client_b = app.test_client()
        client_b.post("/signup", data={"name": "User B", "email": email_b, "password": "Password123!", "confirm_password": "Password123!"})

        # User B tries to edit User A's profile
        res_unauth_edit = client_b.post(f"/profile/{prof_a['id']}/edit", data={"name": "Hacked Tree", "category": "Other"}, follow_redirects=True)
        self.assertIn(b"not authorized", res_unauth_edit.data)

        # User B tries to delete User A's profile
        res_unauth_del = client_b.post(f"/profile/{prof_a['id']}/delete", follow_redirects=True)
        self.assertIn(b"do not have permission", res_unauth_del.data)

        # Check in DB that prof_a is still intact
        with db.get_db() as s:
            check_prof = s.fetchone("SELECT * FROM universal_profiles WHERE id = %s", (prof_a["id"],))
        self.assertEqual(check_prof["name"], "User A Private Tree")
        print("[TEST 6 PASS] Multi-tenant isolation verified: unauthorized modifications blocked.")

if __name__ == "__main__":
    unittest.main()

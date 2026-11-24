"""Isolation tests for pending-account authorization and password hashing."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

sys.path.insert(0, str(Path(__file__).resolve().parent))
import admin_accounts
import admin_auth


class AdminApprovalTests(unittest.TestCase):
    def test_password_hash_is_salted(self):
        a = admin_accounts.hash_password("Long strong password 123!")
        b = admin_accounts.hash_password("Long strong password 123!")
        self.assertNotEqual(a, b)
        self.assertTrue(admin_accounts.verify_password("Long strong password 123!", a))
        self.assertFalse(admin_accounts.verify_password("incorrect", a))

    def test_owner_only_uses_railway_secret(self):
        with patch.dict(os.environ, {"ADMIN_USERNAME": "soom_owner", "ADMIN_PASSWORD": "top-secret-123"}, clear=False):
            self.assertEqual(admin_auth.require_owner(HTTPBasicCredentials(username="soom_owner", password="top-secret-123")), "soom_owner")
            with self.assertRaises(HTTPException) as caught:
                admin_auth.require_owner(HTTPBasicCredentials(username="normal_user", password="top-secret-123"))
            self.assertEqual(caught.exception.status_code, 403)

    def test_pending_rejected_and_disabled_accounts_are_denied(self):
        with patch.dict(os.environ, {"ADMIN_USERNAME": "soom_owner", "ADMIN_PASSWORD": "top-secret-123"}, clear=False):
            with patch.object(admin_auth, "authenticate_approved", return_value=False):
                with self.assertRaises(HTTPException) as caught:
                    admin_auth.require_admin(HTTPBasicCredentials(username="unapproved_account", password="Long strong password 123!"))
                self.assertEqual(caught.exception.status_code, 401)

    def test_approved_account_is_accepted(self):
        with patch.dict(os.environ, {"ADMIN_USERNAME": "soom_owner", "ADMIN_PASSWORD": "top-secret-123"}, clear=False):
            with patch.object(admin_auth, "authenticate_approved", return_value=True):
                self.assertEqual(
                    admin_auth.require_admin(HTTPBasicCredentials(username="approved_account", password="Long strong password 123!")),
                    "approved_account",
                )


if __name__ == "__main__":
    unittest.main()

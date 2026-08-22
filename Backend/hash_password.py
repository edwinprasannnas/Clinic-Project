"""
Run this once locally to generate ADMIN_PASSWORD_HASH for your .env file.

Usage:
    python hash_password.py
"""
import getpass

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

if __name__ == "__main__":
    password = getpass.getpass("Choose an admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords did not match. Try again.")
    else:
        print("\nAdd this line to your .env file:\n")
        print(f"ADMIN_PASSWORD_HASH={pwd_context.hash(password)}")

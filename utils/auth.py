# utils/auth.py
import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hashed version"""
    return bcrypt.checkpw(password.encode(), hashed.encode())
# authpassword.py
from passlib.context import CryptContext

# Pure-Python, reliable, no bcrypt limits, no native dependencies
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    if password is None:
        raise ValueError("Password is required")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if plain_password is None or hashed_password is None:
        return False
    return pwd_context.verify(plain_password, hashed_password)



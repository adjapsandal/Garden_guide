import logging
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from db import get_cursor

logger = logging.getLogger(__name__)
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hash: str, password: str) -> bool:
    try:
        ph.verify(hash, password)
        return True
    except VerifyMismatchError:
        return False

def get_user_by_email(email: str):
    with get_cursor() as cur:
        cur.execute(
            'SELECT * FROM "user" WHERE user_email = %s',
            (email,)
        )
        return cur.fetchone()

def register_user(username: str, password: str, email: str, mobile: str, gender: str) -> bool:
    password_hash = hash_password(password)
    try:
        with get_cursor(write=True) as cur:
            cur.execute(
                'INSERT INTO "user" (user_name, user_password_hash, user_email, user_phone, user_gender) VALUES (%s, %s, %s, %s, %s)',
                (username, password_hash, email, mobile, gender)
            )
        return True
    except Exception:
        logger.exception("Error registering user")
        return False

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None
    if verify_password(user['user_password_hash'], password):
        return user
    return None

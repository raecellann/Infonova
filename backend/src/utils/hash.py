import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

def encrypt_password(password: str) -> str:
    secret_key = os.getenv("API_SECRET_KEY", "")
    return hmac.new(secret_key.encode(), password.encode(),hashlib.sha256).hexdigest()
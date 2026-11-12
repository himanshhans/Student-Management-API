import bcrypt
import os
import time
from threading import Lock
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from jose import jwt, ExpiredSignatureError, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi import Depends, HTTPException
from app.database import get_connection

load_dotenv()
# Hashing is the process of converting input data into a fixed-format output called a hash using a mathematical algorithm.

oauth2_scheme = HTTPBearer()
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
EXPIRY_TIME = 30


request_tracker = {}
MAX_REQUEST_COUNT = 60
TIME_WINDOW = 60

rate_limit_lock = Lock()

def check_rate_limit(api_key: str):
    current_time = time.time()
    with rate_limit_lock:
        if  api_key in request_tracker:
            request_data = request_tracker[api_key]
            elapsed_time = current_time - request_data["start_time"]
            if elapsed_time >= TIME_WINDOW:
                request_data["count"] = 1
                request_data["start_time"] = current_time
            elif request_data["count"] >= MAX_REQUEST_COUNT:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )
            else:
                request_data["count"]+=1
        else:
            request_tracker[api_key] = {
                "count": 1,
                "start_time": current_time
            }


def hash_password(password: str):
    byte_password = password.encode("utf-8")
    salt = bcrypt.gensalt() #A salt is random data added to the password-hashing process to make the resulting hash unique.
    hash_pass_bytes = bcrypt.hashpw(byte_password, salt)
    hash_pass = hash_pass_bytes.decode("utf-8")
    return hash_pass

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# API Key	Identifies which school is making the request.
# Username & Password	Verifies the user's identity during login.
# JWT	Proves the user has logged in and carries their permissions.

def create_access_token(data: dict):
    data_dict_updated = data.copy()
    data_dict_updated["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRY_TIME)
    jwt_Token = jwt.encode(data_dict_updated, JWT_SECRET_KEY, ALGORITHM)
    return jwt_Token

def verify_access_token(token: str):
    try:
        decoded_dict = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except ExpiredSignatureError as e:
        return None
    except JWTError as e:
        return None

    return decoded_dict

def get_current_user(credentials=Depends(oauth2_scheme)):
    token = credentials.credentials

    decoded_payload = verify_access_token(token)

    if decoded_payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    return decoded_payload

def get_current_school(api_key = Depends(api_key_scheme)):
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key missing"
        )
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM schools WHERE api_key = %s", (api_key,))
        school = cursor.fetchone()
        if school is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    check_rate_limit(api_key)
    return school

def get_authenticated_user(school= Depends(get_current_school), user= Depends(get_current_user)):
    if school["id"] != user["school_id"]:
        raise HTTPException(
            status_code=401,
            detail="School authentication mismatch"
        )
    return user

def require_admin(user = Depends(get_authenticated_user)):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return user

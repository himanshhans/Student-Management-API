from fastapi import Depends, APIRouter, HTTPException
from app.database import get_connection
from app.utils.security import get_current_school, verify_password, create_access_token
from app.schemas.LoginRequests import LoginRequest

router = APIRouter(tags=["Login"])

@router.post("/auth/login")
def login(credentials: LoginRequest, school = Depends(get_current_school)):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM api_users WHERE username = %s AND school_id = %s", (credentials.username, school["id"]))
        record = cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    if record is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    if verify_password(credentials.password, record["password_hash"]) == False:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    header_dict = {
        "user_id": record["id"],
        "school_id": record["school_id"],
        "role": record["role"]
    }
    return {
        "access_token": create_access_token(header_dict),
        "token_type": "bearer"
    }

from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env file

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

# # OAuth2 scheme for token parsing from header
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # Token not actually exposed via tokenUrl
oauth2_scheme = HTTPBearer()
# ------------------- Create JWT Token -------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> dict:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return {"username": username, "role": role}
    except JWTError:
        raise credentials_exception

# ------------------- Role Check: Admin -------------------
def admin_only(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ------------------- Role Check: Nurse -------------------
def nurse_only(user: dict = Depends(get_current_user)):
    if user["role"] != "nurse":
        raise HTTPException(status_code=403, detail="Nurse access required")
    return user


# ------------------- WebSocket Token Parser -------------------
# def get_current_user_from_token(token: str) -> dict:
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Invalid or expired token",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         role: str = payload.get("role")
#         if username is None or role is None:
#             raise credentials_exception
#         return {"username": username, "role": role}
#     except JWTError:
#         raise credentials_exception



def get_current_user_from_token(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # sanity check
        if payload.get("sub") is None or payload.get("role") is None:
            raise credentials_exception

        
        return payload   # 👈 return everything, not just username/role
    except JWTError:
        raise credentials_exception

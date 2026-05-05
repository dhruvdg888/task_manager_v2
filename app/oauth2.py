from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import database, schemas, models
import jwt
from .config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(data:dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


# Advance Authentication with JWT (refreshed access token)
def create_refresh_token(data:dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode,SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt



def verify_access_token(token:str, credential_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        id: str = payload.get("user_id")

        if id is None:
            raise credential_exception
        token_data = schemas.TokenData(id=str(id))

    except jwt.PyJWTError:
        raise credential_exception
    
    return token_data



async def get_current_user(token: str= Depends(oauth2_scheme), db: AsyncSession = Depends(database.get_db)):
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail=f"Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    token_data = verify_access_token(token, credential_exception)
    
    query = select(models.User).where(models.User.id == int(token_data.id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credential_exception
    
    return user

def verify_refresh_token(refresh_token: str, credential_exception):
        try:
         payload = jwt.decode(refresh_token,SECRET_KEY, algorithms=ALGORITHM)
         user_id = payload.get("user_id")

         if payload.get("type") != "refresh":
              raise credential_exception

        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_id


# Implementing role based access
def required_role(allowed_roles:list):

    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied")
        
        return current_user
    return role_checker
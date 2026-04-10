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


def verify_access_token(token:str, credential_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        id:str = payload.get("user_id")

        if id is None:
            raise credential_exception
        token_data = schemas.TokenData(id=str(id))

    except jwt.PyJWTError:
        return credential_exception
    
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
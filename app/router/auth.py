from fastapi import APIRouter, HTTPException, Request, status
from fastapi.params import Depends
from fastapi.security.oauth2 import OAuth2PasswordRequestForm

from app.rate_limiter import redis_rate_limiter
from .. import models
from ..database import get_db
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models, utils, oauth2
from datetime import datetime, timedelta, timezone
import jwt

router = APIRouter(tags=['Auth'])

# login rate limit
def login_rate_limit(request: Request):
    ip = request.client.host
    key = f"rate_limit:ip:{ip}:/login"
    redis_rate_limiter(key,limit=5,window=60)

@router.post("/login", response_model=schemas.Token)
# enables rate limiting for login endpoint
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db:AsyncSession = Depends(get_db), _: None = Depends(login_rate_limit)):

    result = await db.execute(select(models.User).where(models.User.email == user_credentials.username))
    user = result.scalar_one_or_none()

    #user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Credentials")
    
    if not utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Credentials")
    
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    refresh_token = oauth2.create_refresh_token(data={"user_id": user.id})

    db_token = models.RefreshToken(
        user_id = user.id,
        token = refresh_token,
        expiry= datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(db_token)
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint to refresh access token using refresh token
@router.post("/refresh-token")
async def refresh_token(data:schemas.RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    credential_exception = HTTPException(status_code=401, detail="Invalid token type")
    user_id = oauth2.verify_refresh_token(data.refresh_token, credential_exception)

    # check db
    query = select(models.RefreshToken).where(models.RefreshToken.token == data.refresh_token)
    result = await db.execute(query)
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=401, detail="Token revoked")
    
    # generate new access token
    access_token = oauth2.create_access_token({"user_id": user_id})

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(data: schemas.RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    query = select(models.RefreshToken).where(models.RefreshToken.token == data.refresh_token)
    result = await db.execute(query)
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=404, detail="Token not found")

    await db.delete(db_token)
    await db.commit()

    return {"message": "Logged out"}
from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from .. import models
from ..database import get_db
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models, utils, oauth2

router = APIRouter(prefix='/login', tags=['Login'])

@router.post("/", response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db:AsyncSession = Depends(get_db)):

    result = await db.execute(select(models.User).where(models.User.email == user_credentials.username))
    user = result.scalar_one_or_none()

    #user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Credentials")
    
    if not utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Credentials")
    
    access_token = oauth2.create_access_token(data={"user_id": user.id})

    return {"access_token": access_token, "token_type": "bearer"}
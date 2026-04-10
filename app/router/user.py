from fastapi import APIRouter
from fastapi.params import Depends
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from .. import models
from ..database import engine,get_db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models, utils, oauth2

router = APIRouter(
    prefix="/signup",
    tags=['Sign Up']
)

@router.post("/")
async def signup(user_credentials: schemas.Usersignup ,db:AsyncSession = Depends(get_db)):
    hashed_password = utils.hash_password(user_credentials.password)

    user_data = user_credentials.model_dump()
    user_data["password"] = hashed_password

    new_user = models.User(**user_data)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user
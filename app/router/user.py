from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.params import Depends
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy import select
from .. import models
from ..database import engine,get_db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models, utils, oauth2
from ..email_service import send_email
from ..celery_tasks import send_email_task


router = APIRouter(
    tags=['User']
)

@router.post("/signup")
async def signup(user_credentials: schemas.Usersignup , background_task: BackgroundTasks, db:AsyncSession = Depends(get_db)):
    hashed_password = utils.hash_password(user_credentials.password)

    user_data = user_credentials.model_dump()
    user_data["password"] = hashed_password

    new_user = models.User(**user_data)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # using Fast API in-built background task
    # background_task.add_task(send_email,
    #     to_email= user_data["email"],
    #     subject="Welcome 🎉",
    #     body="Your account has been created successfully!")

    # using celery
    # send task to queue, by using delay it is not executing the task it pushes task into Redis queue
    # 1. FastAPI calls .delay()
    # 2. Task → stored in Redis
    # 3. Worker sees task
    # 4. Worker executes function

    send_email_task.delay(
        user_data["email"],
        "Welcome 🎉",
        "Your account has been created successfully!"
    )

    return new_user

# role based user deletion only admin can delete user
@router.delete("/users/{id}")
async def delete_user(id:int, current_user = Depends(oauth2.required_role(['admin','user'])), db:AsyncSession = Depends(get_db)):
    query = select(models.User).where(models.User.id == id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id:{id} not found")
    
    await db.delete(user)
    await db.commit()

    return {"message":f"User with id: {id} deleted successfully"}



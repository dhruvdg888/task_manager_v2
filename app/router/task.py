from fastapi import APIRouter, HTTPException, status, Response, BackgroundTasks
from typing import List
from fastapi.params import Depends, Query
from sqlalchemy import or_,select,func,and_
from .. import models
from ..database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, oauth2
from datetime import datetime, timezone
import logging
import time
import json
from ..redis_client import redis_client

logger = logging.getLogger("app")
CACHE_TTL = 60 # seconds


router = APIRouter(prefix='/tasks', tags=['Tasks'])

# invalidate user cache
def invalidate_user_cache(user_id:int):
    # for tasks pattern (* represents any value after tasks:user_id:{user_id}:)
    pattern = f"tasks:user_id:{user_id}:*"
    keys = list(redis_client.scan_iter(match=pattern))

    if keys:
        redis_client.delete(*keys)
    
    redis_client.delete(f"analytics:user_id:{user_id}")
    redis_client.delete(f"dashboard:user_id:{user_id}")

    logger.info(f"cache invalidated for user : {user_id}")
    


# fetch tasks
async def get_user_tasks(db,user_id:int):
    result = await db.execute(
        select(models.Task).where(models.Task.owner_id == user_id)
    )
    return result.scalars().all()


# fetch Analytics
async def get_user_tasks_analytics(db,user_id:int):
    result = await db.execute(
        select(
            func.count(models.Task.id).label("total"),
            func.count(models.Task.id).filter(models.Task.status == "completed").label("completed"),
            func.count(models.Task.id).filter(models.Task.status == "pending").label("pending"),
            func.count(models.Task.id).filter(models.Task.priority == "high").label("high"),
            func.count(models.Task.id).filter(models.Task.priority == "medium").label("medium"),
            func.count(models.Task.id).filter(models.Task.priority == "low").label("low"),
            func.count(models.Task.id).filter(and_(models.Task.due_date < datetime.now(timezone.utc), models.Task.status != "completed")).label("overdue")
        ).where(models.Task.owner_id == user_id)
    )
    data = result.one()
    return {
    "total_tasks": data.total,
    "pending_tasks": data.pending,
    "completed_tasks": data.completed,
    "priority_counts": {
        "high": data.high,
        "medium": data.medium,
        "low": data.low
    },
    "overdue_tasks": data.overdue
    }

# background task to log task creation
def log_task_creation(user_id: int):
    logger.info(f'[Backgroung Job STARTED] user_id={user_id}')

    try:
        time.sleep(3)

        logger.info(f'Processing task creation for user {user_id}')

    except Exception as e:
        logger.error(f'[Backgroung Job ERROR] user_id={user_id} | error={str(e)}')
        return
    
    logger.info(f'[Backgroung Job COMPLETED] user_id={user_id} | Task Created sucessfully')
    



# Create task
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Task)
async def create_task(task: schemas.TaskCreate, background_tasks: BackgroundTasks ,db:AsyncSession = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    owner_id = current_user.id
    new_task = models.Task(**task.model_dump(), owner_id=int(owner_id))

    db.add(new_task)
    await db.commit()
    # after commint we are invalidating cache for that particular user
    invalidate_user_cache(user_id=owner_id)
    await db.refresh(new_task)

    background_tasks.add_task(log_task_creation, owner_id)

    return new_task

# task cache key
def build_tasks_cache_key(user_id:int,limit:int,offset:int,search:str,status:str,priority:str):
    return f"tasks:user_id{user_id}:limit:{limit}:offset:{offset}:search:{search}:status:{status}:priority:{priority}"

# Internal utility function for getting tasks with filters
async def _get_user_tasks_filtered(db, user_id: int, status: str = None, priority: str = None, search: str = None, limit: int = 10, offset: int = 0):
    # creating cache key
    cache_key = build_tasks_cache_key(user_id=user_id, limit=limit, offset=offset, search=search, status=status, priority=priority)

    #checking cache
    cached_task = redis_client.get(cache_key)
    if cached_task:
        logger.info("Cache HIT")
        return json.loads(cached_task)
    
    query = select(models.Task).where(models.Task.owner_id == user_id)

    if status:
        query = query.where(models.Task.status == status)
    
    if priority:
        query = query.where(models.Task.priority == priority)
    
    if search:
        query = query.where(
            or_(
                models.Task.title.ilike(f"%{search}%"),
                models.Task.description.ilike(f"%{search}%")
            )
        )
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    tasks = result.scalars().all()
    #setting data in cache with TTL
    tasks_data = [schemas.Task.model_validate(t).model_dump() for t in tasks]
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(tasks_data, default=str))
    logger.info("Cache MISS")
    return tasks


# Get all tasks for the current user 
# applied filters
@router.get("/", response_model=List[schemas.Task])
async def get_all_tasks(status:str = Query(None),priority:str = Query(None), search:str = Query(None), limit: int = Query(10), offset: int = Query(0),db: AsyncSession = Depends(get_db),current_user = Depends(oauth2.get_current_user)):
    return await _get_user_tasks_filtered(db, int(current_user.id), status, priority, search, limit, offset)


# Get the analytics of overall tasks
# Applied role based access only premium user can see analytics
@router.get("/analytics", response_model=schemas.TaskAnalytics)
async def get_analysis(db:AsyncSession = Depends(get_db), current_user = Depends(oauth2.required_role(['premium-user','user']))):
    # cache key
    analytics_cache_key = f"analytics:user_id:{current_user.id}"
    cached_analytics = redis_client.get(analytics_cache_key)
    # cache_check
    if cached_analytics:
        logger.info("Analytics Cache HIT")
        return json.loads(cached_analytics)
    analytics = await get_user_tasks_analytics(db, current_user.id)
    # Setting analytics data in cache with TTL
    analytics_data = schemas.TaskAnalytics.model_validate(analytics).model_dump()
    redis_client.setex(analytics_cache_key, CACHE_TTL, json.dumps(analytics_data, default=str))
    logger.info("Analytics Cache MISS")
    return analytics


# Get the dashboard
@router.get("/dashboard", response_model=schemas.Dashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    user_id = current_user.id
    # cache key
    dashboard_cache_key = f"dashboard:user_id:{user_id}"
    dashboard_cache_data = redis_client.get(dashboard_cache_key)
    
    # checking cache data for dashboard
    if dashboard_cache_data:
        logger.info("Dashboard Cache HIT")
        return json.loads(dashboard_cache_data)

    # Execute sequentially instead of concurrently to avoid "another operation in progress" error
    tasks = await _get_user_tasks_filtered(db, user_id)
    analytics = await get_user_tasks_analytics(db, user_id)


    # setting data to cahce memory
    dashboard = {
        "tasks": tasks,
        "analytics": analytics
    }
    dashboard_data = schemas.Dashboard.model_validate(dashboard).model_dump()
    redis_client.setex(dashboard_cache_key, CACHE_TTL, json.dumps(dashboard_data, default=str))
    logger.info("Dashboard Cache MISS")

    return dashboard

# Get single task based on task id
@router.get("/{id}", response_model=schemas.Task)
async def get_task(id:int, db:AsyncSession = Depends(get_db), current_user = Depends(oauth2.get_current_user)):

    query = select(models.Task).where(models.Task.id == int(id), models.Task.owner_id == current_user.id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"task with id {id} doesn't not exist")
    return task


# Update task (only owner can update the task)
@router.put("/{id}", response_model=schemas.Task)
async def update_task(task: schemas.TaskUpdate, id:int, db:AsyncSession = Depends(get_db), current_user = Depends(oauth2.get_current_user)):

     query = select(models.Task).where(models.Task.id == int(id))
     result = await db.execute(query)

     existing_task = result.scalar_one_or_none()

     if existing_task == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {id} doesn't exist")

     if current_user.id != task.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'You can not update task with id {id}')
     
     for key, value in task.model_dump(exclude_unset=True).items():
        setattr(existing_task, key, value)

     await db.commit()
     # after updating invalidating the cache memory for that user
     invalidate_user_cache(user_id=current_user.id)
     await db.refresh(existing_task)

     return existing_task

# Delete a task (only owner can delete)
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(id:int, db:AsyncSession = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    
    query = select(models.Task).where(models.Task.id == id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if task == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {id} does not exist")
    
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"You are not the owner of this task")
    
    await db.delete(task)

    await db.commit()
    # after deleting invalidating the cache memory for that user
    invalidate_user_cache(user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

    
# Mark task complete
@router.patch("/{id}", response_model=schemas.TaskBase)
async def mark_as_complete(id: int, db:AsyncSession = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    query = select(models.Task).where(models.Task.id == id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if task.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"You are not the owner of this task")
    
    task.status = "completed"

    await db.commit()
    await db.refresh(task)

    return task

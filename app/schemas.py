from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class Usersignup(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id : Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    # to display our ORM response
    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    title: str
    description: Optional[str]
    priority: Optional[str]
    status: Optional[str]
    due_date: datetime

# request
class TaskCreate(TaskBase):
    pass 

#update
class TaskUpdate(TaskBase):
    owner_id: int

# response
class Task(TaskBase):
    id: int
    owner_id: int
    created_at: datetime
    owner: UserOut

     # to display our ORM response
    model_config = ConfigDict(from_attributes=True)

# analytics response
class TaskAnalytics(BaseModel):
    total_tasks: int
    pending_tasks: int
    completed_tasks: int
    priority_counts: dict
    overdue_tasks: int

# dashboard
class Dashboard(BaseModel):
    tasks: list[Task]
    analytics: TaskAnalytics
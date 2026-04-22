from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True,nullable=False)
    email = Column(String,nullable=False,unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer,primary_key=True,nullable=False)
    title = Column(String,nullable=False)
    description = Column(String,nullable=True)
    priority = Column(String,server_default=text("'low'"))
    status = Column(String,server_default=text("'pending'"))
    due_date = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now() + interval '7 days'"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    owner = relationship("User")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    token = Column(String)
    expiry = Column(TIMESTAMP(timezone=True))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

SQLALCHEMY_DATABASE_URL = f'postgresql+asyncpg://{settings.database_username}:{settings.database_password}@{settings.database_hostname}/{settings.database_name}'

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(bind=engine,class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

#setting up function to get the DB
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
    
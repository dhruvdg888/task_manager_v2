from fastapi import FastAPI
from .router import auth, user, task
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# here for all the domains (global)
origins = ["*"]

#to allow CORS (Cross Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# use this when not using Alembic
#models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(task.router)

@app.get("/")
async def root():
    return {"message":"Welcome to Task Manager App"}


    


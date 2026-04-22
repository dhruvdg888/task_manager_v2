from fastapi import FastAPI, Request
from .router import auth, user, task
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()

logger = logging.getLogger("app")

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

# Logging middleware
# it runs when we get a request by this we track everything
@app.middleware("http")
async def logging_middleware(request:Request, call_next):
    start_time = time.time()

    method = request.method
    path = request.url.path

    try:
        response = await call_next(request)
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"METHOD: {method} | PATH: {path} | STATUS: ERROR | TIME: {process_time:.2f}ms")
        raise e
    
    process_time = (time.time() - start_time) * 1000
    logger.info(f"METHOD: {method} | PATH: {path} | STATUS: {response.status_code}| TIME: {process_time:.2f}ms")

    return response


# use this when not using Alembic
#models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(task.router)

@app.get("/")
async def root():
    return {"message":"Welcome to Task Manager App"}


    


from fastapi import HTTPException, status, Request
import time
from .redis_client import redis_client

# redis based rate limiting ( RATE LIMITING )
def redis_rate_limiter(key:str,limit:int=5,window:int = 60):
    current_time = int(time.time())
    window_start = current_time - window

    # Step 1: remove old requests
    redis_client.zremrangebyscore(key,0,window_start)

    # Step 2: count requests in window
    request_count = redis_client.zcard(key)

    if request_count >= limit:
        oldest_request = redis_client.zrange(key,0,0,withscores=True)

        if oldest_request:
            oldest_time = int(oldest_request[0][1])
            retry_after = window - (current_time - oldest_time)
        else:
            retry_after = window
        raise HTTPException(
            status_code= status.HTTP_429_TOO_MANY_REQUESTS, detail={
                "success" : False,
                "error": {
                    "message": "Too many requests",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": retry_after
                }
            }
        )
    
    # Step 3: add current request
    redis_client.zadd(key, {str(current_time): current_time})

    # Step 4: set expiry
    redis_client.expire(key,window)
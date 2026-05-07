from .celery_app import celery_app
from .email_service import send_email

# converts function into async background task Now this function:is NOT called directly and is sent to queue
#with out tries
# @celery_app.task
# def send_email_task(to_email: str, subject: str, body: str):
#         send_email(to_email,subject,body)

    
# with retries
@celery_app.task(bind=True, max_retries=3)
def send_email_task(self,to_email: str, subject: str, body: str):
    try:
        send_email(to_email,subject,body)
    except Exception as e:
        self.retry(exc=e,countdown=5)



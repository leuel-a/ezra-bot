#!/usr/bin/env python3
import os
import sys
import logging

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv


load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t  %(message)s")

APP_HOST = os.getenv("APP_HOST", "None")
APP_PORT = int(os.getenv("APP_PORT", "5000"))

app = FastAPI()


@app.get('/', summary="root of application")
async def root():
    return { "message": "Hello, World!" }


@app.post('/github-webhook', summary="Webhook deliveries")
async def webhook(request: Request):
    githubEvent = request.headers.get('x-github-event', None)

    if githubEvent is None:
        raise HTTPException(status_code=400, detail="Missing X-Github-Event header")

    print(await request.json())
    logging.info(f"Recieved Github Event: {githubEvent}")
    return { "message": "Hello World" }

# const data = request.body;
#    const action = data.action;
#    if (action === 'opened') {
#      console.log(`An issue was opened with this title: ${data.issue.title}`);
#    } else if (action === 'closed') {
#      console.log(`An issue was closed by ${data.issue.user.login}`);
#    } else {
#      console.log(`Unhandled action for the issue event: ${action}`);
#    }

if __name__ == '__main__':
    uvicorn.run(
            "client.app:app",
            host=APP_HOST,
            port=APP_PORT,
            log_level="info"
        )

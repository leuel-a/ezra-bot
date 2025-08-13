#!/usr/bin/env python3
import os
import sys
import logging

import uvicorn
from fastapi import FastAPI, Request
from dotenv import load_dotenv


load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t  %(message)s")

from client.services.github import get_comments_by_url

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
ENV = os.getenv("ENV", "development")

app = FastAPI()


@app.get('/', summary="root of application")
async def root():
    return { "message": "Hello, World!" }


@app.post('/github-webhook', summary="Webhook deliveries")
async def webhook(request: Request):
    githubEvent = request.headers.get('x-github-event', None)

    logging.info(f"(GITHUB-WEBHOOK-EVENT) Recieved Content-Type: {request.headers.get('content-type')}")

    payload = await request.json()
    githubCurrentAction = payload.get('action', None)

    if githubEvent == 'issue_comment':
        issue = payload.get("issue")
        commentor = issue.get("user")

        logging.info(f"(GITHUB-WEBHOOK-EVENT) Comment Author: {commentor.get('login')}")
        logging.info(f"(GITHUB-WEBHOOK-EVENT) Issue Comments URL: {issue.get('comment_url')}")

        _ = get_comments_by_url(issue.get("comment_url", ""))
        logging.info(f"(GITHUB-WEBHOOK-EVENT) Issue Comment Title {issue.get('title')}")

    logging.info(f"(GITHUB-WEBHOOK-EVENT) Event Name: {githubEvent}")
    logging.info(f"(GITHUB-WEBHOOK-EVENT) Event Action Name: {githubCurrentAction}")

    return { "message": "Hello World" }


if __name__ == '__main__':
    IS_DEVELOPMENT = ENV == "development"

    logging.info(f"Running application in {ENV.capitalize()} enviroment")
    if IS_DEVELOPMENT:
        uvicorn.run(
                "client.app:app",
                host=HOST,
                port=PORT,
                log_level="info",
                reload=ENV == "development"
            )

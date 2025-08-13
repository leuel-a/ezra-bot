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

APP_HOST = os.getenv("APP_HOST", "None")
APP_PORT = int(os.getenv("APP_PORT", "5000"))
API_BASE_URL = os.getenv("API_BASE_URL")
GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_API_TOKEN', '')

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

        _ = get_comments_by_url(issue.get('comment_url'), '')
        logging.info(f"(GITHUB-WEBHOOK-EVENT) Issue Comment Title {issue.get('title')}")

    logging.info(f"(GITHUB-WEBHOOK-EVENT) Event Name: {githubEvent}")
    logging.info(f"(GITHUB-WEBHOOK-EVENT) Event Action Name: {githubCurrentAction}")

    return { "message": "Hello World" }


if __name__ == '__main__':
    uvicorn.run(
            "client.app:app",
            host=APP_HOST,
            port=APP_PORT,
            log_level="info",
            reload=True
        )

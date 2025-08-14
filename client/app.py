#!/usr/bin/env python3
import os
import sys
import logging

import uvicorn
from pprint import pprint
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv


load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t  %(message)s")

from client.services import github

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
ENV = os.getenv("ENV", "development")

app = FastAPI()


@app.get('/', summary="root of application")
async def root():
    return { "message": "Hello, World!" }


@app.get('/github/get_authenticated_app')
async def github_get_authenticated_app():
    try:
        access_token = github.get_github_app_access_token()
        return { "access_token": access_token }
    except Exception as e:
        logging.error(f"Error while trying to get authenticated application {e}")
        raise HTTPException(
                    status_code=500,
                    detail="Failed to generated authentication token for github app"
                )


@app.post('/github-webhook', summary="Webhook deliveries")
async def github_webhook(request: Request):
    githubEvent = request.headers.get('x-github-event', None)

    logging.info(f"(GITHUB-WEBHOOK-EVENT) Recieved Content-Type: {request.headers.get('content-type')}")

    payload = await request.json()
    githubCurrentAction = payload.get('action', None)

    logging.info(f"(GITHUB-WEBHOOK-EVENT) Event Name: {githubEvent}")
    logging.info(f"(GITHUB-WEBHOOK-EVENT) Event Action Name: {githubCurrentAction}")

    if githubEvent == "issue_comment":
        issue = payload.get("issue")
        logging.info(f"(GITHUB-WEBHOOK-EVENT) Issue Comments URL: {issue.get('comments_url')}")

        comments_url = issue.get("comments_url")
        comments = github.get_comments_by_url(comments_url)

        last_comment = comments[-1]
        pprint(last_comment)

        if comments[-1].get("performed_via_github_app", None) == None:
            github.respond_to_current_comment_thread(comments_url)

        logging.info(f"(GITHUB-WEBHOOK-EVENT) Issue Comment Title {issue.get('title')}")

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

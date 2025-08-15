#!/usr/bin/env python3
import os
import sys
import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t  %(message)s")

from core import utils
from core.agent import graph
from core.state import AgentState
from client.services import github

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
ENV = os.getenv("ENV", "development")

app = FastAPI()


@app.post('/github-webhook', summary="Webhook deliveries")
async def webhook(request: Request):
    github_event = request.headers.get('x-github-event', None)
    logging.info(f"(GITHUB-WEBHOOK-EVENT) Received Event: {github_event}")

    if github_event == "ping":
        logging.info("(GITHUB-WEBHOOK-EVENT) This is a test event that github sends")
        return JSONResponse(content={"message": "Content Received"}, status_code=status.HTTP_202_ACCEPTED)

    payload = await request.json()
    github_current_action = payload.get('action', None)

    logging.info(f"(GITHUB-WEBHOOK-PAYLOAD) Received Event-Action: {github_event}:{github_current_action}")

    issue = payload.get("issue")
    issue_url = issue.get("url", "")

    comments_url = issue.get("comments_url", "")

    messages = []
    try:
        logging.info(f"Getting Issue Comments with URL: {comments_url}")
        comments = github.get_data_from_github(comments_url)
        messages = utils.construct_messages_from_comments(comments)
    except Exception as e:
        logging.exception(f"Failed to get comments for url {comments_url}: {e}")
        return JSONResponse(content={"message": f"Unable to get comments from url {comments_url}"}, status_code=status.HTTP_400_BAD_REQUEST)

    github_event_action = f"{github_event}:{github_current_action}"
    input_payload: AgentState = {
        "issue_url": issue_url,
        "comments_url": comments_url,
        "event_action": github_event_action,
        "valid_description_on_issue": True,
        "validation_error_reasons": [],
        "messages": messages,
        "should_continue": True,
    }

    if not utils.check_last_message_is_a_bot(messages):
        graph.invoke(input_payload)
    return JSONResponse(content={"message": "Content received"}, status_code=status.HTTP_202_ACCEPTED)


if __name__ == '__main__':
    IS_DEVELOPMENT = ENV == "development"

    logging.info(f"Running application in {ENV.capitalize()} Environment")
    if IS_DEVELOPMENT:
        uvicorn.run(
                "client.app:app",
                host=HOST,
                port=PORT,
                log_level="info",
                reload=ENV == "development"
            )

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

from core.agent import graph
from core.state import AgentState

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
ENV = os.getenv("ENV", "development")

app = FastAPI()


@app.post('/github-webhook', summary="Webhook deliveries")
async def webhook(request: Request):
    github_event = request.headers.get('x-event', None)

    logging.info(f"(GITHUB-WEBHOOK-EVENT) Received Content-Type: {request.headers.get('content-type')}")

    payload = await request.json()
    github_current_action = payload.get('action', None)

    issue = payload.get("issue")

    if issue is None:
        return JSONResponse(content={"message": "Content received"}, status_code=status.HTTP_202_ACCEPTED)

    issue_url = issue.get("url")

    comments_url = issue.get('comments_url')
    github_event_action = f"{github_event}:{github_current_action}"

    input_payload: AgentState = {
        "comments_url": comments_url,
        "issue_url": issue_url,
        "messages": [],
        "event_action": github_event_action
    }
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

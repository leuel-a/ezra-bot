import os
import jwt
import time
import logging
from typing import List
from langchain_core.messages import AIMessage, HumanMessage, AnyMessage

import requests

EZRA_PRIVATE_KEY = os.getenv("EZRA_PRIVATE_KEY", "")
EZRA_GITHUB_APP_CLIENT_ID = os.getenv("EZRA_GITHUB_APP_CLIENT_ID", "")
API_BASE_URL = os.getenv("API_BASE_URL")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "")
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_API_TOKEN", "")

headers_without_authorization = {
    "Accept": "application/vnd.github+json",
    "X-Github-Api-Version": "2022-11-28",
}

github_issue_labels = {
    "needs_reproduction": "Needs Reproduction",
}

def generate_jwt_token_for_github_app() -> str:
    """Generates a JSON Web Token (JWT) for authenticating as a GitHub App.
    :returns: The encoded JWT, suitable for authenticating with the GitHub API.
    """
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": EZRA_GITHUB_APP_CLIENT_ID
    }

    encoded_token = jwt.encode(payload, EZRA_PRIVATE_KEY, algorithm="RS256")
    return encoded_token


def get_github_app_access_token():
    """Fetches the GitHub App access token.
    :returns: Installation-specific GitHub App access token.
    :rtype: str
    """
    jwt_token = generate_jwt_token_for_github_app()

    logging.info("Successfully generated JWT token with Private Key")

    url = f"{GITHUB_API_URL}/app/installations"
    logging.info(f"Making API Call to Github to get installation ID with URL: {url}")

    request_headers = { **headers_without_authorization, "Authorization": f"Bearer {jwt_token}" }
    response = requests.get(url, headers=request_headers)
    response.raise_for_status()

    app_installations = response.json()

    installation_id = None
    for installation in app_installations:
        if installation.get("client_id", None) == EZRA_GITHUB_APP_CLIENT_ID:
            installation_id = installation.get("id", None)

    logging.info(f"Got Installation Id for Github App: {installation_id}")
    installation_access_tokens_url = f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens"

    logging.info(f"Making API Call to Github to get installation access tokens with URL: {installation_access_tokens_url}")
    response = requests.post(installation_access_tokens_url, headers=request_headers)
    response.raise_for_status()

    access_token = response.json().get('token')
    return access_token


def check_if_comment_is_made_by_agent(comment: dict) -> bool:
    """Checks if comment is made by an agent

    :param comment: the comment that is going to be checked
    :ptype: str
    :retruns: True if the comment is made by agent, else False
    """
    try:
        performed_by_github_app = comment.get("performed_via_github_app.id", None)

        if performed_by_github_app is None:
            return False

        return performed_by_github_app.get("id", None) is None
    except Exception:
        return False


def get_issue_comments(comments_url: str | None) -> List[dict]:
    """Fetch comments for the issue
    :returns: A list of raw comment dicts (as received from GitHub).
    """
    if comments_url is None:
        return []

    try:
        access_token = get_github_app_access_token()
        headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}

        response = requests.get(comments_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list):
            logging.info("Fetched %d comment(s) for conversation analysis", len(data))
            return []

        logging.warning("Comments returned as an empty string or is not an instance of a list")
        return []
    except Exception as e:
        logging.exception(f"Failed to fetch comments {e}")
        return []



def is_github_bot_comment(comment: dict) -> bool:
    """Heuristics to identify if a comment appears to be authored by a GitHub app/bot.
    """
    user = (comment or {}).get("user") or {}
    login = (user.get("login") or "").lower()
    user_type = (user.get("type") or "").lower()
    performed_via_app = (comment or {}).get("performed_via_github_app")

    if performed_via_app:
        return True
    if user_type == "bot":
        return True
    if login.endswith("[bot]") or login.endswith("-bot") or "bot" in login:
        return True
    return False


def post_issue_comment(comments_url: str | None, body: str) -> bool:
    """
    Posts an issue comment, provided the comments_url and body
    """
    if comments_url is None:
        return False

    access_token = get_github_app_access_token()
    headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    payload = {"body": body}

    try:
        response = requests.post(comments_url, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        logging.exception("Failed to create GitHub issue comment: %s", e)
        return False
    return True


def construct_messages_from_comments(comments: List[dict]) -> List[AnyMessage]:
    """Construct Messages from Comments For LLMs"""
    messages = []

    for comment in comments:
        comment_body = comment.get('body', '')
        is_bot_comment = is_github_bot_comment(comment)

        if is_bot_comment:
            messages.append(AIMessage(content=comment_body))
        else:
            messages.append(HumanMessage(content=comment_body))
    return messages

def check_last_message_is_a_bot(messages: List[AnyMessage]):
    if len(messages) == 0:
        return False
    return isinstance(messages[-1], AIMessage)

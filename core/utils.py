import os
import jwt
import time
import logging

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

    logging.info(f"Recieved response with text content: {response.text}")
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


def check_if_issue_comment_is_made_by_agent(issue: dict):
    try:
        performed_by_github_app = issue.get("performed_via_github_app.id", None)

        if performed_by_github_app is None:
            return False

        return performed_by_github_app.get("id", None) is None
    except Exception as e:
        return False

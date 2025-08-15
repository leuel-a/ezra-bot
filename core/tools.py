import logging
import requests
from core import utils
from core.utils import headers_without_authorization
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool


@tool
def get_data_from_github(url: str):
    """
    Use this tool when:
        - You need to retrieve information from GitHub for processing or display.
        - You have the exact API URL for the resource you want to access.
        - You need to read details of issues, pull requests, repositories, 
          comments, workflows, or other GitHub resources.
    """
    logging.info("(TOOL_CALL) Get Data from GitHub")
    access_token = utils.get_github_app_access_token()

    request_headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=request_headers)

    response.raise_for_status()
    return response.json()


@tool
def post_issue_comment_on_github(comments_url: str, body: str):
    """
    Use this tool when:
        - The task requires adding, create a comment to an existing GitHub issue
        - You already have both the `comments_url` and the desired comment body.
    """
    logging.info("(TOOL_CALL) Post Issue Comment on GitHub")
    access_token = utils.get_github_app_access_token()
    headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    payload = {"body": body}

    try:
        response = requests.post(comments_url, json=payload, headers=headers)
        response.raise_for_status()

        logging.info(f"Successfully created a new comment for this issue on {comments_url}")
    except Exception as e:
        logging.exception(f"Failed to create a new comment for this issue on {comments_url}: {e}")


tool_node = ToolNode(tools=[get_data_from_github, post_issue_comment_on_github])


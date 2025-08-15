import logging
import requests
from core import utils
from core.utils import headers_without_authorization
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool


@tool
def get_data_from_github(url: str):
    """Use this tool to get, search, or post data to GitHub when a task requires interacting with GitHub."""
    access_token = utils.get_github_app_access_token()

    request_headers = {**headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=request_headers)

    response.raise_for_status()
    return response.json()



tool_node = ToolNode(tools=[get_data_from_github])


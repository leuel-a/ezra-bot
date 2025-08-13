import os
import logging
import requests


API_BASE_URL = os.getenv("API_BASE_URL")
GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_API_TOKEN', '')
headers = {
        "Accept": "application/vnd.github+json",
        "X-Github-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {GITHUB_ACCESS_TOKEN}"
    }


def get_comments_by_url(url: str):
    """Fetches comments from a given GitHub API URL.

    This function sends an HTTP GET request to the provided URL to retrieve
    a list of comments, likely from a GitHub issue or pull request. It
    utilizes globally defined headers for authentication with the GitHub API.

    :param url: The full API URL to fetch comments from.
    :return: A list of comment objects returned by the API.
    :rtype: list
    """
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        comments = response.json()
        return comments
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve comments from {url}. Error: {e}")
        return []

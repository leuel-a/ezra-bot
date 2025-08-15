import requests
from core import utils


def get_data_from_github(url: str):
    """
    Retrieves data from GitHub using the provided API URL.

    :param url: The url to use to get the data from GitHub
    :ptype: str

    :returns: The data from GitHub
    """
    access_token = utils.get_github_app_access_token()

    request_headers = {**utils.headers_without_authorization, "Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=request_headers)

    response.raise_for_status()
    return response.json()

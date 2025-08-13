from typing import Optional
from pydantic import BaseModel, HttpUrl

class Reactions(BaseModel):
    plus_1: int = 0
    minus_1: int = 0
    confused: int = 0
    eyes: int = 0
    heart: int = 0
    hooray: int = 0
    laugh: int = 0
    rocket: int = 0
    total_count: int
    url: HttpUrl

    class Config:
        fields = {
            'plus_1': '+1',
            'minus_1': '-1'
        }

class User(BaseModel):
    login: str
    id: int
    node_id: str
    avatar_url: HttpUrl
    gravatar_id: str
    html_url: HttpUrl
    followers_url: HttpUrl
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: HttpUrl
    organizations_url: HttpUrl
    repos_url: HttpUrl
    events_url: str
    received_events_url: HttpUrl
    site_admin: bool
    type: str
    user_view_type: Optional[str] = None
    url: HttpUrl

class IssueComment(BaseModel):
    id: int
    node_id: str
    url: HttpUrl
    html_url: HttpUrl
    issue_url: HttpUrl
    body: str
    user: User
    created_at: str
    updated_at: str
    author_association: str
    performed_via_github_app: Optional[dict] = None
    reactions: Reactions

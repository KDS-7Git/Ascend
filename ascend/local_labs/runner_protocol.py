"""Data-only runner contract shared with the web client; no provider imports."""

from urllib.request import HTTPRedirectHandler

from pydantic import BaseModel, ConfigDict, Field

ACTIONS = frozenset(
    {"start", "check", "stop", "resume", "finish", "destroy", "save", "http", "router"}
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_id: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=256)
    content: str | None = Field(default=None, max_length=262144)
    target: str | None = Field(default=None, max_length=100)
    path: str = Field(default="/", max_length=2048)
    method: str = Field(default="GET", max_length=10)
    body: str = Field(default="", max_length=65536)
    token: str = Field(default="", max_length=4096)
    commands: list[str] | None = Field(default=None, max_length=40)

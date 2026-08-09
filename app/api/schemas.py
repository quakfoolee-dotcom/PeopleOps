from typing import Literal

from pydantic import BaseModel, Field

ComponentState = Literal["ready", "planned", "not_configured", "error"]


class ComponentStatus(BaseModel):
    status: ComponentState
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_name: str
    version: str
    environment: str
    release_sha: str
    components: dict[str, ComponentStatus] = Field(default_factory=dict)

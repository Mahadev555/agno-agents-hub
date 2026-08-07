"""
Typed agent configuration.

Configs used to be `Dict[str, Any]` validated nowhere, with defaults hand-patched
in the HTTP layer and bypassed entirely by the seeder. This module is the single
definition: the API, the seeder, and the runtime all get the same defaults and
the same validation.

Naming note: the stored blob calls the LLM section `model_config`, which is a
*reserved attribute name in Pydantic v2*. The field is called `model` here and
`model_config` is still accepted (and written) for compatibility with existing
rows. New code should use `model`.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from runtime.registry import available_models, is_known_model_type, validate_tools

# Bump when the stored shape changes in a way that needs migrating. Persisted
# with every config so old rows stay identifiable.
CURRENT_SCHEMA_VERSION = 1

DEFAULT_MODEL_ID = "gemini-2.5-flash-lite"
DEFAULT_MODEL_TYPE = "google"


class ModelConfig(BaseModel):
    """LLM settings for an agent or team coordinator."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(default=DEFAULT_MODEL_TYPE, description="Provider key")
    id: str = Field(default=DEFAULT_MODEL_ID, description="Provider model id")
    max_tokens: Optional[int] = Field(default=None, gt=0, le=200_000)
    api_version: Optional[str] = None
    additional_params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _known_provider(cls, value: str) -> str:
        if not is_known_model_type(value):
            raise ValueError(
                f"Unknown model type '{value}'. Supported: {available_models()}"
            )
        return value


class MCPConfig(BaseModel):
    """Connection settings for an MCP-backed agent."""

    model_config = ConfigDict(extra="allow")

    url: str = Field(default="http://localhost:3001/sse")
    transport: Literal["sse", "stdio", "streamable-http"] = "sse"
    timeout_seconds: int = Field(default=300, gt=0, le=3600)
    additional_params: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """
    The full configuration blob stored on an agent row.

    Unknown keys are rejected rather than silently carried, so a typo like
    `instuctions` fails at create time instead of producing an agent that
    quietly ignores its instructions.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = CURRENT_SCHEMA_VERSION

    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    role: str = "Assistant"

    # Accepts a single string or a list; normalized to a list.
    instructions: List[str] = Field(default_factory=list)

    tools: List[str] = Field(default_factory=list)

    # `model` is the field; `model_config` is the legacy alias on the wire.
    model: ModelConfig = Field(default_factory=ModelConfig)

    markdown: bool = True
    show_tool_calls: bool = True
    additional_params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("instructions", mode="before")
    @classmethod
    def _normalize_instructions(cls, value: Any) -> List[str]:
        """Older rows store instructions as a bare string."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        raise ValueError("instructions must be a string or a list of strings")

    @field_validator("tools")
    @classmethod
    def _known_tools(cls, value: List[str]) -> List[str]:
        # Fail here, at write time, rather than when a user runs the agent.
        validate_tools(value)
        return value

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_model_config(cls, data: Any) -> Any:
        """
        Consume the legacy `model_config` key.

        to_storage() writes the LLM section under both names, so this must pop
        `model_config` unconditionally: leaving it behind would trip
        extra="forbid" when re-reading a config this code wrote itself.
        """
        if isinstance(data, dict) and "model_config" in data:
            data = dict(data)
            legacy = data.pop("model_config")
            data.setdefault("model", legacy)
        return data

    def to_storage(self) -> Dict[str, Any]:
        """
        Serialize for the JSONB column.

        Writes the LLM section under both `model` and `model_config` so rows
        stay readable by any code still expecting the old key.
        """
        payload = self.model_dump(mode="json")
        payload["model_config"] = payload["model"]
        return payload


def parse_agent_config(
    raw: Optional[Dict[str, Any]],
    fallback_name: str,
    fallback_description: Optional[str] = None,
) -> AgentConfig:
    """
    Build a validated AgentConfig from a raw dict.

    Fills name/description from the agent row when the blob omits them, which is
    what the create endpoint used to do by hand.

    Raises:
        pydantic.ValidationError: surfaced by callers as a 400.
    """
    data = dict(raw or {})
    data.setdefault("name", fallback_name)
    if fallback_description and not data.get("description"):
        data["description"] = fallback_description
    return AgentConfig(**data)


class TeamConfig(BaseModel):
    """Configuration for a coordinator (host) agent."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = CURRENT_SCHEMA_VERSION

    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    mode: Literal["route", "coordinate", "collaborate"] = "coordinate"
    instructions: List[str] = Field(default_factory=list)
    model: ModelConfig = Field(default_factory=ModelConfig)
    additional_params: Dict[str, Any] = Field(default_factory=dict)

    _normalize_instructions = field_validator("instructions", mode="before")(
        AgentConfig._normalize_instructions.__func__
    )

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_model_config(cls, data: Any) -> Any:
        """See AgentConfig._accept_legacy_model_config."""
        if isinstance(data, dict) and "model_config" in data:
            data = dict(data)
            legacy = data.pop("model_config")
            data.setdefault("model", legacy)
        return data

    def to_storage(self) -> Dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["model_config"] = payload["model"]
        return payload


def parse_team_config(
    raw: Optional[Dict[str, Any]],
    fallback_name: str,
    fallback_mode: str = "coordinate",
) -> TeamConfig:
    """Build a validated TeamConfig, filling gaps from the row."""
    data = dict(raw or {})
    data.setdefault("name", fallback_name)
    data.setdefault("mode", fallback_mode)
    return TeamConfig(**data)

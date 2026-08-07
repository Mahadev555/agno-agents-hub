"""
Registries for tools and model providers.

Both used to be hardcoded dicts inside the agent factory, where an unknown tool
name was silently dropped and an unknown model type silently became Gemini. An
agent configured with a typo produced a working-looking agent that quietly did
less than asked.

Registering here gives one place to add capabilities and one place to validate
against, so a bad name is rejected when an agent is *saved* rather than when a
user runs it days later.
"""

from typing import Any, Callable, Dict, List, Optional

# ----------------------------- tools -----------------------------

# name -> zero-arg factory. Factories, not instances, so each agent gets its own
# tool object instead of sharing one across the process.
_TOOL_REGISTRY: Dict[str, Callable[[], Any]] = {}


def register_tool(name: str):
    """Decorator registering a tool factory under a config name."""

    def decorator(factory: Callable[[], Any]) -> Callable[[], Any]:
        if name in _TOOL_REGISTRY:
            raise ValueError(f"Tool '{name}' is already registered")
        _TOOL_REGISTRY[name] = factory
        return factory

    return decorator


@register_tool("duckduckgo")
def _duckduckgo():
    from agno.tools.duckduckgo import DuckDuckGoTools

    return DuckDuckGoTools()


def available_tools() -> List[str]:
    """Every registered tool name, sorted."""
    return sorted(_TOOL_REGISTRY)


def validate_tools(names: Optional[List[str]]) -> None:
    """
    Raise if any name is not registered.

    Called from the config schema, so this runs on create/update rather than at
    execution time.
    """
    if not names:
        return
    unknown = [n for n in names if n not in _TOOL_REGISTRY]
    if unknown:
        raise ValueError(
            f"Unknown tool(s) {unknown}. Registered tools: {available_tools()}"
        )


def build_tools(names: Optional[List[str]]) -> List[Any]:
    """Instantiate tools by name. Assumes names were already validated."""
    if not names:
        return []
    validate_tools(names)
    return [_TOOL_REGISTRY[name]() for name in names]


# ---------------------------- models -----------------------------

# Provider key -> builder taking the validated model settings.
_MODEL_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register_model(name: str):
    """Decorator registering a model-provider builder."""

    def decorator(builder: Callable[..., Any]) -> Callable[..., Any]:
        if name in _MODEL_REGISTRY:
            raise ValueError(f"Model provider '{name}' is already registered")
        _MODEL_REGISTRY[name] = builder
        return builder

    return decorator


@register_model("google")
def _google(model_id: str, max_tokens: Optional[int], extra: Dict[str, Any], **_):
    from agno.models.google import Gemini

    # Gemini names the cap max_output_tokens, not max_tokens.
    if max_tokens:
        return Gemini(id=model_id, max_output_tokens=max_tokens, **extra)
    return Gemini(id=model_id, **extra)


@register_model("openai")
def _openai(model_id: str, max_tokens: Optional[int], extra: Dict[str, Any], **_):
    from agno.models.openai import OpenAIChat

    return OpenAIChat(id=model_id, max_tokens=max_tokens, **extra)


@register_model("azure")
def _azure(
    model_id: str,
    max_tokens: Optional[int],
    extra: Dict[str, Any],
    api_version: Optional[str] = None,
    **_,
):
    import os

    from agno.models.azure import AzureOpenAI

    return AzureOpenAI(
        id=model_id if model_id.startswith("gpt") else "gpt-4o",
        max_tokens=max_tokens or 16384,
        api_version=api_version or os.getenv("AZURE_OPENAI_API_VERSION"),
        **extra,
    )


def available_models() -> List[str]:
    """Every registered provider key, sorted."""
    return sorted(_MODEL_REGISTRY)


def is_known_model_type(name: str) -> bool:
    """Whether a provider key is registered. Derived, never a parallel list."""
    return name in _MODEL_REGISTRY


def build_model(model_settings: Dict[str, Any]) -> Any:
    """
    Instantiate a model from validated settings.

    Unlike the old factory, an unrecognised provider raises instead of quietly
    returning a Gemini model.
    """
    settings = dict(model_settings or {})
    model_type = settings.get("type", "google")

    builder = _MODEL_REGISTRY.get(model_type)
    if builder is None:
        raise ValueError(
            f"Unknown model type '{model_type}'. Registered: {available_models()}"
        )

    return builder(
        model_id=settings.get("id") or "gemini-2.5-flash-lite",
        max_tokens=settings.get("max_tokens"),
        extra=settings.get("additional_params") or {},
        api_version=settings.get("api_version"),
    )

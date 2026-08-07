"""
Tests for the typed config schema, the registries, and team entities.

The schema tests are pure and cost nothing. The team tests touch the database
and clean up after themselves.
"""

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent import AgentKind  # noqa: E402
from runtime.registry import (  # noqa: E402
    available_models,
    available_tools,
    build_model,
    build_tools,
    validate_tools,
)
from schemas.agent_config import (  # noqa: E402
    CURRENT_SCHEMA_VERSION,
    AgentConfig,
    parse_agent_config,
    parse_team_config,
)
from services.agent_service import AgentService, ConfigError, TeamService  # noqa: E402


# ------------------------------ schema ------------------------------


def test_defaults_are_filled_from_one_place():
    """Defaults live on the schema, not hand-patched in the HTTP layer."""
    config = parse_agent_config({}, fallback_name="Agent A")

    assert config.name == "Agent A"
    assert config.role == "Assistant"
    assert config.markdown is True
    assert config.show_tool_calls is True
    assert config.tools == []
    assert config.model.type == "google"
    assert config.schema_version == CURRENT_SCHEMA_VERSION


def test_legacy_model_config_key_is_read():
    """Existing rows store the LLM section as `model_config`."""
    config = parse_agent_config(
        {"model_config": {"type": "google", "id": "gemini-2.5-flash-lite", "max_tokens": 2048}},
        fallback_name="A",
    )
    assert config.model.id == "gemini-2.5-flash-lite"
    assert config.model.max_tokens == 2048


def test_storage_round_trip_keeps_both_keys():
    """Writes stay readable by code that still expects `model_config`."""
    stored = parse_agent_config({}, "A").to_storage()
    assert stored["model"] == stored["model_config"]
    assert parse_agent_config(stored, "A").model.type == "google"


def test_string_instructions_normalize_to_list():
    """Older rows store instructions as a bare string."""
    assert parse_agent_config({"instructions": "be terse"}, "A").instructions == ["be terse"]
    assert parse_agent_config({"instructions": ["a", "b"]}, "A").instructions == ["a", "b"]
    assert parse_agent_config({"instructions": None}, "A").instructions == []


def test_unknown_tool_rejected():
    with pytest.raises(ValidationError, match="Unknown tool"):
        AgentConfig(name="A", tools=["wikipedia"])


def test_unknown_model_provider_rejected():
    with pytest.raises(ValidationError, match="Unknown model type"):
        AgentConfig(name="A", model={"type": "anthropic", "id": "x"})


def test_typo_in_key_is_rejected_not_ignored():
    """extra='forbid' turns a silent no-op into an error."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        AgentConfig(name="A", instuctions="oops")


def test_team_config_rejects_invalid_mode():
    """
    'standalone' is what silently disabled delegation before Week 1; it can no
    longer even be saved.
    """
    with pytest.raises(ValidationError):
        parse_team_config({"mode": "standalone"}, "T")

    assert parse_team_config({"mode": "route"}, "T").mode == "route"


# ----------------------------- registries -----------------------------


def test_registries_expose_known_names():
    assert "duckduckgo" in available_tools()
    assert set(available_models()) >= {"google", "openai", "azure"}


def test_validate_tools_raises_on_unknown():
    validate_tools(["duckduckgo"])  # no raise
    validate_tools([])
    with pytest.raises(ValueError, match="Unknown tool"):
        validate_tools(["nope"])


def test_build_tools_returns_fresh_instances():
    """Factories, not shared singletons: two agents must not share a tool."""
    a = build_tools(["duckduckgo"])
    b = build_tools(["duckduckgo"])
    assert len(a) == 1 and len(b) == 1
    assert a[0] is not b[0]


def test_build_model_raises_instead_of_silently_defaulting():
    """The old factory returned Gemini for anything unrecognised."""
    with pytest.raises(ValueError, match="Unknown model type"):
        build_model({"type": "anthropic", "id": "claude"})


def test_build_model_passes_max_tokens_to_gemini():
    """max_tokens was previously read for Azure and dropped for Gemini."""
    model = build_model({"type": "google", "id": "gemini-2.5-flash-lite", "max_tokens": 1234})
    assert model.max_output_tokens == 1234


# ------------------------------- teams -------------------------------


@pytest.fixture
def temp_agents():
    """Create a host and two workers, removing them afterwards."""
    created = []
    host = AgentService.create_agent(
        name="__test_host", config={"mode": "coordinate"}, kind=AgentKind.HOST
    )
    created.append(host["agent_id"])
    workers = []
    for i in range(2):
        w = AgentService.create_agent(
            name=f"__test_worker_{i}", config={}, kind=AgentKind.SIMPLE
        )
        workers.append(w["agent_id"])
        created.append(w["agent_id"])

    yield host["agent_id"], workers

    for team in TeamService.list_teams():
        if team["name"].startswith("__test_"):
            TeamService.delete_team(team["team_id"])
    for agent_id in created:
        try:
            AgentService.delete_agent(agent_id)
        except ConfigError:
            pass


def test_team_persists_membership_and_order(temp_agents):
    host_id, workers = temp_agents
    team = TeamService.create_team(
        name="__test_team",
        host_agent_id=host_id,
        member_agent_ids=[workers[1], workers[0]],
    )

    assert [m["agent_id"] for m in team["members"]] == [workers[1], workers[0]]
    assert [m["position"] for m in team["members"]] == [0, 1]

    fetched = TeamService.get_team(team["team_id"])
    assert [m["agent_id"] for m in fetched["members"]] == [workers[1], workers[0]]


def test_team_coordinator_must_be_a_host_agent(temp_agents):
    _, workers = temp_agents
    with pytest.raises(ConfigError, match="must be kind='host'"):
        TeamService.create_team(
            name="__test_bad", host_agent_id=workers[0], member_agent_ids=[workers[1]]
        )


def test_team_rejects_missing_members(temp_agents):
    host_id, _ = temp_agents
    with pytest.raises(ConfigError, match="not found"):
        TeamService.create_team(
            name="__test_bad2", host_agent_id=host_id, member_agent_ids=[999999]
        )


def test_deleting_a_coordinator_in_use_is_refused(temp_agents):
    """The team would otherwise be left without a coordinator."""
    host_id, workers = temp_agents
    TeamService.create_team(
        name="__test_team_guard", host_agent_id=host_id, member_agent_ids=[workers[0]]
    )

    with pytest.raises(ConfigError, match="coordinates team"):
        AgentService.delete_agent(host_id)


def test_duplicate_members_are_collapsed(temp_agents):
    host_id, workers = temp_agents
    team = TeamService.create_team(
        name="__test_dupes",
        host_agent_id=host_id,
        member_agent_ids=[workers[0], workers[0], workers[1]],
    )
    assert len(team["members"]) == 2

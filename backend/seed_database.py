"""
Database Seeder Script
Loads agent configurations from JSON files and populates the database.
Run this script to initialize the database with predefined agents.

Usage: python seed_database.py
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.agent_service import AgentService, HostAgentService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> dict:
    """Load a JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return None


def seed_agents_from_directory(directory: str):
    """
    Seed agents from JSON files in a directory.
    
    Directory structure expected:
    ├── simple_agents/
    │   ├── research_agent.json
    │   └── ...
    └── mcp_agents/
        ├── hr_agent.json
        └── ...
    
    JSON format:
    {
        "name": "Agent Name",
        "description": "...",
        "is_mcp": false,
        "mcp_config": {...},  // Optional, for MCP agents
        "config": {
            "name": "...",
            "model_config": {...},
            "instructions": [...],
            "tools": [...],
            ...
        }
    }
    """
    configs_dir = Path(directory)
    
    if not configs_dir.exists():
        logger.error(f"Configs directory not found: {directory}")
        return
    
    seeded_count = 0
    
    # Seed simple agents
    simple_agents_dir = configs_dir / "simple_agents"
    if simple_agents_dir.exists():
        logger.info(f"Loading simple agents from {simple_agents_dir}...")
        for json_file in simple_agents_dir.glob("*.json"):
            try:
                config = load_json_file(str(json_file))
                if not config:
                    continue
                
                # config should have: name, description, is_mcp, config (with model_config, instructions, tools)
                agent_data = {
                    "name": config.get("name"),
                    "description": config.get("description"),
                    "agent_type": "simple",
                    "is_mcp": config.get("is_mcp", False),
                    "mcp_config": config.get("mcp_config"),
                    "config": config.get("config", config)  # Fall back to entire config if nested config not present
                }
                
                try:
                    result = AgentService.create_agent(**agent_data)
                    logger.info(f"[OK] Seeded agent: {result['name']}")
                    seeded_count += 1
                except ValueError as e:
                    logger.warning(f"⚠ {json_file.name}: {e}")
                except Exception as e:
                    logger.error(f"✗ Error seeding {json_file.name}: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing {json_file.name}: {e}")
    
    # Seed MCP agents
    mcp_agents_dir = configs_dir / "mcp_agents"
    if mcp_agents_dir.exists():
        logger.info(f"Loading MCP agents from {mcp_agents_dir}...")
        for json_file in mcp_agents_dir.glob("*.json"):
            try:
                config = load_json_file(str(json_file))
                if not config:
                    continue
                
                # config should have: name, description, is_mcp, mcp_config, config
                agent_data = {
                    "name": config.get("name"),
                    "description": config.get("description"),
                    "agent_type": "mcp",
                    "is_mcp": config.get("is_mcp", True),
                    "mcp_config": config.get("mcp_config", {}),
                    "config": config.get("config", config)
                }
                
                try:
                    result = AgentService.create_agent(**agent_data)
                    logger.info(f"[OK] Seeded MCP agent: {result['name']}")
                    seeded_count += 1
                except ValueError as e:
                    logger.warning(f"⚠ {json_file.name}: {e}")
                except Exception as e:
                    logger.error(f"✗ Error seeding {json_file.name}: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing {json_file.name}: {e}")
    
    logger.info(f"\n[OK] Seeding complete! {seeded_count} agents loaded.")
    return seeded_count


def seed_host_agent_from_file(file_path: str):
    """
    Seed a host agent from a JSON file.
    
    Expected JSON format:
    {
        "name": "Host Agent Name",
        "description": "...",
        "mode": "coordinate",
        "config": {
            "name": "...",
            "model_config": {...},
            "instructions": [...],
            "additional_params": {...}
        }
    }
    """
    config = load_json_file(file_path)
    if not config:
        return False
    
    try:
        host_agent_data = {
            "name": config.get("name"),
            "description": config.get("description"),
            "mode": config.get("mode", "coordinate"),
            "config": config.get("config", config)
        }
        
        result = HostAgentService.create_host_agent(**host_agent_data)
        logger.info(f"[OK] Seeded host agent: {result['name']}")
        return True
    except ValueError as e:
        logger.warning(f"⚠ Host agent seed warning: {e}")
        return False
    except Exception as e:
        logger.error(f"[ERROR] Error seeding host agent: {e}")
        return False


def main():
    """
    Seed agents from JSON config files.

    Seeding is additive by default: existing agents with the same name are
    skipped and nothing else is touched. `--reset` drops every table first,
    which destroys users, teams, and run history as well as agents, so it has
    to be asked for explicitly and is refused outside development.
    """
    import argparse

    from config import get_settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="DESTRUCTIVE: drop and recreate all tables before seeding",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt for --reset",
    )
    args = parser.parse_args()

    settings = get_settings()

    if args.reset:
        if settings.is_production:
            logger.error(
                f"Refusing to --reset with ENVIRONMENT={settings.environment}. "
                "This would delete all users, agents, teams, and run history."
            )
            return 1

        target = settings.database_url.split("@")[-1].split("?")[0]
        logger.warning("=" * 60)
        logger.warning("--reset will DROP every table in:")
        logger.warning(f"    {target}")
        logger.warning("That includes users, teams, and all run history.")
        logger.warning("=" * 60)

        if not args.yes:
            answer = input("Type the word RESET to continue: ").strip()
            if answer != "RESET":
                logger.info("Aborted; nothing was changed.")
                return 1

        from connection import init_db

        init_db(recreate_tables=True)
    else:
        # Schema is Alembic's job. Fail early with a useful message rather than
        # a confusing "relation does not exist" from the first insert.
        from sqlalchemy import inspect

        from connection import engine

        if "agents" not in inspect(engine).get_table_names():
            logger.error(
                "No 'agents' table. Create the schema first: "
                "python -m alembic upgrade head"
            )
            return 1

    logger.info("=" * 60)
    logger.info("Seeding agents from JSON configs...")
    logger.info("=" * 60)

    configs_dir = os.path.join(os.path.dirname(__file__), "agents", "configs")
    seed_agents_from_directory(configs_dir)

    host_config_file = os.path.join(configs_dir, "host_config.json")
    if os.path.exists(host_config_file):
        logger.info(f"Loading host agent from {host_config_file}...")
        seed_host_agent_from_file(host_config_file)

    logger.info("Seeding completed.")
    logger.info(
        "Seeded agents have no owner, so only an administrator can edit them. "
        "The first registered account is an administrator."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

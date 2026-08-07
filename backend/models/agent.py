"""
SQLAlchemy models for database tables.
Database models for marketplace agents and orchestration.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB

# Base lives in models.base so every model shares one metadata registry.
# Re-exported here because existing imports do `from models.agent import Base`.
from models.base import Base, utcnow


class Agent(Base):
    """
    SQLAlchemy model for the agents table.
    Represents an agent with its configuration in the marketplace.
    """
    __tablename__ = "agents"
    
    agent_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=False, default="simple")  # simple, mcp, host
    is_mcp = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # MCP configuration (for MCP agents)
    mcp_config = Column(JSONB, nullable=True, default={})
    
    # Full agent configuration - includes name, description, model_config, instructions, tools, etc.
    # This is the complete config that gets passed to the agent execution engine
    config = Column(JSONB, nullable=False, default={})
    
    # Metadata
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "is_mcp": self.is_mcp,
            "is_active": self.is_active,
            "mcp_config": self.mcp_config,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<Agent(id={self.agent_id}, name='{self.name}', type='{self.agent_type}', is_mcp={self.is_mcp})>"


class HostAgent(Base):
    """
    SQLAlchemy model for the host_agent table.
    Represents a host/orchestrator agent that coordinates multiple agents.
    """
    __tablename__ = "host_agent"
    
    agent_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_mcp = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Orchestration mode: coordinate, sequential, parallel
    mode = Column(String(50), default="coordinate")
    
    # Full host agent configuration
    # Expected structure:
    # {
    #   "name": "...",
    #   "mode": "coordinate",
    #   "model_config": {...},
    #   "instructions": [...],
    #   "additional_params": {...}
    # }
    config = Column(JSONB, nullable=False, default={})
    
    # Metadata
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "is_mcp": self.is_mcp,
            "is_active": self.is_active,
            "mode": self.mode,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<HostAgent(id={self.agent_id}, name='{self.name}', mode='{self.mode}')>"


"""SQLAlchemy ORM models for system database."""
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import Uuid

Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    oauth_sub = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    user_policies = relationship("UserPolicy", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    """Role model."""

    __tablename__ = "roles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(50), unique=True, nullable=False)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_policies = relationship("RolePolicy", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    """User-Role association."""

    __tablename__ = "user_roles"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id = Column(Uuid(as_uuid=True), ForeignKey("roles.id"), primary_key=True)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class RolePolicy(Base):
    """Role-level policy model."""

    __tablename__ = "role_policies"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    role_id = Column(Uuid(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    table_pattern = Column(String, nullable=False)

    # Relationships
    role = relationship("Role", back_populates="role_policies")


class UserPolicy(Base):
    """User-level policy model."""

    __tablename__ = "user_policies"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    table_pattern = Column(String, nullable=False)
    policy_type = Column(String(10), nullable=False)  # 'grant' | 'restrict'

    # Relationships
    user = relationship("User", back_populates="user_policies")


class ChatMessage(Base):
    """Chat message model."""

    __tablename__ = "chat_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(Uuid(as_uuid=True), nullable=False)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    chunk_ids = Column(JSON, nullable=True)
    guardrail_result = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


class RequestLog(Base):
    """Request log model."""

    __tablename__ = "request_log"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    violation_chunk_ids = Column(JSON, nullable=True)
    severity = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

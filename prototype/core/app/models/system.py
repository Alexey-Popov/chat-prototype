"""SQLAlchemy ORM models for system_db.

Uses dialect-agnostic types (sqlalchemy.types.Uuid, JSON) so the same models
work against both PostgreSQL (production) and SQLite (unit tests).
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, JSON, String, Text, func,
)
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    oauth_sub = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    user_policies = relationship("UserPolicy", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(50), unique=True, nullable=False)

    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_policies = relationship("RolePolicy", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id = Column(Uuid(as_uuid=True), ForeignKey("roles.id"), primary_key=True)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_roles")


class RolePolicy(Base):
    __tablename__ = "role_policies"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    role_id = Column(Uuid(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    table_pattern = Column(String, nullable=False)

    role = relationship("Role", back_populates="role_policies")


class UserPolicy(Base):
    __tablename__ = "user_policies"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    table_pattern = Column(String, nullable=False)
    policy_type = Column(String(10), nullable=False)  # 'grant' or 'restrict'

    user = relationship("User", back_populates="user_policies")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(10), nullable=False)   # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    chunk_ids = Column(JSON, nullable=False, default=list)
    guardrail_result = Column(String(10), nullable=True)  # 'pass' or 'fail'
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User", back_populates="chat_messages")


class RequestLog(Base):
    __tablename__ = "request_log"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    violation_chunk_ids = Column(JSON, nullable=True)
    severity = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

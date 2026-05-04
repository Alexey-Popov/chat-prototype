# Internal Company Assistant — Project Brief

## Overview

Build a prototype of an AI-powered internal assistant for fintech companies. The system collects and indexes internal knowledge, exposes it through a role-aware chat interface, and enforces strict identity-based access control so each user only sees what they're permitted to see.

---

## Core Components

### 1. Internal Knowledge Ingestion
Connects to internal company data sources — **not** public or external networks. Collects and indexes:
- Internal messages and communications
- Company history and institutional knowledge
- Financial information and reports
- Transaction data
- Database records and structured data

> Domain focus: **Fintech**

### 2. Chat Interface (External-Facing)
A conversational UI that serves as the primary interface for end users:
- Chat-based interaction (natural language)
- Supports **multiple user roles** — each role surfaces a different scope of information
- Responses are filtered at query time based on the caller's identity and role

### 3. Identity & Access Control Layer
The security core of the system:
- Authenticates and identifies each user
- **Isolates information access** per identity — a support agent cannot see what a finance officer sees, and vice versa
- Access rules are enforced at the data retrieval level, not just the UI level

### 4. Admin Interface
A management UI for administrators to:
- Create, edit, and deactivate user identities
- Assign and adjust roles and access permissions
- Audit who has access to what

---

## Target User Roles

| Role | Primary Use Case |
|------|-----------------|
| **Support** | Customer and internal issue resolution, knowledge lookup |
| **Financial Department** | Access to financial data, transactions, reports |
| **Business Development** | Company history, deal context, strategic information |

---

## Key Requirements

- **Data isolation**: Information visible to one role must be invisible to another at the retrieval level
- **Internal-only ingestion**: No external data sources; all knowledge is company-internal
- **Role-based responses**: The same question asked by two different roles may return different answers
- **Admin control**: Centralized identity management with the ability to add/remove/modify access without engineering involvement
- **Prototype scope**: Prove the core loop — ingest → retrieve → respond with access control — before scaling

---

## Decisions

| Question | Decision |
|----------|----------|
| **Data sources in scope** | Database (DB) only for prototype |
| **Authentication** | OAuth for prototype; architecture must support additional providers in the future |
| **Access policy granularity** | Both role-level and user-level policies |
| **Target stack** | Python — fast to build, easily expandable. Suggest lightweight RAG pipeline (e.g. LangChain or LlamaIndex) with a vector DB (e.g. pgvector or Chroma) and a pluggable LLM provider |
| **Interface** | Web chat as a standalone app + REST API for integrations |

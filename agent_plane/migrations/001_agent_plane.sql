create schema if not exists agent_plane;

create table if not exists agent_plane.principal_map (
    id text primary key,
    source_facade text not null,
    principal jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists agent_plane.facade_sessions (
    id text primary key,
    source_facade text not null,
    principal_id text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists agent_plane.messages (
    id text primary key,
    session_id text,
    source_facade text not null,
    role text not null,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists agent_plane.policy_decisions (
    id text primary key,
    request_id text not null,
    source_facade text not null,
    principal jsonb not null,
    tool text not null,
    allowed boolean not null,
    reason text not null,
    guarded boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists agent_plane.tool_calls (
    id text primary key,
    request_id text not null,
    source_facade text not null,
    principal jsonb not null,
    tool text not null,
    policy_decision_id text not null,
    policy_allowed boolean not null,
    policy_reason text not null,
    status text not null,
    result_meta jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists agent_plane.approvals (
    id text primary key,
    request_id text,
    source_facade text not null,
    principal jsonb not null,
    scope text not null,
    status text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    expires_at timestamptz
);

create table if not exists agent_plane.memory_refs (
    id text primary key,
    source_facade text not null,
    intbrain_ref text not null,
    source_ref text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists tool_calls_source_facade_created_idx
    on agent_plane.tool_calls (source_facade, created_at desc);

create index if not exists tool_calls_request_id_idx
    on agent_plane.tool_calls (request_id);

create index if not exists memory_refs_source_facade_created_idx
    on agent_plane.memory_refs (source_facade, created_at desc);

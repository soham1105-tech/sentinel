-- SENTINEL persistence schema (Supabase/Postgres).
-- store.py uses the same table and column names for its SQLite fallback.

create extension if not exists "pgcrypto";

create table if not exists public.runs (
    id uuid primary key,
    created_at timestamptz not null default now(),
    target_version text not null,
    score_before int not null,
    score_after int not null
);

create table if not exists public.test_results (
    id uuid primary key,
    run_id uuid not null references public.runs(id) on delete cascade,
    scenario_id text not null,
    version text not null,
    passed boolean not null,
    reply text not null,
    transcript text not null
);

create table if not exists public.patches (
    id uuid primary key,
    run_id uuid not null references public.runs(id) on delete cascade,
    scenario_id text not null,
    patch_text text not null
);

create index if not exists test_results_run_id_idx
    on public.test_results (run_id);

create index if not exists patches_run_id_idx
    on public.patches (run_id);

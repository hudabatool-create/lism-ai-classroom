-- Future real schema for LISM AI Classroom.
-- Mirrors app/services/data_store.py exactly, so swapping the in-memory
-- DataStore for a Supabase-backed one is a contained rewrite of that one
-- module, not a redesign. Not applied anywhere yet — this scaffold runs
-- entirely in-memory.

create extension if not exists "pgcrypto";

-- Teachers are Supabase Auth users; this table holds profile data keyed to auth.users.id.
create table if not exists teachers (
  id uuid primary key references auth.users (id) on delete cascade,
  name text not null,
  email text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists activities (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references teachers (id) on delete cascade,
  title text not null,
  subject text default '',
  grade text default '',
  activity_type text default '',
  html text not null,
  source text not null default 'upload', -- 'upload' | 'ai'
  created_at timestamptz not null default now()
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references teachers (id) on delete cascade,
  activity_id uuid not null references activities (id) on delete cascade,
  code text not null unique,
  status text not null default 'active', -- 'active' | 'ended'
  created_at timestamptz not null default now(),
  ended_at timestamptz
);

create table if not exists students (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions (id) on delete cascade,
  name text not null,
  grade text default '',
  section text default '',
  joined_at timestamptz not null default now()
);

create table if not exists responses (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions (id) on delete cascade,
  student_id uuid not null references students (id) on delete cascade,
  correct boolean,
  answer text default '',
  submitted_at timestamptz not null default now()
);

-- Row Level Security: a teacher may only see their own activities/sessions.
-- Students join/respond through the public API (service role), not directly.
alter table teachers enable row level security;
alter table activities enable row level security;
alter table sessions enable row level security;
alter table students enable row level security;
alter table responses enable row level security;

create policy "teachers manage own profile" on teachers
  for all using (auth.uid() = id);

create policy "teachers manage own activities" on activities
  for all using (auth.uid() = teacher_id);

create policy "teachers manage own sessions" on sessions
  for all using (auth.uid() = teacher_id);

create policy "teachers read own session students" on students
  for select using (
    exists (select 1 from sessions s where s.id = students.session_id and s.teacher_id = auth.uid())
  );

create policy "teachers read own session responses" on responses
  for select using (
    exists (select 1 from sessions s where s.id = responses.session_id and s.teacher_id = auth.uid())
  );

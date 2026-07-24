// Placeholder for the future real Supabase client. Not wired up yet — this
// scaffold authenticates against the FastAPI backend's own JWT auth (see
// lib/api.ts). To go live with real Supabase Auth/DB/Storage, install
// @supabase/supabase-js and initialize createClient() here with these vars.

export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

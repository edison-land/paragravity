// Raw shape returned by `pgrav list --json` (see profile_summary() in
// bin/paragravity). Keep in sync with the CLI — the web console and the
// vite dev middleware both consume this verbatim.
export interface ApiProfile {
  name: string
  running: boolean
  pid: number | null
  account: string | null
  has_token: boolean
  token_exp: string | null
  token_state: 'expired' | 'expiring' | null
  size: string | null
  directory: string | null
  created_at: string | null
  description: string
  inherited_from: string | null
}

// Normalized shape the UI renders (also used by the demo profiles).
export interface Profile {
  name: string
  status: 'running' | 'stopped'
  pid: number
  email: string | null
  has_token: boolean
  token_exp: string | null
  size: string
  description: string
  created_at: string | null
  path: string
}

export function mapApiProfile(p: ApiProfile): Profile {
  return {
    name: p.name,
    status: p.running ? 'running' : 'stopped',
    pid: p.pid ?? 0,
    email: p.account,
    has_token: p.has_token,
    token_exp: p.token_exp,
    size: p.size ?? '—',
    description: p.description ?? '',
    created_at: p.created_at ?? null,
    path: p.directory ?? '',
  }
}

export interface SystemInfo {
  version: string
  theme: string
  themeName: string
  platform: string
}

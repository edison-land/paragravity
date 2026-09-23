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

export interface SystemInfo {
  version: string
  theme: string
  themeName: string
  platform: string
}

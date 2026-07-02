import axios, { type AxiosInstance } from 'axios'

export const TOKEN_KEY = 'lotto_token'

/* ---------------------------------------------------------------- Types --- */

export interface User {
  id: number | string
  email: string
  display_name: string
  role: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface AnalyticsSummary {
  total_spent_cents: number
  total_won_cents: number
  net_cents: number
  tickets_purchased: number
  lines_played: number
  win_rate: number
  biggest_win_cents: number
  roi_pct: number
  pending_cents: number
}

export interface GameBreakdown {
  game_key: string
  display_name: string
  spent_cents: number
  won_cents: number
  net_cents: number
  tickets: number
}

export type OverTimeBucket = 'month' | 'week'

export interface OverTimePoint {
  /** 'YYYY-MM' for month buckets, 'YYYY-Www' for week buckets. */
  period: string
  spent_cents: number
  won_cents: number
  net_cents: number
}

export interface PickSideBreakdown {
  lines: number
  wins: number
  win_rate: number
}

export interface PickBreakdown {
  quick_pick: PickSideBreakdown
  self_pick: PickSideBreakdown
}

export interface InviteResponse {
  token: string
  email: string
  expires_at: string
}

export interface IngestSummary {
  games_ingested?: number
  draws_created?: number
  results_created?: number
  [key: string]: unknown
}

export interface DrawCreate {
  game_key: string
  draw_date: string // 'YYYY-MM-DD'
  winning_main: number[]
  winning_special?: number | null
  multiplier?: number | null
  payouts?: Record<string, number> | null
  draw_period?: string | null
}

export interface DrawCreateResponse {
  draw: Draw
  results_created: number
}

export interface MatchResponse {
  results_created: number
}

export interface TicketLine {
  id: number | string
  line_index: number
  main_numbers: number[]
  special_number: number | null
  play_type: string | null
  wager_cents: number
  is_quick_pick: boolean
}

export interface TicketResult {
  tier_key: string
  match_main_count: number
  match_special: boolean
  amount_won_cents: number
  status: string
  draw_id: number | string
}

/** Add-ons is a flag map, e.g. { power_play: true } / { extra: true } / { fireball: true }. */
export type AddOns = Record<string, boolean>

export interface Ticket {
  id: number | string
  game_key: string
  purchase_date: string
  num_draws: number
  add_ons: AddOns | null
  entry_method: string | null
  total_cost_cents: number
  created_at: string
  lines: TicketLine[]
  results: TicketResult[]
  total_won_cents: number
}

/** Shape sent to POST /api/tickets (mirrors backend PlayLineIn). */
export interface PlayLineIn {
  main_numbers: number[]
  special_number?: number | null
  play_type?: string | null
  wager_cents?: number
  is_quick_pick?: boolean
}

export interface TicketCreate {
  game_key: string
  purchase_date: string // 'YYYY-MM-DD'
  num_draws: number
  add_ons: AddOns
  entry_method: 'manual' | 'ocr'
  lines: PlayLineIn[]
}

/** Draft returned by POST /api/ocr/scan — shaped like TicketCreate, plus meta. */
export interface OcrDraft {
  game_key: string
  purchase_date: string
  num_draws: number
  add_ons: AddOns
  lines: PlayLineIn[]
  confidence: Record<string, number>
  flags: string[]
  image_path?: string | null
}

export interface Draw {
  id: number | string
  game_key: string
  draw_date: string
  draw_period: string | null
  winning_main: number[]
  winning_special: number | null
  multiplier: number | null
}

/* ------------------------------------------------------------- Instance --- */

export const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      setToken(null)
      // Avoid redirect loops when already on the login screen.
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

/* ------------------------------------------------------------ Endpoints --- */

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { email, password })
  return data
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function fetchSummary(): Promise<AnalyticsSummary> {
  const { data } = await api.get<AnalyticsSummary>('/analytics/summary')
  return data
}

export async function fetchByGame(): Promise<GameBreakdown[]> {
  const { data } = await api.get<GameBreakdown[]>('/analytics/by-game')
  return data
}

export async function fetchOverTime(bucket: OverTimeBucket = 'month'): Promise<OverTimePoint[]> {
  const { data } = await api.get<OverTimePoint[]>('/analytics/over-time', {
    params: { bucket },
  })
  return data
}

export async function fetchPickBreakdown(): Promise<PickBreakdown> {
  const { data } = await api.get<PickBreakdown>('/analytics/pick-breakdown')
  return data
}

export async function createInvite(email: string): Promise<InviteResponse> {
  const { data } = await api.post<InviteResponse>('/invites/', { email })
  return data
}

export async function ingestResults(): Promise<IngestSummary> {
  const { data } = await api.post<IngestSummary>('/results/ingest', {})
  return data
}

export async function createDraw(body: DrawCreate): Promise<DrawCreateResponse> {
  const { data } = await api.post<DrawCreateResponse>('/results/draws', body)
  return data
}

export async function rematchResults(): Promise<MatchResponse> {
  const { data } = await api.post<MatchResponse>('/results/match', {})
  return data
}

export async function fetchTickets(): Promise<Ticket[]> {
  const { data } = await api.get<Ticket[]>('/tickets/')
  return data
}

export async function fetchTicket(id: string): Promise<Ticket> {
  const { data } = await api.get<Ticket>(`/tickets/${id}`)
  return data
}

export async function createTicket(body: TicketCreate): Promise<Ticket> {
  const { data } = await api.post<Ticket>('/tickets/', body)
  return data
}

export async function deleteTicket(id: string): Promise<void> {
  await api.delete(`/tickets/${id}`)
}

export async function scanTicket(file: File): Promise<OcrDraft> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<OcrDraft>('/ocr/scan', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function fetchDraws(limit = 10): Promise<Draw[]> {
  const { data } = await api.get<Draw[]>('/results/draws', { params: { limit } })
  return data
}

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

export interface Ticket {
  id: number | string
  game_key: string
  purchase_date: string
  num_draws: number
  add_ons: string[] | null
  entry_method: string | null
  total_cost_cents: number
  created_at: string
  lines: TicketLine[]
  results: TicketResult[]
  total_won_cents: number
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

export async function fetchTickets(): Promise<Ticket[]> {
  const { data } = await api.get<Ticket[]>('/tickets/')
  return data
}

export async function fetchTicket(id: string): Promise<Ticket> {
  const { data } = await api.get<Ticket>(`/tickets/${id}`)
  return data
}

export async function fetchDraws(limit = 10): Promise<Draw[]> {
  const { data } = await api.get<Draw[]>('/results/draws', { params: { limit } })
  return data
}

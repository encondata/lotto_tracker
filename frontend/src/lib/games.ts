export interface GameMeta {
  key: string
  name: string
  color: string
  mainCount: number
  mainMin: number
  mainMax: number
  hasSpecial: boolean
  specialMin?: number
  specialMax?: number
  isDaily4?: boolean
  playTypes?: string[]
}

export const GAMES: Record<string, GameMeta> = {
  powerball: {
    key: 'powerball',
    name: 'Powerball',
    color: 'var(--pb)',
    mainCount: 5,
    mainMin: 1,
    mainMax: 69,
    hasSpecial: true,
    specialMin: 1,
    specialMax: 26,
  },
  mega_millions: {
    key: 'mega_millions',
    name: 'Mega Millions',
    color: 'var(--mm)',
    mainCount: 5,
    mainMin: 1,
    mainMax: 70,
    hasSpecial: true,
    specialMin: 1,
    specialMax: 24,
  },
  lotto_texas: {
    key: 'lotto_texas',
    name: 'Lotto Texas',
    color: 'var(--lt)',
    mainCount: 6,
    mainMin: 1,
    mainMax: 54,
    hasSpecial: false,
  },
  texas_two_step: {
    key: 'texas_two_step',
    name: 'Texas Two Step',
    color: 'var(--ts)',
    mainCount: 4,
    mainMin: 1,
    mainMax: 35,
    hasSpecial: true,
    specialMin: 1,
    specialMax: 35,
  },
  daily4: {
    key: 'daily4',
    name: 'Daily 4',
    color: 'var(--d4)',
    mainCount: 4,
    mainMin: 0,
    mainMax: 9,
    hasSpecial: false,
    isDaily4: true,
    // Must match backend validation (app/services/tickets.py DAILY4_PLAY_TYPES).
    playTypes: ['straight', 'box', 'combo', 'pair-front', 'pair-mid', 'pair-back'],
  },
}

const FALLBACK_COLORS = [
  'var(--mint)',
  'var(--brass)',
  'var(--ts)',
  'var(--d4)',
]

export function gameMeta(key: string): GameMeta {
  const found = GAMES[key]
  if (found) return found
  // Deterministic fallback for unknown game keys so UI never breaks.
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) | 0
  const color = FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length]
  const name = key
    .split('_')
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' ')
  return {
    key,
    name,
    color,
    mainCount: 5,
    mainMin: 1,
    mainMax: 99,
    hasSpecial: false,
  }
}

export function gameName(key: string): string {
  return gameMeta(key).name
}

export function gameColor(key: string): string {
  return gameMeta(key).color
}

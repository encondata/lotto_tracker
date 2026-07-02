import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  fetchMe,
  getToken,
  login as apiLogin,
  setToken as persistToken,
  type User,
} from './api'

interface AuthContextValue {
  token: string | null
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(!!getToken())

  // Hydrate `me` whenever we hold a token.
  useEffect(() => {
    let active = true
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    setLoading(true)
    fetchMe()
      .then((u) => {
        if (active) setUser(u)
      })
      .catch(() => {
        if (active) {
          persistToken(null)
          setTokenState(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [token])

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password)
    persistToken(res.access_token)
    setTokenState(res.access_token)
    const u = await fetchMe()
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    persistToken(null)
    setTokenState(null)
    setUser(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: !!token,
      login,
      logout,
    }),
    [token, user, loading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

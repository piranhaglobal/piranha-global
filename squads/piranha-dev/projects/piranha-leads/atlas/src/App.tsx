import { useEffect, useState } from 'react'
import { Database, LogIn, LogOut, MessageSquare, Radio, Settings as SettingsIcon } from 'lucide-react'
import StudioDatabase from './components/views/StudioDatabase'
import ScraperControl from './components/views/ScraperControl'
import Settings from './components/views/Settings'
import ResearchChat from './components/views/ResearchChat'
import logoUrl from './assets/logo.svg'

type Tab = 'database' | 'scraper' | 'chat' | 'settings'
type AuthConfig = { required: boolean; google_configured: boolean; domain: string }

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'database', label: 'Studio Database', icon: <Database size={16} /> },
  { id: 'scraper', label: 'Scraper Control', icon: <Radio size={16} /> },
  { id: 'chat', label: 'Chat', icon: <MessageSquare size={16} /> },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon size={16} /> },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('database')
  const [authLoading, setAuthLoading] = useState(true)
  const [user, setUser] = useState<{ email: string; name: string } | null>(null)
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const error = params.get('auth_error')
    if (error) {
      setAuthError(error)
      window.history.replaceState({}, '', window.location.pathname)
    }

    Promise.all([
      fetch('/api/auth/config')
        .then(res => res.ok ? res.json() : Promise.reject())
        .catch(() => null),
      fetch('/api/auth/me')
        .then(res => res.ok ? res.json() : Promise.reject())
        .catch(() => null),
    ])
      .then(([config, session]) => {
        setAuthConfig(config)
        setUser(session?.user || null)
      })
      .finally(() => setAuthLoading(false))
  }, [])

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => null)
    window.location.href = '/'
  }

  if (authLoading) {
    return <div style={{ height: '100vh', background: 'var(--color-bg-primary)' }} />
  }

  if (!user) {
    const googleReady = authConfig?.google_configured !== false
    const domain = authConfig?.domain || 'piranha.com.pt'
    return (
      <div style={{
        height: '100vh',
        background: 'radial-gradient(circle at 20% 10%, rgba(225,29,46,0.18), transparent 32%), linear-gradient(135deg, #101113 0%, #080809 100%)',
        display: 'grid',
        placeItems: 'center',
        padding: 24,
      }}>
        <div style={{
          width: 'min(430px, 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          background: 'linear-gradient(180deg, rgba(28,29,33,0.94), rgba(17,18,20,0.94))',
          borderRadius: 14,
          padding: 26,
          boxShadow: '0 28px 90px rgba(0,0,0,0.38)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
            <img src={logoUrl} alt="Piranha" style={{ height: 34, width: 'auto', filter: 'brightness(0) saturate(100%) invert(18%) sepia(93%) saturate(2500%) hue-rotate(340deg) brightness(85%)' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text-primary)', fontSize: 18, fontWeight: 750 }}>Atlas</div>
              <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginTop: 2 }}>Portal privado de scraping</div>
            </div>
          </div>
          <div style={{ color: 'var(--color-text-primary)', fontSize: 20, fontWeight: 750, marginBottom: 8 }}>
            Acesso restrito
          </div>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, lineHeight: 1.55, margin: '0 0 18px' }}>
            Entre com uma conta Google do domínio @{domain}. Nenhum dado do portal é carregado sem sessão ativa.
          </p>
          {authError && (
            <div style={{
              color: '#FCA5A5',
              background: 'rgba(239,68,68,0.10)',
              border: '1px solid rgba(239,68,68,0.22)',
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: 12,
              lineHeight: 1.45,
              marginBottom: 12,
            }}>
              {authError}
            </div>
          )}
          {!googleReady && (
            <div style={{
              color: '#FCD34D',
              background: 'rgba(245,158,11,0.10)',
              border: '1px solid rgba(245,158,11,0.22)',
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: 12,
              lineHeight: 1.45,
              marginBottom: 12,
            }}>
              Google OAuth ainda não está configurado no servidor.
            </div>
          )}
          <a
            href="/api/auth/google/login"
            aria-disabled={!googleReady}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              height: 44,
              borderRadius: 8,
              border: '1px solid rgba(225,29,46,0.35)',
              background: 'var(--color-accent)',
              color: 'white',
              fontSize: 13,
              fontWeight: 600,
              textDecoration: 'none',
              pointerEvents: googleReady ? 'auto' : 'none',
              opacity: googleReady ? 1 : 0.55,
            }}
          >
            <LogIn size={15} />
            Entrar com Google
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col" style={{ height: '100vh', overflow: 'hidden', background: 'var(--color-bg-primary)' }}>
      {/* Topbar */}
      <header style={{ background: 'var(--color-bg-secondary)', borderBottom: '1px solid var(--color-border)' }}
        className="flex items-center gap-6 px-6 h-14 shrink-0">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src={logoUrl} alt="Piranha" style={{ height: 28, width: 'auto', filter: 'brightness(0) saturate(100%) invert(18%) sepia(93%) saturate(2500%) hue-rotate(340deg) brightness(85%)' }} />
          <span style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text-primary)', fontSize: 16, fontWeight: 700, letterSpacing: '-0.3px' }}>
            Atlas
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{
                background: activeTab === tab.id ? 'var(--color-bg-surface)' : 'transparent',
                color: activeTab === tab.id ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                border: activeTab === tab.id ? '1px solid var(--color-border)' : '1px solid transparent',
              }}>
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          title={user.email}
          style={{
            marginLeft: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            border: '1px solid var(--color-border)',
            background: 'var(--color-bg-surface)',
            color: 'var(--color-text-secondary)',
            borderRadius: 6,
            padding: '7px 10px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          <LogOut size={14} />
          {user.email}
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden" style={{ minHeight: 0 }}>
        {activeTab === 'database' && <StudioDatabase />}
        {activeTab === 'scraper' && <ScraperControl />}
        {activeTab === 'chat' && <ResearchChat />}
        {activeTab === 'settings' && <Settings />}
      </main>
    </div>
  )
}

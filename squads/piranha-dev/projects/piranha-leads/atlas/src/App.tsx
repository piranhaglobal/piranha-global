import { useState } from 'react'
import { Database, Radio, Settings as SettingsIcon } from 'lucide-react'
import StudioDatabase from './components/views/StudioDatabase'
import ScraperControl from './components/views/ScraperControl'
import Settings from './components/views/Settings'
import logoUrl from './assets/logo.svg'

type Tab = 'database' | 'scraper' | 'settings'

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'database', label: 'Studio Database', icon: <Database size={16} /> },
  { id: 'scraper', label: 'Scraper Control', icon: <Radio size={16} /> },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon size={16} /> },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('database')

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--color-bg-primary)' }}>
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
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === 'database' && <StudioDatabase />}
        {activeTab === 'scraper' && <ScraperControl />}
        {activeTab === 'settings' && <Settings />}
      </main>
    </div>
  )
}

import { Loader, CheckCircle, Zap } from 'lucide-react'
import type { KlaviyoSyncResult } from '../../types'

interface Props {
  syncing: boolean
  result: KlaviyoSyncResult | null
  onSync: () => void
}

export default function KlaviyoSyncBar({ syncing, result, onSync }: Props) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '10px 16px',
      background: 'var(--color-bg-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 8,
    }}>
      <Zap size={14} style={{ color: '#A78BFA', flexShrink: 0 }} />

      {syncing ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, color: 'var(--color-text-secondary)', fontSize: 13 }}>
          <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />
          <span>A sincronizar com Klaviyo...</span>
        </div>
      ) : result ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-success)', fontSize: 13 }}>
          <CheckCircle size={13} />
          <span>
            <strong>{result.synced}</strong> sincronizados
            {result.skipped > 0 && <>, <span style={{ color: 'var(--color-text-secondary)' }}>{result.skipped} sem contacto</span></>}
          </span>
        </div>
      ) : (
        <div style={{ flex: 1, color: 'var(--color-text-secondary)', fontSize: 13 }}>
          Sincronizar leads pendentes com Klaviyo
        </div>
      )}

      <button
        onClick={onSync}
        disabled={syncing}
        style={{
          padding: '6px 14px',
          background: syncing ? 'var(--color-border)' : 'rgba(167,139,250,0.15)',
          border: '1px solid rgba(167,139,250,0.3)',
          color: syncing ? 'var(--color-text-secondary)' : '#A78BFA',
          borderRadius: 6,
          fontSize: 12,
          fontWeight: 500,
          cursor: syncing ? 'not-allowed' : 'pointer',
          whiteSpace: 'nowrap',
          transition: 'all 0.15s',
        }}
        onMouseEnter={e => {
          if (!syncing) (e.currentTarget as HTMLElement).style.background = 'rgba(167,139,250,0.25)'
        }}
        onMouseLeave={e => {
          if (!syncing) (e.currentTarget as HTMLElement).style.background = 'rgba(167,139,250,0.15)'
        }}
      >
        {syncing ? 'A sincronizar...' : 'Sincronizar Pendentes'}
      </button>
    </div>
  )
}

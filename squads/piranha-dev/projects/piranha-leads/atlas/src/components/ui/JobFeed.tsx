import { format, parseISO } from 'date-fns'
import { pt } from 'date-fns/locale'
import { CheckCircle, XCircle, Loader, Clock, MapPin, Users, Mail, Zap } from 'lucide-react'
import type { ScraperJob } from '../../types'
import { formatDuration } from '../../lib/utils'

interface Props {
  jobs: ScraperJob[]
  loading: boolean
}

function StatusChip({ status }: { status: ScraperJob['status'] }) {
  if (status === 'running') {
    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-accent)', fontSize: 12 }}>
        <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />
        A correr
      </span>
    )
  }
  if (status === 'completed') {
    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-success)', fontSize: 12 }}>
        <CheckCircle size={12} />
        Concluído
      </span>
    )
  }
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#F87171', fontSize: 12 }}>
      <XCircle size={12} />
      Erro
    </span>
  )
}

export default function JobFeed({ jobs, loading }: Props) {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 20, color: 'var(--color-text-secondary)', fontSize: 13 }}>
        <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
        A carregar jobs...
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: 13 }}>
        Nenhum job executado ainda.
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      {jobs.map(job => {
        let parsedCities: string[] = []
        try {
          parsedCities = JSON.parse(job.cities)
        } catch {
          parsedCities = []
        }
        return (
          <div
            key={job.id}
            style={{
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              padding: '12px 16px',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
            }}
          >
            {/* Left: status icon */}
            <div style={{ marginTop: 2, flexShrink: 0 }}>
              {job.status === 'running' ? (
                <div style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: 'var(--color-accent)',
                  animation: 'pulse 1s ease-in-out infinite',
                  marginTop: 4,
                }} />
              ) : job.status === 'completed' ? (
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-success)', marginTop: 4 }} />
              ) : (
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#F87171', marginTop: 4 }} />
              )}
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-text-secondary)' }}>
                    #{job.id}
                  </span>
                  <span style={{
                    background: 'rgba(225,29,46,0.12)',
                    color: 'var(--color-accent)',
                    border: '1px solid rgba(225,29,46,0.25)',
                    padding: '1px 6px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 500,
                  }}>
                    {job.query}
                  </span>
                </div>
                <StatusChip status={job.status} />
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  <Clock size={11} />
                  <span>{format(parseISO(job.started_at), "dd MMM HH:mm", { locale: pt })}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  <MapPin size={11} />
                  <span>{parsedCities.length} cidades</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  <Users size={11} />
                  <span style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>{job.leads_found}</span>
                  <span>leads</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  <Mail size={11} />
                  <span style={{ color: job.leads_with_email > 0 ? 'var(--color-success)' : 'var(--color-text-secondary)', fontWeight: 500 }}>
                    {job.leads_with_email}
                  </span>
                  <span>emails</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  <Zap size={11} />
                  <span style={{ color: job.klaviyo_synced > 0 ? '#A78BFA' : 'var(--color-text-secondary)', fontWeight: 500 }}>
                    {job.klaviyo_synced}
                  </span>
                  <span>Klaviyo</span>
                </div>
                {job.duration_seconds && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-secondary)', fontSize: 12 }}>
                    <Clock size={11} />
                    <span>{formatDuration(job.duration_seconds)}</span>
                  </div>
                )}
              </div>

              {job.error && (
                <div style={{
                  marginTop: 8,
                  padding: '6px 8px',
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  borderRadius: 4,
                  color: '#F87171',
                  fontSize: 12,
                  fontFamily: 'var(--font-mono)',
                }}>
                  {job.error}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

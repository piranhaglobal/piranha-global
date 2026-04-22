import { useEffect } from 'react'
import { X, MessageCircle, Globe, Mail, Phone, MapPin, Star, Users, CheckCircle, Circle, Instagram, Facebook } from 'lucide-react'
import type { Lead } from '../../types'
import { formatReviews } from '../../lib/utils'

interface Props {
  lead: Lead | null
  onClose: () => void
}

function Field({ icon, label, value, href }: { icon: React.ReactNode; label: string; value: React.ReactNode; href?: string }) {
  return (
    <div style={{ display: 'flex', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div style={{ color: 'var(--color-text-secondary)', marginTop: 2, flexShrink: 0 }}>{icon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginBottom: 2 }}>{label}</div>
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer"
            style={{ color: '#60A5FA', textDecoration: 'none', wordBreak: 'break-all', fontSize: 13 }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            {value}
          </a>
        ) : (
          <div style={{ color: 'var(--color-text-primary)', wordBreak: 'break-all', fontSize: 13 }}>{value || '—'}</div>
        )}
      </div>
    </div>
  )
}

export default function LeadDrawer({ lead, onClose }: Props) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      {/* Overlay */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.6)',
          zIndex: 40,
          opacity: lead ? 1 : 0,
          pointerEvents: lead ? 'auto' : 'none',
          transition: 'opacity 0.2s',
        }}
      />

      {/* Drawer */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 400,
          background: 'var(--color-bg-secondary)',
          borderLeft: '1px solid var(--color-border)',
          zIndex: 50,
          transform: lead ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}
      >
        {lead && (
          <>
            {/* Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}>
              <div style={{ flex: 1 }}>
                <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, fontFamily: 'var(--font-display)', color: 'var(--color-text-primary)' }}>
                  {lead.name}
                </h2>
                <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                  <span style={{
                    background: 'rgba(225,29,46,0.12)',
                    color: 'var(--color-accent)',
                    border: '1px solid rgba(225,29,46,0.25)',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 500,
                  }}>{lead.city}</span>
                  <span style={{
                    background: lead.business_status === 'OPERATIONAL' ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                    color: lead.business_status === 'OPERATIONAL' ? 'var(--color-success)' : '#F87171',
                    border: `1px solid ${lead.business_status === 'OPERATIONAL' ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)'}`,
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 500,
                  }}>
                    {lead.business_status === 'OPERATIONAL' ? 'Operacional' : lead.business_status === 'CLOSED_TEMPORARILY' ? 'Fechado temp.' : 'Fechado perm.'}
                  </span>
                  <span style={{
                    background: lead.klaviyo_synced ? 'rgba(34,197,94,0.12)' : 'rgba(156,163,175,0.12)',
                    color: lead.klaviyo_synced ? 'var(--color-success)' : 'var(--color-text-secondary)',
                    border: `1px solid ${lead.klaviyo_synced ? 'rgba(34,197,94,0.25)' : 'rgba(156,163,175,0.2)'}`,
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}>
                    {lead.klaviyo_synced ? <CheckCircle size={10} /> : <Circle size={10} />}
                    Klaviyo
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  padding: 4,
                  borderRadius: 4,
                  display: 'flex',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-border)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <X size={18} />
              </button>
            </div>

            {/* Stats row */}
            <div style={{
              display: 'flex',
              gap: 0,
              borderBottom: '1px solid var(--color-border)',
            }}>
              <div style={{ flex: 1, padding: '12px 20px', borderRight: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Star size={14} style={{ color: '#FBBF24' }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {lead.rating?.toFixed(1) ?? '—'}
                  </span>
                </div>
                <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginTop: 2 }}>Rating</div>
              </div>
              <div style={{ flex: 1, padding: '12px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Users size={14} style={{ color: 'var(--color-text-secondary)' }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {formatReviews(lead.total_reviews)}
                  </span>
                </div>
                <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginTop: 2 }}>Reviews</div>
              </div>
            </div>

            {/* Fields */}
            <div style={{ padding: '0 20px', flex: 1 }}>
              <Field icon={<MapPin size={14} />} label="Endereço" value={lead.address} />
              <Field
                icon={<Phone size={14} />}
                label="Telefone"
                value={lead.phone}
                href={lead.phone ? `https://wa.me/${lead.phone.replace(/\D/g, '')}` : undefined}
              />
              <Field
                icon={<Mail size={14} />}
                label="Email"
                value={lead.email}
                href={lead.email ? `mailto:${lead.email}` : undefined}
              />
              <Field
                icon={<Globe size={14} />}
                label="Website"
                value={lead.website}
                href={lead.website ?? undefined}
              />
              <Field
                icon={<Instagram size={14} />}
                label="Instagram"
                value={lead.instagram_url}
                href={lead.instagram_url ?? undefined}
              />
              <Field
                icon={<Facebook size={14} />}
                label="Facebook"
                value={lead.facebook_url}
                href={lead.facebook_url ?? undefined}
              />
              <Field icon={<Star size={14} />} label="Fonte" value={lead.source === 'google_places' ? 'Google Places' : 'Páginas Amarillas'} />
              <Field icon={<CheckCircle size={14} />} label="Status" value={lead.status} />
              <Field icon={<CheckCircle size={14} />} label="Criado em" value={new Date(lead.created_at).toLocaleString('pt-PT')} />
            </div>

            {/* Action buttons */}
            <div style={{ padding: 20, borderTop: '1px solid var(--color-border)', display: 'flex', gap: 8 }}>
              {lead.phone && (
                <a
                  href={`https://wa.me/${lead.phone.replace(/\D/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    padding: '8px 12px',
                    background: 'rgba(34,197,94,0.12)',
                    border: '1px solid rgba(34,197,94,0.3)',
                    color: 'var(--color-success)',
                    borderRadius: 6,
                    textDecoration: 'none',
                    fontSize: 13,
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  <MessageCircle size={14} />
                  WhatsApp
                </a>
              )}
              {lead.website && (
                <a
                  href={lead.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    padding: '8px 12px',
                    background: 'rgba(59,130,246,0.12)',
                    border: '1px solid rgba(59,130,246,0.3)',
                    color: '#93C5FD',
                    borderRadius: 6,
                    textDecoration: 'none',
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  <Globe size={14} />
                  Website
                </a>
              )}
              {!lead.website && lead.instagram_url && (
                <a
                  href={lead.instagram_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    padding: '8px 12px',
                    background: 'rgba(244,114,182,0.12)',
                    border: '1px solid rgba(244,114,182,0.3)',
                    color: '#F9A8D4',
                    borderRadius: 6,
                    textDecoration: 'none',
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  <Instagram size={14} />
                  Instagram
                </a>
              )}
              {!lead.website && !lead.instagram_url && lead.facebook_url && (
                <a
                  href={lead.facebook_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    padding: '8px 12px',
                    background: 'rgba(59,130,246,0.12)',
                    border: '1px solid rgba(59,130,246,0.3)',
                    color: '#93C5FD',
                    borderRadius: 6,
                    textDecoration: 'none',
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  <Facebook size={14} />
                  Facebook
                </a>
              )}
              <button
                onClick={onClose}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  background: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Fechar
              </button>
            </div>
          </>
        )}
      </div>
    </>
  )
}

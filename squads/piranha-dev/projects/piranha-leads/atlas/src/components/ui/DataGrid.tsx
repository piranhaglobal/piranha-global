import { useState } from 'react'
import { ChevronRight, ChevronUp, ChevronDown } from 'lucide-react'
import type { Lead } from '../../types'
import { formatReviews } from '../../lib/utils'

type SortKey = 'name' | 'city' | 'rating' | 'total_reviews'
type SortDir = 'asc' | 'desc'

interface Props {
  leads: Lead[]
  onSelectLead: (lead: Lead) => void
  selectedIds: Set<number>
  onToggleSelect: (id: number) => void
  onToggleAll: () => void
  selectable?: boolean
}

function SourceBadge({ source }: { source: string }) {
  const isGoogle = source === 'google_places'
  return (
    <span style={{
      background: isGoogle ? 'rgba(59,130,246,0.15)' : 'rgba(168,85,247,0.15)',
      color: isGoogle ? '#93C5FD' : '#C084FC',
      border: `1px solid ${isGoogle ? 'rgba(59,130,246,0.3)' : 'rgba(168,85,247,0.3)'}`,
    }} className="px-2 py-0.5 rounded text-xs font-medium">
      {isGoogle ? 'Google' : 'PAmr'}
    </span>
  )
}

function CityBadge({ city }: { city: string }) {
  return (
    <span style={{
      background: 'rgba(225,29,46,0.12)',
      color: 'var(--color-accent)',
      border: '1px solid rgba(225,29,46,0.25)',
    }} className="px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap">
      {city}
    </span>
  )
}

function RatingBar({ rating }: { rating: number | null }) {
  if (rating === null) return <span style={{ color: 'var(--color-text-secondary)' }}>—</span>
  const pct = (rating / 5) * 100
  return (
    <div className="flex items-center gap-2">
      <div style={{ background: 'var(--color-border)', borderRadius: 2 }} className="w-14 h-1.5">
        <div style={{
          width: `${pct}%`,
          background: rating >= 4 ? 'var(--color-success)' : rating >= 3 ? 'var(--color-warning)' : 'var(--color-accent)',
          borderRadius: 2,
          height: '100%',
        }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)', fontSize: 12 }}>
        {rating.toFixed(1)}
      </span>
    </div>
  )
}

type ExtendedSortKey = SortKey | 'created_at'

function formatCreatedAt(value: string) {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const parsed = new Date(normalized)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString('pt-PT')
}

export default function DataGrid({ leads, onSelectLead, selectedIds, onToggleSelect, onToggleAll, selectable = true }: Props) {
  const [sortKey, setSortKey] = useState<ExtendedSortKey>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(key: ExtendedSortKey) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = [...leads].sort((a, b) => {
    const av = a[sortKey] ?? (sortDir === 'asc' ? Infinity : -Infinity)
    const bv = b[sortKey] ?? (sortDir === 'asc' ? Infinity : -Infinity)
    if (typeof av === 'string' && typeof bv === 'string') {
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    }
    return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const allSelected = leads.length > 0 && leads.every(l => selectedIds.has(l.id))

  function SortIcon({ col }: { col: ExtendedSortKey }) {
    if (sortKey !== col) return <ChevronUp size={12} style={{ opacity: 0.3 }} />
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
  }

  const thStyle: React.CSSProperties = {
    background: 'var(--color-bg-secondary)',
    color: 'var(--color-text-secondary)',
    borderBottom: '1px solid var(--color-border)',
    padding: '8px 12px',
    fontSize: 12,
    fontWeight: 500,
    textAlign: 'left',
    whiteSpace: 'nowrap',
    position: 'sticky',
    top: 0,
    zIndex: 10,
    userSelect: 'none',
  }

  return (
    <div style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: '100%' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {selectable && (
              <th style={{ ...thStyle, width: 36 }}>
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onToggleAll}
                  style={{ accentColor: 'var(--color-accent)', cursor: 'pointer' }}
                />
              </th>
            )}
            <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('name')}>
              <span className="flex items-center gap-1">Nome <SortIcon col="name" /></span>
            </th>
            <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('city')}>
              <span className="flex items-center gap-1">Cidade <SortIcon col="city" /></span>
            </th>
            <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('rating')}>
              <span className="flex items-center gap-1">Rating <SortIcon col="rating" /></span>
            </th>
            <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('total_reviews')}>
              <span className="flex items-center gap-1">Reviews <SortIcon col="total_reviews" /></span>
            </th>
            <th style={thStyle}>Telefone</th>
            <th style={thStyle}>Email</th>
            <th style={thStyle}>Fonte</th>
            <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('created_at')}>
              <span className="flex items-center gap-1">Criado em <SortIcon col="created_at" /></span>
            </th>
            <th style={thStyle}>Validado</th>
            <th style={thStyle}>Klaviyo</th>
            <th style={{ ...thStyle, width: 36 }}></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((lead, idx) => {
            const isSelected = selectedIds.has(lead.id)
            const isEven = idx % 2 === 0
            return (
              <tr
                key={lead.id}
                style={{
                  background: isSelected
                    ? 'rgba(225,29,46,0.08)'
                    : isEven ? 'transparent' : 'rgba(255,255,255,0.01)',
                  transition: 'background 0.1s',
                  cursor: 'default',
                }}
                onMouseEnter={e => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'var(--color-bg-surface)'
                }}
                onMouseLeave={e => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.background = isEven ? 'transparent' : 'rgba(255,255,255,0.01)'
                }}
              >
                {selectable && (
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(lead.id)}
                      style={{ accentColor: 'var(--color-accent)', cursor: 'pointer' }}
                    />
                  </td>
                )}
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)', maxWidth: 200 }}>
                  <span style={{ color: 'var(--color-text-primary)', fontWeight: 500 }} className="truncate block">
                    {lead.name}
                  </span>
                  {lead.address && (
                    <span style={{ color: 'var(--color-text-secondary)', fontSize: 11 }} className="truncate block">
                      {lead.address}
                    </span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <CityBadge city={lead.city} />
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <RatingBar rating={lead.rating} />
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)', fontSize: 12 }}>
                  {formatReviews(lead.total_reviews)}
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)' }}>
                  {lead.phone ? (
                    <a
                      href={`https://wa.me/${lead.phone.replace(/\D/g, '')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#4ADE80', textDecoration: 'none', fontFamily: 'var(--font-mono)', fontSize: 12 }}
                      onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                      onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                    >
                      {lead.phone}
                    </a>
                  ) : (
                    <span style={{ color: 'var(--color-text-secondary)' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)', maxWidth: 180 }}>
                  {lead.email ? (
                    <a
                      href={`mailto:${lead.email}`}
                      style={{ color: '#60A5FA', textDecoration: 'none', fontSize: 12, fontFamily: 'var(--font-mono)' }}
                      className="truncate block"
                      onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                      onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                    >
                      {lead.email}
                    </a>
                  ) : (
                    <span style={{ color: 'var(--color-text-secondary)' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <SourceBadge source={lead.source} />
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)', fontSize: 12, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>
                  {formatCreatedAt(lead.created_at)}
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)', textAlign: 'center' }}>
                  {lead.validated_at ? (
                    <span style={{
                      background: 'rgba(34,197,94,0.12)',
                      color: 'var(--color-success)',
                      border: '1px solid rgba(34,197,94,0.25)',
                      borderRadius: 4,
                      padding: '2px 7px',
                      fontSize: 11,
                      fontWeight: 600,
                    }}>SIM</span>
                  ) : (
                    <span style={{
                      background: 'rgba(148,163,184,0.08)',
                      color: 'var(--color-text-secondary)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 4,
                      padding: '2px 7px',
                      fontSize: 11,
                    }}>NÃO</span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border-subtle)', textAlign: 'center' }}>
                  {lead.klaviyo_synced === 1 ? (
                    <span style={{ color: 'var(--color-success)', fontSize: 14 }}>✓</span>
                  ) : (
                    <span style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>○</span>
                  )}
                </td>
                <td style={{ padding: '8px 8px', borderBottom: '1px solid var(--color-border-subtle)' }}>
                  <button
                    onClick={() => onSelectLead(lead)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--color-text-secondary)',
                      cursor: 'pointer',
                      padding: '2px 4px',
                      borderRadius: 4,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLElement).style.color = 'var(--color-text-primary)'
                      ;(e.currentTarget as HTMLElement).style.background = 'var(--color-border)'
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.color = 'var(--color-text-secondary)'
                      ;(e.currentTarget as HTMLElement).style.background = 'transparent'
                    }}
                  >
                    <ChevronRight size={14} />
                  </button>
                </td>
              </tr>
            )
          })}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={selectable ? 12 : 11} style={{ padding: 48, textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                Nenhum lead encontrado com os filtros actuais.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

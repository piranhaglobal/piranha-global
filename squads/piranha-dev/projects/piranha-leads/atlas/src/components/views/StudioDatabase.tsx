import { useState, useEffect, useMemo, useRef } from 'react'
import { Filter, Download, RefreshCw, Loader, ShieldCheck, X, CheckCircle, AlertCircle, Trash2, Sparkles } from 'lucide-react'
import type { Lead } from '../../types'
import { fetchLeads, startEnrichment, startValidation } from '../../services/leadsService'
import { triggerKlaviyoSync } from '../../services/klaviyoService'
import DataGrid from '../ui/DataGrid'
import LeadDrawer from '../ui/LeadDrawer'
import KlaviyoSyncBar from '../ui/KlaviyoSyncBar'
import type { KlaviyoSyncResult } from '../../types'

interface Filters {
  search: string
  ratingMin: number
  reviewsMin: number
  businessStatus: string
  source: string
  klaviyo: string
  quickFilter: '' | 'missing_email' | 'missing_phone' | 'missing_website' | 'missing_social' | 'needs_enrich'
}

interface ValidationProgress {
  mode: 'validate' | 'enrich'
  phase: 'running' | 'done'
  index: number
  total: number
  currentName: string
  changed: number
  websiteCount: number
  emailCount: number
  phoneCount: number
  socialCount: number
  klaviyoSynced: number
  log: Array<{ name: string; changed: boolean; details: string }>
}

function exportCSV(leadsToExport: Lead[]) {
  const fields: (keyof Lead)[] = [
    'id', 'name', 'city', 'address', 'phone', 'website', 'email',
    'instagram_url', 'facebook_url', 'rating', 'total_reviews',
    'business_status', 'source', 'status', 'klaviyo_synced', 'created_at'
  ]
  const header = fields.join(',')
  const rows = leadsToExport.map(l =>
    fields.map(f => {
      const v = l[f]
      if (v === null || v === undefined) return ''
      return `"${String(v).replace(/"/g, '""')}"`
    }).join(',')
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `piranha_atlas_export_${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function StudioDatabase() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [drawerLead, setDrawerLead] = useState<Lead | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [showFilters, setShowFilters] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<KlaviyoSyncResult | null>(null)
  const [validating, setValidating] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [validationProgress, setValidationProgress] = useState<ValidationProgress | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const validationEsRef = useRef<EventSource | null>(null)
  const [filters, setFilters] = useState<Filters>({
    search: '',
    ratingMin: 0,
    reviewsMin: 0,
    businessStatus: '',
    source: '',
    klaviyo: '',
    quickFilter: '',
  })

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchLeads()
      setLeads(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const onLeadsUpdated = () => load()
    window.addEventListener('piranha:leads-updated', onLeadsUpdated)
    return () => window.removeEventListener('piranha:leads-updated', onLeadsUpdated)
  }, [])

  const filtered = useMemo(() => {
    return leads.filter(l => {
      if (filters.search) {
        const q = filters.search.toLowerCase()
        if (!l.name.toLowerCase().includes(q) &&
          !l.city.toLowerCase().includes(q) &&
          !(l.email?.toLowerCase().includes(q)) &&
          !(l.phone?.includes(q)) &&
          !(l.instagram_url?.toLowerCase().includes(q)) &&
          !(l.facebook_url?.toLowerCase().includes(q))) return false
      }
      if (filters.ratingMin > 0 && (l.rating ?? 0) < filters.ratingMin) return false
      if (filters.reviewsMin > 0 && (l.total_reviews ?? 0) < filters.reviewsMin) return false
      if (filters.businessStatus && l.business_status !== filters.businessStatus) return false
      if (filters.source && l.source !== filters.source) return false
      if (filters.klaviyo === 'synced' && l.klaviyo_synced !== 1) return false
      if (filters.klaviyo === 'unsynced' && l.klaviyo_synced !== 0) return false
      if (filters.quickFilter === 'missing_email' && !!l.email) return false
      if (filters.quickFilter === 'missing_phone' && !!l.phone) return false
      if (filters.quickFilter === 'missing_website' && !!l.website) return false
      if (filters.quickFilter === 'missing_social' && (!!l.instagram_url || !!l.facebook_url)) return false
      if (filters.quickFilter === 'needs_enrich' && l.email && l.phone && l.website && (l.instagram_url || l.facebook_url)) return false
      return true
    })
  }, [leads, filters])

  const quickFilters: Array<{ key: Filters['quickFilter']; label: string }> = [
    { key: 'missing_email', label: 'Sem email' },
    { key: 'missing_phone', label: 'Sem telefone' },
    { key: 'missing_website', label: 'Sem website' },
    { key: 'missing_social', label: 'Sem social' },
    { key: 'needs_enrich', label: 'Precisa enrich' },
  ]

  function handleToggleSelect(id: number) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleToggleAll() {
    if (filtered.every(l => selectedIds.has(l.id))) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filtered.map(l => l.id)))
    }
  }

  function handleExport() {
    const toExport = selectedIds.size > 0
      ? filtered.filter(l => selectedIds.has(l.id))
      : filtered
    exportCSV(toExport)
  }

  async function handleSync() {
    setSyncing(true)
    setSyncResult(null)
    try {
      const result = await triggerKlaviyoSync()
      setSyncResult(result)
      await load()
    } catch {
      // silent
    } finally {
      setSyncing(false)
    }
  }

  async function handleDelete() {
    if (deleting || selectedIds.size === 0) return
    setDeleting(true)
    setDeleteConfirm(false)
    try {
      await fetch('/api/leads', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedIds) }),
      })
      setSelectedIds(new Set())
      await load()
    } catch { /* silent */ }
    finally { setDeleting(false) }
  }

  async function handleValidate() {
    if (validating || enriching || selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    setValidating(true)
    setValidationProgress({
      mode: 'validate', phase: 'running', index: 0, total: ids.length, currentName: '...',
      changed: 0, websiteCount: 0, emailCount: 0, phoneCount: 0, socialCount: 0,
      klaviyoSynced: 0, log: [],
    })

    function cleanup(es: EventSource) {
      es.close()
      validationEsRef.current = null
    }

    try {
      const valId = await startValidation(ids, false)

      // Abrir SSE imediatamente após receber o val_id
      // A queue no servidor preserva todos os eventos mesmo se chegarem antes da ligação
      await new Promise<void>((resolve) => {
        const es = new EventSource(`/api/leads/validate/${valId}/stream`)
        validationEsRef.current = es

        es.onopen = () => resolve()

        // fallback: se onopen não disparar em 500ms, continua na mesma
        setTimeout(resolve, 500)

        es.onmessage = (e) => {
          try {
            const event = JSON.parse(e.data)
            if (event.type === 'ping') return

            if (event.type === 'lead_check') {
              const details: string[] = []
              if (event.website_cleared) details.push('website limpo')
              if (event.email_cleared)   details.push('email limpo')
              if (event.phone_cleared)   details.push('telefone limpo')

              setValidationProgress(p => {
                if (!p) return p
                return {
                  ...p,
                  index: event.index,
                  total: event.total,
                  currentName: event.name,
                  changed: p.changed + (event.changed ? 1 : 0),
                  websiteCount: p.websiteCount + (event.website_cleared ? 1 : 0),
                  emailCount:   p.emailCount   + (event.email_cleared   ? 1 : 0),
                  phoneCount:   p.phoneCount   + (event.phone_cleared   ? 1 : 0),
                  log: event.changed
                    ? [{ name: event.name, changed: true, details: details.join(', ') }, ...p.log].slice(0, 50)
                    : p.log,
                }
              })
            }

            if (event.type === 'validation_complete') {
              setValidationProgress(p => p ? {
                ...p,
                phase: 'done',
                index: event.total,
                total: event.total,
                changed: event.changed,
                websiteCount: event.cleared_website,
                emailCount:   event.cleared_email,
                phoneCount:   event.cleared_phone,
                klaviyoSynced:  event.klaviyo_synced,
              } : p)
              setValidating(false)
              cleanup(es)
              load()
            }
          } catch { /* parse error silencioso */ }
        }

        es.onerror = () => {
          setValidating(false)
          cleanup(es)
          load()
        }
      })
    } catch (err) {
      console.error('Validation error:', err)
      setValidating(false)
      setValidationProgress(p => p ? { ...p, phase: 'done' } : null)
    }
  }

  async function handleEnrich() {
    if (enriching || validating || selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    setEnriching(true)
    setValidationProgress({
      mode: 'enrich', phase: 'running', index: 0, total: ids.length, currentName: '...',
      changed: 0, websiteCount: 0, emailCount: 0, phoneCount: 0, socialCount: 0,
      klaviyoSynced: 0, log: [],
    })

    function cleanup(es: EventSource) {
      es.close()
      validationEsRef.current = null
    }

    try {
      const enrichId = await startEnrichment(ids)

      await new Promise<void>((resolve) => {
        const es = new EventSource(`/api/leads/enrich/${enrichId}/stream`)
        validationEsRef.current = es

        es.onopen = () => resolve()
        setTimeout(resolve, 500)

        es.onmessage = (e) => {
          try {
            const event = JSON.parse(e.data)
            if (event.type === 'ping') return

            if (event.type === 'lead_enrich') {
              setValidationProgress(p => {
                if (!p) return p
                return {
                  ...p,
                  index: event.index,
                  total: event.total,
                  currentName: event.name,
                  changed: p.changed + (event.changed ? 1 : 0),
                  websiteCount: p.websiteCount + (event.website_found ? 1 : 0),
                  emailCount: p.emailCount + (event.email_found ? 1 : 0),
                  phoneCount: p.phoneCount + (event.phone_found ? 1 : 0),
                  socialCount: p.socialCount + (event.social_found ? 1 : 0),
                  log: event.changed
                    ? [{ name: event.name, changed: true, details: event.details || 'atualizado' }, ...p.log].slice(0, 50)
                    : p.log,
                }
              })
            }

            if (event.type === 'enrichment_complete') {
              setValidationProgress(p => p ? {
                ...p,
                phase: 'done',
                index: event.total,
                total: event.total,
                changed: event.changed,
                websiteCount: event.found_website,
                emailCount: event.found_email,
                phoneCount: event.found_phone,
                socialCount: event.found_social,
                klaviyoSynced: 0,
              } : p)
              setEnriching(false)
              cleanup(es)
              load()
            }
          } catch {
            // silent
          }
        }

        es.onerror = () => {
          setEnriching(false)
          cleanup(es)
          load()
        }
      })
    } catch (err) {
      console.error('Enrichment error:', err)
      setEnriching(false)
      setValidationProgress(p => p ? { ...p, phase: 'done' } : null)
    }
  }

  const selectStyle: React.CSSProperties = {
    background: 'var(--color-bg-surface)',
    border: '1px solid var(--color-border)',
    color: 'var(--color-text-primary)',
    padding: '6px 10px',
    borderRadius: 6,
    fontSize: 13,
    outline: 'none',
  }

  const inputStyle: React.CSSProperties = {
    background: 'var(--color-bg-surface)',
    border: '1px solid var(--color-border)',
    color: 'var(--color-text-primary)',
    padding: '6px 10px',
    borderRadius: 6,
    fontSize: 13,
    outline: 'none',
    width: '100%',
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        flexShrink: 0,
        background: 'var(--color-bg-secondary)',
      }}>
        <input
          type="text"
          placeholder="Pesquisar por nome, cidade, email..."
          value={filters.search}
          onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          style={{ ...inputStyle, width: 280 }}
        />

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {quickFilters.map(filter => {
            const active = filters.quickFilter === filter.key
            return (
              <button
                key={filter.key}
                onClick={() => setFilters(f => ({ ...f, quickFilter: active ? '' : filter.key }))}
                style={{
                  padding: '6px 10px',
                  background: active ? 'rgba(245,158,11,0.14)' : 'transparent',
                  border: `1px solid ${active ? 'rgba(245,158,11,0.35)' : 'var(--color-border)'}`,
                  color: active ? '#FBBF24' : 'var(--color-text-secondary)',
                  borderRadius: 999,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {filter.label}
              </button>
            )
          })}
        </div>

        <button
          onClick={() => setShowFilters(f => !f)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: showFilters ? 'var(--color-bg-surface)' : 'transparent',
            border: '1px solid var(--color-border)',
            color: showFilters ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            borderRadius: 6,
            fontSize: 13,
            cursor: 'pointer',
          }}
        >
          <Filter size={13} />
          Filtros
        </button>

        <div style={{ flex: 1 }} />

        <span style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>
          <span style={{ color: 'var(--color-text-primary)', fontWeight: 500 }}>{filtered.length}</span> studios
          {selectedIds.size > 0 && (
            <> · <span style={{ color: 'var(--color-accent)', fontWeight: 500 }}>{selectedIds.size}</span> seleccionados</>
          )}
        </span>

        {selectedIds.size > 0 && (
          <button
            onClick={() => setDeleteConfirm(true)}
            disabled={deleting}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.35)',
              color: '#F87171',
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 500,
              cursor: deleting ? 'not-allowed' : 'pointer',
            }}
          >
            {deleting
              ? <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />
              : <Trash2 size={13} />}
            Apagar ({selectedIds.size})
          </button>
        )}

        {selectedIds.size > 0 && (
          <button
            onClick={handleEnrich}
            disabled={enriching || validating}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              background: enriching ? 'rgba(245,158,11,0.18)' : 'rgba(245,158,11,0.12)',
              border: '1px solid rgba(245,158,11,0.35)',
              color: '#FBBF24',
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 500,
              cursor: enriching || validating ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {enriching
              ? <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />
              : <Sparkles size={13} />}
            Enriquecer Leads ({selectedIds.size})
          </button>
        )}

        {selectedIds.size > 0 && (
          <button
            onClick={handleValidate}
            disabled={validating || enriching}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              background: validating ? 'var(--color-accent-dim)' : 'rgba(225,29,46,0.12)',
              border: '1px solid rgba(225,29,46,0.4)',
              color: 'var(--color-accent)',
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 500,
              cursor: validating || enriching ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {validating
              ? <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />
              : <ShieldCheck size={13} />}
            Validar Leads ({selectedIds.size})
          </button>
        )}

        <button
          onClick={handleExport}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'transparent',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)',
            borderRadius: 6,
            fontSize: 13,
            cursor: 'pointer',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--color-text-primary)'
            ;(e.currentTarget as HTMLElement).style.background = 'var(--color-bg-surface)'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--color-text-secondary)'
            ;(e.currentTarget as HTMLElement).style.background = 'transparent'
          }}
        >
          <Download size={13} />
          Export CSV
        </button>

        <button
          onClick={load}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '6px',
            background: 'transparent',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)',
            borderRadius: 6,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={13} />}
        </button>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-bg-surface)',
          display: 'flex',
          gap: 16,
          flexWrap: 'wrap',
          alignItems: 'flex-end',
          flexShrink: 0,
        }}>
          <div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginBottom: 4 }}>Rating mínimo ({filters.ratingMin})</div>
            <input
              type="range"
              min={0} max={5} step={0.5}
              value={filters.ratingMin}
              onChange={e => setFilters(f => ({ ...f, ratingMin: Number(e.target.value) }))}
              style={{ accentColor: 'var(--color-accent)', width: 120 }}
            />
          </div>
          <div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginBottom: 4 }}>Reviews mínimas ({filters.reviewsMin})</div>
            <input
              type="range"
              min={0} max={500} step={10}
              value={filters.reviewsMin}
              onChange={e => setFilters(f => ({ ...f, reviewsMin: Number(e.target.value) }))}
              style={{ accentColor: 'var(--color-accent)', width: 120 }}
            />
          </div>
          <div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginBottom: 4 }}>Status</div>
            <select value={filters.businessStatus} onChange={e => setFilters(f => ({ ...f, businessStatus: e.target.value }))} style={selectStyle}>
              <option value="">Todos</option>
              <option value="OPERATIONAL">Operacional</option>
              <option value="CLOSED_TEMPORARILY">Fechado temp.</option>
              <option value="CLOSED_PERMANENTLY">Fechado perm.</option>
            </select>
          </div>
          <div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginBottom: 4 }}>Fonte</div>
            <select value={filters.source} onChange={e => setFilters(f => ({ ...f, source: e.target.value }))} style={selectStyle}>
              <option value="">Todas</option>
              <option value="google_places">Google Places</option>
              <option value="paginasamarillas">Páginas Amarillas</option>
            </select>
          </div>
          <div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginBottom: 4 }}>Klaviyo</div>
            <select value={filters.klaviyo} onChange={e => setFilters(f => ({ ...f, klaviyo: e.target.value }))} style={selectStyle}>
              <option value="">Todos</option>
              <option value="synced">Sincronizados</option>
              <option value="unsynced">Pendentes</option>
            </select>
          </div>
          <button
            onClick={() => setFilters({ search: '', ratingMin: 0, reviewsMin: 0, businessStatus: '', source: '', klaviyo: '', quickFilter: '' })}
            style={{
              padding: '6px 12px',
              background: 'transparent',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)',
              borderRadius: 6,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            Limpar
          </button>
        </div>
      )}

      {/* Klaviyo bar */}
      <div style={{ padding: '8px 20px', flexShrink: 0, borderBottom: '1px solid var(--color-border)' }}>
        <KlaviyoSyncBar syncing={syncing} result={syncResult} onSync={handleSync} />
      </div>

      {/* Grid */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        {error ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#F87171', fontSize: 13 }}>
            Erro ao carregar: {error}
          </div>
        ) : loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
            A carregar leads...
          </div>
        ) : (
          <DataGrid
            leads={filtered}
            onSelectLead={setDrawerLead}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            onToggleAll={handleToggleAll}
          />
        )}
      </div>

      <LeadDrawer lead={drawerLead} onClose={() => setDrawerLead(null)} />

      {/* Delete Confirm Modal */}
      {deleteConfirm && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 50,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: 'var(--color-bg-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
            padding: 28,
            width: 380,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <Trash2 size={18} style={{ color: '#F87171' }} />
              <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color: 'var(--color-text-primary)' }}>
                Apagar {selectedIds.size} lead{selectedIds.size !== 1 ? 's' : ''}?
              </span>
            </div>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, margin: '0 0 20px' }}>
              Esta acção é irreversível. Os leads seleccionados serão removidos permanentemente da base de dados.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteConfirm(false)}
                style={{
                  padding: '8px 16px',
                  background: 'transparent',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                  borderRadius: 6,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                style={{
                  padding: '8px 16px',
                  background: '#EF4444',
                  border: 'none',
                  color: '#fff',
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Apagar definitivamente
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Validation Modal */}
      {validationProgress && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 50,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: 'var(--color-bg-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
            width: 480,
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              {validationProgress.phase === 'running'
                ? <Loader size={15} style={{ color: 'var(--color-accent)', animation: 'spin 1s linear infinite' }} />
                : <CheckCircle size={15} style={{ color: 'var(--color-success)' }} />}
              <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 15, color: 'var(--color-text-primary)' }}>
                {validationProgress.phase === 'running'
                  ? (validationProgress.mode === 'validate' ? 'A validar contactos...' : 'A enriquecer leads...')
                  : (validationProgress.mode === 'validate' ? 'Validação concluída' : 'Enriquecimento concluído')}
              </span>
              {validationProgress.phase === 'done' && (
                <button
                  onClick={() => { setValidationProgress(null); setSelectedIds(new Set()) }}
                  style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer', padding: 4 }}
                >
                  <X size={15} />
                </button>
              )}
            </div>

            {/* Progress bar */}
            <div style={{ padding: '12px 20px 0', flexShrink: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 6 }}>
                <span>{validationProgress.phase === 'running' ? validationProgress.currentName || '...' : 'Concluído'}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>
                  {validationProgress.index}/{validationProgress.total}
                </span>
              </div>
              <div style={{ background: 'var(--color-border)', borderRadius: 4, height: 4 }}>
                <div style={{
                  width: `${Math.round((validationProgress.index / validationProgress.total) * 100)}%`,
                  height: '100%',
                  background: validationProgress.phase === 'done' ? 'var(--color-success)' : 'var(--color-accent)',
                  borderRadius: 4,
                  transition: 'width 0.2s',
                }} />
              </div>
            </div>

            {/* Stats */}
            <div style={{
              padding: '12px 20px',
              display: 'flex',
              gap: 16,
              flexShrink: 0,
              borderBottom: '1px solid var(--color-border)',
            }}>
              {[
                { label: 'Alterados', value: validationProgress.changed, color: validationProgress.changed > 0 ? 'var(--color-warning)' : 'var(--color-text-secondary)' },
                { label: validationProgress.mode === 'validate' ? 'Website limpo' : 'Website', value: validationProgress.websiteCount, color: 'var(--color-text-secondary)' },
                { label: validationProgress.mode === 'validate' ? 'Email limpo' : 'Email', value: validationProgress.emailCount, color: 'var(--color-text-secondary)' },
                { label: validationProgress.mode === 'validate' ? 'Telefone limpo' : 'Telefone', value: validationProgress.phoneCount, color: 'var(--color-text-secondary)' },
                { label: validationProgress.mode === 'validate' ? 'Klaviyo sync' : 'Social', value: validationProgress.mode === 'validate' ? validationProgress.klaviyoSynced : validationProgress.socialCount, color: validationProgress.mode === 'validate' && validationProgress.klaviyoSynced > 0 ? 'var(--color-success)' : 'var(--color-text-secondary)' },
              ].map(s => (
                <div key={s.label} style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Log */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '8px 20px 16px' }}>
              {validationProgress.log.length === 0 && validationProgress.phase === 'running' && (
                <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, paddingTop: 8 }}>
                  {validationProgress.mode === 'validate'
                    ? 'A verificar leads — apenas alterações serão listadas aqui.'
                    : 'A enriquecer leads — apenas alterações serão listadas aqui.'}
                </div>
              )}
              {validationProgress.phase === 'done' && validationProgress.log.length === 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 8, color: 'var(--color-success)', fontSize: 13 }}>
                  <CheckCircle size={14} />
                  {validationProgress.mode === 'validate'
                    ? 'Todos os contactos estão válidos — nenhuma alteração necessária.'
                    : 'Nenhum dado adicional foi encontrado nesta tentativa.'}
                </div>
              )}
              {validationProgress.log.map((entry, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '5px 0',
                  borderBottom: '1px solid var(--color-border-subtle)',
                  fontSize: 12,
                }}>
                  <AlertCircle size={12} style={{ color: 'var(--color-warning)', flexShrink: 0 }} />
                  <span style={{ color: 'var(--color-text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.name}
                  </span>
                  <span style={{ color: 'var(--color-text-secondary)', flexShrink: 0 }}>{entry.details}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

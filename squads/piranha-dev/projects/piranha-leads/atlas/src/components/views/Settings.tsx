import { useState, useEffect, useRef } from 'react'
import { CheckCircle, XCircle, Loader, Key, Zap, Globe, RefreshCw, Terminal, Search, Mail, Trash2 } from 'lucide-react'
import type { KlaviyoList, StatusResponse, ScraperJob } from '../../types'
import { addKlaviyoList, fetchJobs, fetchKlaviyoLists, fetchStatus, removeKlaviyoList } from '../../services/klaviyoService'

function StatusDot({ ok }: { ok: boolean }) {
  return ok
    ? <CheckCircle size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
    : <XCircle size={14} style={{ color: '#F87171', flexShrink: 0 }} />
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--color-bg-secondary)',
      border: '1px solid var(--color-border)',
      borderRadius: 10,
      overflow: 'hidden',
      marginBottom: 16,
    }}>
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'var(--color-bg-surface)',
      }}>
        <span style={{ color: 'var(--color-accent)' }}>{icon}</span>
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14, color: 'var(--color-text-primary)' }}>
          {title}
        </span>
      </div>
      <div style={{ padding: 20 }}>
        {children}
      </div>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <span style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>{label}</span>
      <span style={{ color: 'var(--color-text-primary)', fontSize: 13, fontFamily: mono ? 'var(--font-mono)' : undefined }}>
        {value}
      </span>
    </div>
  )
}

interface EmailSearchState {
  running: boolean
  searchId: string | null
  index: number
  total: number
  found: number
  lastLead: string
  lastEmail: string | null
  done: boolean
}

export default function Settings() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [recentJobs, setRecentJobs] = useState<ScraperJob[]>([])
  const [listInput, setListInput] = useState('')
  const [listSaving, setListSaving] = useState(false)
  const [listMessage, setListMessage] = useState<string | null>(null)
  const [klaviyoLists, setKlaviyoLists] = useState<KlaviyoList[]>([])
  const [clearing, setClearing] = useState(false)
  const [clearResult, setClearResult] = useState<{ removed: number } | null>(null)
  const [clearConfirm, setClearConfirm] = useState(false)
  const [emailSearch, setEmailSearch] = useState<EmailSearchState>({
    running: false, searchId: null, index: 0, total: 0, found: 0, lastLead: '', lastEmail: null, done: false,
  })
  const esRef = useRef<EventSource | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [s, j, klaviyoData] = await Promise.all([fetchStatus(), fetchJobs(), fetchKlaviyoLists()])
      setStatus(s)
      setKlaviyoLists(klaviyoData.lists ?? [])
      setRecentJobs(j.slice(0, 5))
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function handleAddList() {
    if (!listInput.trim()) return
    setListSaving(true)
    setListMessage(null)
    try {
      const result = await addKlaviyoList(listInput.trim())
      setKlaviyoLists(result.lists)
      setListMessage(`Lista adicionada: ${result.added.name}`)
      setListInput('')
    } catch {
      setListMessage('Não foi possível importar esta List ID.')
    } finally {
      setListSaving(false)
    }
  }

  async function handleRemoveList(listId: string) {
    try {
      const result = await removeKlaviyoList(listId)
      setKlaviyoLists(result.lists)
    } catch {
      setListMessage('Não foi possível remover a lista.')
    }
  }

  async function handleClearList() {
    setClearing(true)
    setClearConfirm(false)
    setClearResult(null)
    try {
      const r = await fetch('/api/klaviyo/list', { method: 'DELETE' })
      const data = await r.json()
      setClearResult(data)
    } catch { /* silent */ }
    finally { setClearing(false) }
  }

  async function startEmailSearch() {
    if (emailSearch.running) return
    setEmailSearch({ running: true, searchId: null, index: 0, total: 0, found: 0, lastLead: '', lastEmail: null, done: false })

    const res = await fetch('/api/leads/search-emails', { method: 'POST' })
    const { search_id } = await res.json()

    const es = new EventSource(`/api/leads/search-emails/${search_id}/stream`)
    esRef.current = es

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'email_search_progress') {
        setEmailSearch(prev => ({
          ...prev,
          searchId: search_id,
          index: data.index,
          total: data.total,
          found: data.found_so_far,
          lastLead: data.name,
          lastEmail: data.email,
        }))
      } else if (data.type === 'email_search_complete') {
        setEmailSearch(prev => ({ ...prev, running: false, done: true, found: data.found, total: data.total }))
        es.close()
      }
    }
    es.onerror = () => {
      setEmailSearch(prev => ({ ...prev, running: false }))
      es.close()
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 40, display: 'flex', alignItems: 'center', gap: 10, color: 'var(--color-text-secondary)', fontSize: 13 }}>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
        A carregar configurações...
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', maxWidth: 700, overflowY: 'auto', height: '100%' }}>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
          Settings
        </h2>
        <button
          onClick={load}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'transparent',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)',
            borderRadius: 6,
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={12} />
          Actualizar
        </button>
      </div>

      {/* Google Places */}
      <Section title="Google Places API" icon={<Key size={15} />}>
        <Row
          label="Status"
          value={
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <StatusDot ok={status?.google_places.configured ?? false} />
              {status?.google_places.configured ? 'Configurado' : 'Não configurado'}
            </span>
          }
        />
        {status?.google_places.configured && (
          <Row label="Chave (preview)" value={status.google_places.key_preview} mono />
        )}
        {!status?.google_places.configured && (
          <div style={{ marginTop: 12, padding: '10px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6 }}>
            <div style={{ color: '#F87171', fontSize: 12, marginBottom: 4 }}>GOOGLE_PLACES_API_KEY não definida</div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
              Adicionar ao ficheiro .env na raiz do projecto
            </div>
          </div>
        )}
      </Section>

      {/* Klaviyo */}
      <Section title="Klaviyo" icon={<Zap size={15} />}>
        <Row
          label="Status"
          value={
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <StatusDot ok={status?.klaviyo.configured ?? false} />
              {status?.klaviyo.configured ? 'Configurado' : 'Não configurado'}
            </span>
          }
        />
        <Row label="List ID" value={status?.klaviyo.list_id ?? '—'} mono />

        <div style={{ marginTop: 16 }}>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 8 }}>
            Listas disponíveis no Atlas para sync manual a partir do Studio Database
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input
              value={listInput}
              onChange={e => setListInput(e.target.value)}
              placeholder="Adicionar List ID do Klaviyo"
              style={{
                flex: 1,
                background: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)',
                padding: '8px 10px',
                borderRadius: 6,
                fontSize: 13,
                outline: 'none',
              }}
            />
            <button
              onClick={handleAddList}
              disabled={listSaving || !listInput.trim()}
              style={{
                padding: '8px 12px',
                background: listSaving || !listInput.trim() ? 'var(--color-bg-surface)' : 'var(--color-accent)',
                border: 'none',
                color: listSaving || !listInput.trim() ? 'var(--color-text-secondary)' : '#fff',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: listSaving || !listInput.trim() ? 'not-allowed' : 'pointer',
              }}
            >
              {listSaving ? 'A validar...' : 'Importar List ID'}
            </button>
          </div>

          {listMessage && (
            <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--color-text-secondary)' }}>
              {listMessage}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {klaviyoLists.length === 0 && (
              <div style={{ padding: '10px 12px', border: '1px dashed var(--color-border)', borderRadius: 6, fontSize: 12, color: 'var(--color-text-secondary)' }}>
                Ainda não há listas importadas no Atlas.
              </div>
            )}
            {klaviyoLists.map(list => (
              <div key={list.id} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 10,
                padding: '10px 12px',
                background: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
              }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{list.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', marginTop: 3 }}>
                    {list.id}
                  </div>
                </div>
                <button
                  onClick={() => handleRemoveList(list.id)}
                  style={{
                    padding: '6px 10px',
                    background: 'rgba(239,68,68,0.08)',
                    border: '1px solid rgba(239,68,68,0.25)',
                    color: '#F87171',
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Remover
                </button>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--color-border-subtle)' }}>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 8 }}>
            Limpar lista — remove todos os profiles da lista Klaviyo
          </div>
          {clearResult && (
            <div style={{ marginBottom: 8, padding: '6px 10px', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, fontSize: 12, color: 'var(--color-success)' }}>
              {clearResult.removed} profiles removidos da lista
            </div>
          )}
          {clearConfirm ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Tem a certeza?</span>
              <button onClick={handleClearList} disabled={clearing} style={{ padding: '5px 12px', background: '#EF4444', border: 'none', color: '#fff', borderRadius: 5, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                {clearing ? <Loader size={11} style={{ animation: 'spin 1s linear infinite' }} /> : 'Confirmar'}
              </button>
              <button onClick={() => setClearConfirm(false)} style={{ padding: '5px 12px', background: 'transparent', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)', borderRadius: 5, fontSize: 12, cursor: 'pointer' }}>
                Cancelar
              </button>
            </div>
          ) : (
            <button
              onClick={() => setClearConfirm(true)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#F87171', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}
            >
              <Trash2 size={12} /> Limpar lista Klaviyo
            </button>
          )}
        </div>

        {recentJobs.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 8 }}>Últimos 5 jobs</div>
            {recentJobs.map(job => (
              <div key={job.id} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 0',
                borderBottom: '1px solid var(--color-border-subtle)',
                fontSize: 12,
              }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>#{job.id}</span>
                <span style={{ color: 'var(--color-text-primary)' }}>{job.leads_found} leads</span>
                <span style={{
                  color: job.status === 'completed' ? 'var(--color-success)' : job.status === 'running' ? 'var(--color-accent)' : '#F87171',
                  fontWeight: 500,
                }}>
                  {job.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Serper + Email Search */}
      <Section title="Serper (Google Search API)" icon={<Search size={15} />}>
        <Row
          label="Status"
          value={
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <StatusDot ok={status?.serper.configured ?? false} />
              {status?.serper.configured ? 'Configurado' : 'Não configurado'}
            </span>
          }
        />
        {status?.serper.configured && (
          <Row label="Chave (preview)" value={status.serper.key_preview} mono />
        )}

        {status?.serper.configured && (
          <div style={{ marginTop: 16 }}>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 10 }}>
              Busca emails em falta via Google Snippets
            </div>

            {/* Progress bar */}
            {(emailSearch.running || emailSearch.done) && emailSearch.total > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--color-text-secondary)', marginBottom: 4 }}>
                  <span>{emailSearch.index}/{emailSearch.total} leads</span>
                  <span style={{ color: 'var(--color-success)' }}>{emailSearch.found} encontrados</span>
                </div>
                <div style={{ height: 4, background: 'var(--color-border)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${(emailSearch.index / emailSearch.total) * 100}%`,
                    background: 'var(--color-accent)',
                    borderRadius: 2,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
                {emailSearch.lastLead && (
                  <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Mail size={10} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {emailSearch.lastLead}
                      {emailSearch.lastEmail && (
                        <span style={{ color: 'var(--color-success)', marginLeft: 6 }}>→ {emailSearch.lastEmail}</span>
                      )}
                    </span>
                  </div>
                )}
                {emailSearch.done && (
                  <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, fontSize: 12, color: 'var(--color-success)' }}>
                    Concluído — {emailSearch.found} emails encontrados em {emailSearch.total} leads
                  </div>
                )}
              </div>
            )}

            <button
              onClick={startEmailSearch}
              disabled={emailSearch.running}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 14px',
                background: emailSearch.running ? 'var(--color-bg-surface)' : 'var(--color-accent)',
                border: 'none',
                color: emailSearch.running ? 'var(--color-text-secondary)' : '#000',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: emailSearch.running ? 'not-allowed' : 'pointer',
              }}
            >
              {emailSearch.running
                ? <><Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> A pesquisar...</>
                : <><Search size={12} /> Buscar Emails em Falta</>
              }
            </button>
          </div>
        )}
      </Section>

      {/* Firecrawl */}
      <Section title="Firecrawl" icon={<Globe size={15} />}>
        <Row
          label="Status"
          value={
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <StatusDot ok={status?.firecrawl.online ?? false} />
              {status?.firecrawl.online ? 'Online' : 'Offline'}
            </span>
          }
        />
        <Row label="URL" value={status?.firecrawl.url ?? '—'} mono />

        {!status?.firecrawl.online && (
          <div style={{ marginTop: 12, padding: '10px 12px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 6 }}>
            <div style={{ color: 'var(--color-warning)', fontSize: 12, marginBottom: 6 }}>
              Firecrawl offline — extracção de emails e Páginas Amarillas desactivadas.
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-text-secondary)', fontSize: 12 }}>
              <Terminal size={11} />
              <span>Para activar, na raiz do projecto:</span>
            </div>
            <div style={{
              marginTop: 6,
              padding: '6px 10px',
              background: 'var(--color-bg-primary)',
              borderRadius: 4,
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              color: '#86EFAC',
            }}>
              docker-compose up -d
            </div>
          </div>
        )}
      </Section>
    </div>
  )
}

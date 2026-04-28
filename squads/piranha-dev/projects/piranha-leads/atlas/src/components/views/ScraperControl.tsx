import { useState, useEffect, useRef } from 'react'
import { Play, MapPin, Search, Mail, CheckSquare, Square, Loader, ChevronDown, ChevronUp, X } from 'lucide-react'
import type { Lead, ScraperJob, SSEEvent } from '../../types'
import { startJob, fetchJobLeads, fetchJobs } from '../../services/klaviyoService'
import JobFeed from '../ui/JobFeed'
import { EUROPEAN_COUNTRIES, getCitiesForCountries } from '../../data/europeanCities'
import DataGrid from '../ui/DataGrid'
import LeadDrawer from '../ui/LeadDrawer'

interface ProgressState {
  currentCity: string | null
  cityIndex: number
  totalCities: number
  leadsFound: number
  leadsWithEmail: number
  validatedCount: number
  enrichedCount: number
  phase: 'idle' | 'collecting' | 'klaviyo' | 'done'
}

export default function ScraperControl() {
  const [query, setQuery] = useState('estudio de tatuaje')
  const [selectedCountries, setSelectedCountries] = useState<string[]>(['ES'])
  const [selectedCities, setSelectedCities] = useState<string[]>(
    () => getCitiesForCountries(['ES'])
  )
  const [enrichEmail, setEnrichEmail] = useState(true)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<ProgressState>({
    currentCity: null, cityIndex: 0, totalCities: 0, leadsFound: 0, leadsWithEmail: 0,
    validatedCount: 0, enrichedCount: 0, phase: 'idle',
  })
  const [sseLog, setSseLog] = useState<SSEEvent[]>([])
  const [jobs, setJobs] = useState<ScraperJob[]>([])
  const [jobsLoading, setJobsLoading] = useState(true)
  const [jobLeads, setJobLeads] = useState<Lead[]>([])
  const [jobLeadsLoading, setJobLeadsLoading] = useState(false)
  const [selectedJob, setSelectedJob] = useState<ScraperJob | null>(null)
  const [drawerLead, setDrawerLead] = useState<Lead | null>(null)
  const [expandedCountries, setExpandedCountries] = useState<string[]>(['ES'])
  const esRef = useRef<EventSource | null>(null)

  async function loadJobs() {
    setJobsLoading(true)
    try {
      const data = await fetchJobs()
      setJobs(data)
    } catch { /* silent */ }
    finally { setJobsLoading(false) }
  }

  useEffect(() => {
    loadJobs()
    const onJobsUpdated = () => loadJobs()
    window.addEventListener('piranha:jobs-updated', onJobsUpdated)
    return () => window.removeEventListener('piranha:jobs-updated', onJobsUpdated)
  }, [])

  function toggleCountry(code: string) {
    const country = EUROPEAN_COUNTRIES.find(c => c.code === code)!
    const isSelected = selectedCountries.includes(code)

    if (isSelected) {
      setSelectedCountries(prev => prev.filter(c => c !== code))
      setSelectedCities(prev => prev.filter(city => !country.cities.includes(city)))
      setExpandedCountries(prev => prev.filter(c => c !== code))
    } else {
      setSelectedCountries(prev => [...prev, code])
      setSelectedCities(prev => [...new Set([...prev, ...country.cities])])
      setExpandedCountries(prev => [...prev, code])
    }
  }

  function toggleCity(city: string) {
    setSelectedCities(prev =>
      prev.includes(city) ? prev.filter(c => c !== city) : [...prev, city]
    )
  }

  function toggleAllCitiesInCountry(code: string) {
    const country = EUROPEAN_COUNTRIES.find(c => c.code === code)!
    const allSelected = country.cities.every(city => selectedCities.includes(city))
    if (allSelected) {
      setSelectedCities(prev => prev.filter(city => !country.cities.includes(city)))
    } else {
      setSelectedCities(prev => [...new Set([...prev, ...country.cities])])
    }
  }

  function toggleExpandCountry(code: string) {
    setExpandedCountries(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
  }

  async function handleStart() {
    if (running || selectedCities.length === 0) return
    setRunning(true)
    setSseLog([])
    setProgress({
      currentCity: null,
      cityIndex: 0,
      totalCities: selectedCities.length,
      leadsFound: 0,
      leadsWithEmail: 0,
      validatedCount: 0,
      enrichedCount: 0,
      phase: 'collecting',
    })

    try {
      const { job_id } = await startJob({
        query,
        cities: selectedCities,
        enrich_email: enrichEmail,
        use_firecrawl: false,
        validate_and_enrich: false,
        auto_klaviyo: false,
      })

      const es = new EventSource(`/api/jobs/${job_id}/stream`)
      esRef.current = es

      es.onmessage = (e) => {
        try {
          const event: SSEEvent = JSON.parse(e.data)
          if (event.type === 'ping') return

          setSseLog(prev => [...prev, event])

          if (event.type === 'city_start') {
            setProgress(p => ({
              ...p,
              currentCity: event.city ?? null,
              cityIndex: event.city_index ?? p.cityIndex,
              totalCities: event.total_cities ?? p.totalCities,
              phase: 'collecting',
            }))
          }

          if (event.type === 'city_progress') {
            setProgress(p => ({
              ...p,
              currentCity: event.city ?? null,
              cityIndex: event.city_index ?? p.cityIndex,
              totalCities: event.total_cities ?? p.totalCities,
              leadsFound: (p.leadsFound) + (event.leads_found ?? 0),
              leadsWithEmail: (p.leadsWithEmail) + (event.leads_with_email ?? 0),
            }))
          }

          if (event.type === 'job_complete' || event.type === '__done__') {
            setProgress(p => ({
              ...p,
              phase: 'done',
              leadsFound: event.total_leads ?? p.leadsFound,
              validatedCount: event.validated_count ?? p.validatedCount,
              enrichedCount: event.enriched_count ?? p.enrichedCount,
            }))
            setRunning(false)
            es.close()
            esRef.current = null
            loadJobs()
            // Notifica a Studio Database para recarregar
            window.dispatchEvent(new CustomEvent('piranha:leads-updated'))
          }
        } catch { /* parse error */ }
      }

      es.onerror = () => {
        setRunning(false)
        es.close()
        esRef.current = null
        loadJobs()
      }
    } catch {
      setRunning(false)
    }
  }

  async function handleOpenJob(job: ScraperJob) {
    setSelectedJob(job)
    setJobLeadsLoading(true)
    setJobLeads([])
    try {
      const leads = await fetchJobLeads(job.id)
      setJobLeads(leads)
    } catch {
      setJobLeads([])
    } finally {
      setJobLeadsLoading(false)
    }
  }

  const pct = progress.totalCities > 0
    ? Math.round((progress.cityIndex / progress.totalCities) * 100)
    : 0

  const emailPct = progress.leadsFound > 0
    ? Math.round((progress.leadsWithEmail / progress.leadsFound) * 100)
    : 0

  const toggleStyle = (active: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 14px',
    background: active ? 'rgba(225,29,46,0.12)' : 'var(--color-bg-surface)',
    border: `1px solid ${active ? 'rgba(225,29,46,0.35)' : 'var(--color-border)'}`,
    color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
    borderRadius: 6,
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: 500,
    transition: 'all 0.15s',
    userSelect: 'none',
  })

  return (
    <div style={{ height: '100%', display: 'flex', overflow: 'hidden' }}>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

      {/* Left: config panel */}
      <div style={{
        width: 380,
        flexShrink: 0,
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Config header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)' }}>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-display)', color: 'var(--color-text-primary)' }}>
            Configuração
          </h3>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Query */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 6 }}>
              <Search size={12} />
              Query de Pesquisa
            </div>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              disabled={running}
              style={{
                width: '100%',
                background: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)',
                padding: '8px 12px',
                borderRadius: 6,
                fontSize: 13,
                outline: 'none',
                opacity: running ? 0.6 : 1,
              }}
            />
          </div>

          {/* Toggles */}
          <div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 8 }}>Opções</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <button
                onClick={() => !running && setEnrichEmail(v => !v)}
                style={toggleStyle(enrichEmail)}
              >
                <Mail size={13} />
                Enriquecer emails
                {enrichEmail ? <CheckSquare size={13} style={{ marginLeft: 'auto' }} /> : <Square size={13} style={{ marginLeft: 'auto' }} />}
              </button>
            </div>
          </div>

          {/* Countries + Cities */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-text-secondary)', fontSize: 12, marginBottom: 8 }}>
              <MapPin size={12} />
              Países e Cidades · <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{selectedCities.length} cidades</span> seleccionadas
            </div>

            {/* Country selector pills */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 10 }}>
              {EUROPEAN_COUNTRIES.map(country => {
                const active = selectedCountries.includes(country.code)
                return (
                  <button
                    key={country.code}
                    onClick={() => !running && toggleCountry(country.code)}
                    title={country.name}
                    style={{
                      padding: '3px 8px',
                      borderRadius: 4,
                      fontSize: 12,
                      fontWeight: 500,
                      cursor: running ? 'not-allowed' : 'pointer',
                      border: active ? '1px solid rgba(225,29,46,0.4)' : '1px solid var(--color-border)',
                      background: active ? 'rgba(225,29,46,0.12)' : 'var(--color-bg-surface)',
                      color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                      transition: 'all 0.1s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <span>{country.flag}</span>
                    <span>{country.name}</span>
                  </button>
                )
              })}
            </div>

            {/* Cities grouped by selected country */}
            {selectedCountries.length > 0 && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                maxHeight: 260,
                overflowY: 'auto',
                padding: '8px',
                background: 'var(--color-bg-surface)',
                borderRadius: 6,
                border: '1px solid var(--color-border)',
              }}>
                {EUROPEAN_COUNTRIES.filter(c => selectedCountries.includes(c.code)).map(country => {
                  const isExpanded = expandedCountries.includes(country.code)
                  const allSelected = country.cities.every(city => selectedCities.includes(city))
                  const someSelected = country.cities.some(city => selectedCities.includes(city))
                  const selectedCount = country.cities.filter(city => selectedCities.includes(city)).length

                  return (
                    <div key={country.code}>
                      {/* Country header row */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: isExpanded ? 6 : 0 }}>
                        <button
                          onClick={() => !running && toggleExpandCountry(country.code)}
                          style={{
                            background: 'transparent', border: 'none',
                            color: 'var(--color-text-secondary)', cursor: 'pointer',
                            padding: 0, display: 'flex', alignItems: 'center',
                          }}
                        >
                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                        </button>
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {country.flag} {country.name}
                        </span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: someSelected ? 'var(--color-accent)' : 'var(--color-text-secondary)' }}>
                          {selectedCount}/{country.cities.length}
                        </span>
                        <button
                          onClick={() => !running && toggleAllCitiesInCountry(country.code)}
                          style={{
                            marginLeft: 'auto', background: 'transparent', border: 'none',
                            color: 'var(--color-accent)', fontSize: 10, cursor: 'pointer', padding: '1px 4px',
                          }}
                        >
                          {allSelected ? 'Limpar' : 'Todas'}
                        </button>
                      </div>

                      {/* Cities grid */}
                      {isExpanded && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, paddingLeft: 18 }}>
                          {country.cities.map(city => {
                            const active = selectedCities.includes(city)
                            return (
                              <button
                                key={city}
                                onClick={() => !running && toggleCity(city)}
                                style={{
                                  padding: '2px 7px',
                                  borderRadius: 3,
                                  fontSize: 11,
                                  cursor: running ? 'not-allowed' : 'pointer',
                                  border: active ? '1px solid rgba(225,29,46,0.4)' : '1px solid var(--color-border-subtle)',
                                  background: active ? 'rgba(225,29,46,0.12)' : 'transparent',
                                  color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                                  transition: 'all 0.1s',
                                }}
                              >
                                {city}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {selectedCountries.length === 0 && (
              <div style={{
                padding: '16px', textAlign: 'center', fontSize: 12,
                color: 'var(--color-text-secondary)', border: '1px dashed var(--color-border)',
                borderRadius: 6,
              }}>
                Selecciona pelo menos um país acima
              </div>
            )}
          </div>
        </div>

        {/* Start button */}
        <div style={{ padding: 16, borderTop: '1px solid var(--color-border)' }}>
          <button
            onClick={handleStart}
            disabled={running || selectedCities.length === 0}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              padding: '10px 20px',
              background: running ? 'var(--color-accent-dim)' : 'var(--color-accent)',
              border: 'none',
              color: '#fff',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              fontFamily: 'var(--font-display)',
              cursor: running || selectedCities.length === 0 ? 'not-allowed' : 'pointer',
              letterSpacing: '0.5px',
              transition: 'background 0.15s',
            }}
          >
            {running ? (
              <>
                <Loader size={15} style={{ animation: 'spin 1s linear infinite' }} />
                A Extrair...
              </>
            ) : (
              <>
                <Play size={15} />
                INICIAR EXTRACÇÃO
              </>
            )}
          </button>
        </div>
      </div>

      {/* Right: progress + jobs */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Progress panel */}
        {(running || progress.phase !== 'idle') && (
          <div style={{
            padding: '16px 24px',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-bg-surface)',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {progress.phase === 'collecting' && `Processando: ${progress.currentCity ?? '...'}`}
                {progress.phase === 'done' && 'Extracção concluída'}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-text-secondary)' }}>
                {progress.cityIndex}/{progress.totalCities} cidades · {pct}%
              </span>
            </div>

            {/* Progress bar */}
            <div style={{ background: 'var(--color-border)', borderRadius: 4, height: 4, marginBottom: 12 }}>
              <div style={{
                width: `${pct}%`,
                height: '100%',
                background: progress.phase === 'done' ? 'var(--color-success)' : 'var(--color-accent)',
                borderRadius: 4,
                transition: 'width 0.3s',
              }} />
            </div>

            <div style={{ display: 'flex', gap: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>Leads encontrados:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {progress.leadsFound}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>Com email:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600, color: 'var(--color-success)' }}>
                  {progress.leadsWithEmail} ({emailPct}%)
                </span>
              </div>
            </div>

            {/* Last events log */}
            {sseLog.length > 0 && (
              <div style={{
                marginTop: 10,
                maxHeight: 80,
                overflowY: 'auto',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--color-text-secondary)',
                background: 'var(--color-bg-primary)',
                padding: '6px 8px',
                borderRadius: 4,
                display: 'flex',
                flexDirection: 'column-reverse',
                gap: 2,
              }}>
                {[...sseLog].reverse().slice(0, 8).map((ev, i) => (
                  <div key={i}>
                    {ev.type === 'city_start' && `→ ${ev.city}`}
                    {ev.type === 'city_progress' && `✓ ${ev.city}: ${ev.leads_found} leads, ${ev.leads_with_email} emails`}
                    {ev.type === 'job_complete' && `✓ Concluído: ${ev.total_leads} leads`}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Jobs feed */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-display)', color: 'var(--color-text-primary)' }}>
            Histórico de Jobs
          </h3>
          <JobFeed jobs={jobs} loading={jobsLoading} onSelectJob={handleOpenJob} />
        </div>
      </div>

      {selectedJob && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 60,
          background: 'rgba(0,0,0,0.72)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
        }}>
          <div style={{
            width: 'min(1200px, 96vw)',
            height: 'min(80vh, 860px)',
            background: 'var(--color-bg-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}>
            <div style={{
              padding: '14px 18px',
              borderBottom: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                  Job #{selectedJob.id}
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
                  {selectedJob.query} · {jobLeads.length} leads ligados a esta extração
                </div>
              </div>
              <button
                onClick={() => { setSelectedJob(null); setJobLeads([]) }}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                  borderRadius: 6,
                  cursor: 'pointer',
                  padding: 6,
                  display: 'flex',
                }}
              >
                <X size={14} />
              </button>
            </div>

            <div style={{ flex: 1, overflow: 'auto' }}>
              {jobLeadsLoading ? (
                <div style={{ padding: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--color-text-secondary)', fontSize: 13 }}>
                  <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                  A carregar leads do job...
                </div>
              ) : (
                <DataGrid
                  leads={jobLeads}
                  onSelectLead={setDrawerLead}
                  selectedIds={new Set()}
                  onToggleSelect={() => {}}
                  onToggleAll={() => {}}
                  selectable={false}
                />
              )}
            </div>
          </div>
          <LeadDrawer lead={drawerLead} onClose={() => setDrawerLead(null)} />
        </div>
      )}
    </div>
  )
}

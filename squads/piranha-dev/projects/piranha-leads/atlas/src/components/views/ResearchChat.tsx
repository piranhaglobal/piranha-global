import { useEffect, useRef, useState, type CSSProperties } from 'react'
import {
  AlertCircle,
  CheckCircle,
  Clock3,
  Folder,
  Loader,
  Mic,
  Plus,
  Radio,
  Save,
  Send,
  Sparkles,
  Square,
  Trash2,
  Zap,
} from 'lucide-react'
import type { ChatExecution, ChatFolder, ChatMessage, ChatPlacesSnapshot, ChatThread, ResearchContext } from '../../types'
import {
  clearChatContext,
  createChatFolder,
  createChatThread,
  deleteChatFolder,
  deleteChatThread,
  fetchChatQueue,
  fetchChatFolders,
  fetchChatMessages,
  fetchChatPlacesInsights,
  fetchChatThreads,
  moveChatThread,
  renameChatThread,
  setChatThreadQueue,
  sendChatMessage,
  transcribeChatAudio,
  updateChatContext,
} from '../../services/chatService'
import type { ChatQueueItem } from '../../types'

const missingLabels: Record<string, string> = {
  category: 'Categoria',
  region_or_cities: 'Região ou cidades',
  leads_per_city: 'Leads por cidade',
  min_reviews: 'Reviews mínimas',
}

function FieldCard({ label, value, muted }: { label: string; value: string | number | null | undefined; muted?: boolean }) {
  return (
    <div style={{
      minHeight: 58,
      padding: '10px 12px',
      border: '1px solid var(--color-border)',
      background: muted ? 'rgba(255,255,255,0.015)' : 'var(--color-bg-surface)',
      borderRadius: 6,
    }}>
      <div style={{ color: 'var(--color-text-secondary)', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{
        color: value ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
        fontSize: 13,
        fontWeight: value ? 650 : 500,
        whiteSpace: 'normal',
        wordBreak: 'break-word',
        lineHeight: 1.45,
      }}>
        {value || '-'}
      </div>
    </div>
  )
}

function FormField({
  label,
  value,
  onChange,
  type = 'text',
  multiline = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'number'
  multiline?: boolean
}) {
  const baseStyle: CSSProperties = {
    width: '100%',
    background: 'var(--color-bg-surface)',
    border: '1px solid var(--color-border)',
    color: 'var(--color-text-primary)',
    borderRadius: 6,
    padding: '9px 10px',
    outline: 'none',
    fontSize: 12,
    lineHeight: 1.35,
  }
  return (
    <label style={{ display: 'grid', gap: 6 }}>
      <span style={{ color: 'var(--color-text-secondary)', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0 }}>{label}</span>
      {multiline ? (
        <textarea
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{ ...baseStyle, minHeight: 72, resize: 'vertical' }}
        />
      ) : (
        <input
          value={value}
          type={type}
          onChange={e => onChange(e.target.value)}
          style={baseStyle}
        />
      )}
    </label>
  )
}

function ExecutionNotice({ execution }: { execution: ChatExecution | null }) {
  if (!execution) return null
  if (execution.blocked_duplicate) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        border: '1px solid rgba(245,158,11,0.22)',
        background: 'rgba(245,158,11,0.08)',
        color: '#FBBF24',
        borderRadius: 6,
        padding: '10px 12px',
        fontSize: 12,
      }}>
        <AlertCircle size={15} />
        Pesquisa bloqueada porque já existe no histórico.
      </div>
    )
  }
  if (execution.job_id) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        border: '1px solid rgba(34,197,94,0.22)',
        background: 'rgba(34,197,94,0.08)',
        color: 'var(--color-success)',
        borderRadius: 6,
        padding: '10px 12px',
        fontSize: 12,
      }}>
        <CheckCircle size={15} />
        Job #{execution.job_id} criado no Scraper Control.
      </div>
    )
  }
  return null
}

function formatThreadDate(value: string) {
  try {
    return new Date(value).toLocaleString('pt-PT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function formatCountdown(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours <= 0) return `${minutes}m`
  return `${hours}h ${minutes}m`
}

export default function ResearchChat() {
  const [folders, setFolders] = useState<ChatFolder[]>([])
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [queueItems, setQueueItems] = useState<ChatQueueItem[]>([])
  const [queueEta, setQueueEta] = useState<number>(0)
  const [activeThread, setActiveThread] = useState<ChatThread | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [context, setContext] = useState<ResearchContext | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastExecution, setLastExecution] = useState<ChatExecution | null>(null)
  const [placesSnapshot, setPlacesSnapshot] = useState<ChatPlacesSnapshot | null>(null)
  const [contextDraft, setContextDraft] = useState({
    category: '',
    query: '',
    region: '',
    cities: '',
    leads_per_city: '',
    min_reviews: '',
    objective: '',
  })
  const recorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  async function loadThreads() {
    setLoading(true)
    setError(null)
    try {
      let data = await fetchChatThreads()
      const [folderData, queueData] = await Promise.all([
        fetchChatFolders().catch(() => []),
        fetchChatQueue().catch(() => ({ scheduled_for: '', seconds_until_run: 0, items: [] })),
      ])
      if (data.length === 0) {
        const created = await createChatThread()
        data = [created]
      }
      setFolders(folderData)
      setQueueItems(queueData.items)
      setQueueEta(queueData.seconds_until_run)
      setThreads(data)
      setActiveThread(prev => prev || data[0])
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  async function loadMessages(threadId: string) {
    try {
      const data = await fetchChatMessages(threadId)
      setMessages(data.messages)
      setContext(data.context)
      setPlacesSnapshot(null)
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => { loadThreads() }, [])

  useEffect(() => {
    if (activeThread) loadMessages(activeThread.id)
  }, [activeThread?.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    setPlacesSnapshot(null)
  }, [activeThread?.id])

  useEffect(() => {
    setContextDraft({
      category: context?.category || '',
      query: context?.query || '',
      region: context?.region || '',
      cities: context?.cities?.join('\n') || '',
      leads_per_city: context?.leads_per_city ? String(context.leads_per_city) : '',
      min_reviews: context?.min_reviews ? String(context.min_reviews) : '',
      objective: context?.objective || '',
    })
  }, [context?.updated_at, activeThread?.id])

  async function handleNewThread() {
    const thread = await createChatThread('Nova pesquisa', activeThread?.folder_id || 'default')
    setThreads(prev => [thread, ...prev])
    setActiveThread(thread)
    setMessages([])
    setContext(null)
    setLastExecution(null)
    setPlacesSnapshot(null)
  }

  async function handleNewFolder() {
    const name = window.prompt('Nome da pasta/segmento')
    if (!name?.trim()) return
    const folder = await createChatFolder(name.trim())
    setFolders(prev => [...prev, folder])
  }

  async function handleDeleteFolder(folder: ChatFolder) {
    if (folder.id === 'default') return
    const ok = window.confirm(`Apagar a pasta "${folder.name}"? Os chats regressam a "Geral".`)
    if (!ok) return
    await deleteChatFolder(folder.id)
    await loadThreads()
  }

  async function handleRenameThread(thread: ChatThread) {
    const title = window.prompt('Novo nome da conversa', thread.title)
    if (!title?.trim()) return
    const updated = await renameChatThread(thread.id, title.trim())
    setThreads(prev => prev.map(item => item.id === updated.id ? updated : item))
    if (activeThread?.id === updated.id) setActiveThread(updated)
    await loadThreads()
  }

  async function handleDeleteThread(thread: ChatThread) {
    const ok = window.confirm(`Apagar "${thread.title}" e limpar toda a memória/contexto desta conversa?`)
    if (!ok) return
    await deleteChatThread(thread.id)
    const remaining = threads.filter(item => item.id !== thread.id)
    setThreads(remaining)
    setActiveThread(remaining[0] || null)
    if (activeThread?.id === thread.id) {
      setMessages([])
      setContext(null)
      setLastExecution(null)
      setPlacesSnapshot(null)
    }
  }

  async function handleMoveActiveThread(folderId: string) {
    if (!activeThread) return
    const updated = await moveChatThread(activeThread.id, folderId)
    setActiveThread(updated)
    setThreads(prev => prev.map(thread => thread.id === updated.id ? updated : thread))
  }

  async function handleQueueToggle(threadId: string, enabled: boolean) {
    await setChatThreadQueue(threadId, enabled)
    await loadThreads()
  }

  async function handleSend() {
    if (!activeThread || sending || !input.trim()) return
    const content = input.trim()
    setInput('')
    setSending(true)
    setError(null)
    setLastExecution(null)
    try {
      const result = await sendChatMessage(activeThread.id, content)
      await Promise.all([loadMessages(activeThread.id), loadThreads()])
      setContext(result.context)
      setLastExecution(result.execution)
      setPlacesSnapshot(result.places_snapshot ?? null)
      if (result.execution?.job_id) {
        window.dispatchEvent(new CustomEvent('piranha:jobs-updated'))
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setSending(false)
    }
  }

  async function startRecording() {
    if (!activeThread || recording) return
    setError(null)
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('Não foi possível aceder ao microfone.')
      return
    }
    const recorder = new MediaRecorder(stream)
    audioChunksRef.current = []
    recorderRef.current = recorder
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunksRef.current.push(event.data)
    }
    recorder.onstop = async () => {
      stream.getTracks().forEach(track => track.stop())
      const audio = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      setTranscribing(true)
      try {
        const result = await transcribeChatAudio(activeThread.id, audio)
        setInput(prev => [prev.trim(), result.transcript.trim()].filter(Boolean).join('\n'))
      } catch (e) {
        setError(String(e))
      } finally {
        setTranscribing(false)
      }
    }
    recorder.start()
    setRecording(true)
  }

  function stopRecording() {
    recorderRef.current?.stop()
    recorderRef.current = null
    setRecording(false)
  }

  const missing = context?.missing_fields
    ? context.missing_fields.split(',').filter(Boolean)
    : []
  const complete = context?.completeness_status === 'complete'
  const cityCount = context?.cities?.length || 0
  const folderMap = new Map(folders.map(folder => [folder.id, folder]))
  const groupedFolders = folders.length > 0 ? folders : [{ id: 'default', name: 'Geral', created_at: '' }]

  async function handleSaveContext() {
    if (!activeThread) return
    const cities = contextDraft.cities
      .split(/[\n,]+/)
      .map(city => city.trim())
      .filter(Boolean)
    const updated = await updateChatContext(activeThread.id, {
      category: contextDraft.category.trim() || null,
      query: contextDraft.query.trim() || null,
      region: contextDraft.region.trim() || null,
      cities,
      leads_per_city: contextDraft.leads_per_city ? Number(contextDraft.leads_per_city) : null,
      min_reviews: contextDraft.min_reviews ? Number(contextDraft.min_reviews) : null,
      objective: contextDraft.objective.trim() || null,
    })
    setContext(updated)
  }

  async function handleClearContext() {
    if (!activeThread) return
    const ok = window.confirm('Limpar o contexto extraído desta conversa?')
    if (!ok) return
    await clearChatContext(activeThread.id)
    setContext(null)
    setPlacesSnapshot(null)
    setContextDraft({
      category: '',
      query: '',
      region: '',
      cities: '',
      leads_per_city: '',
      min_reviews: '',
      objective: '',
    })
  }

  async function handleGeneratePlacesSnapshot() {
    if (!activeThread || sending) return
    setError(null)
    try {
      const snapshot = await fetchChatPlacesInsights(activeThread.id, input.trim() || context?.query || activeThread.title)
      setPlacesSnapshot(snapshot)
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div style={{ height: '100%', minHeight: 0, display: 'flex', overflow: 'hidden', background: 'var(--color-bg-primary)' }}>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulseDot { 0%, 100% { opacity: .45; transform: scale(.85); } 50% { opacity: 1; transform: scale(1); } }
      `}</style>

      <aside style={{
        width: 292,
        borderRight: '1px solid var(--color-border)',
        background: 'linear-gradient(180deg, #191A1D 0%, #121315 100%)',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ padding: 16, borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 14, color: 'var(--color-text-primary)', fontFamily: 'var(--font-display)' }}>Research Chat</h3>
              <div style={{ marginTop: 4, color: 'var(--color-text-secondary)', fontSize: 11 }}>
                {threads.length} threads
              </div>
            </div>
            <button
              onClick={handleNewFolder}
              title="Nova pasta"
              style={{
                width: 32,
                height: 32,
                borderRadius: 6,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg-surface)',
                color: 'var(--color-text-primary)',
                display: 'grid',
                placeItems: 'center',
                cursor: 'pointer',
              }}
            >
              <Folder size={15} />
            </button>
          </div>
          <button
            onClick={handleNewThread}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              color: 'var(--color-text-primary)',
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 6,
              padding: '8px 10px',
              cursor: 'pointer',
              marginBottom: 10,
              fontSize: 12,
              fontWeight: 650,
            }}
          >
            <Plus size={14} />
            Nova conversa
          </button>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            color: complete ? 'var(--color-success)' : 'var(--color-text-secondary)',
            fontSize: 12,
            padding: '8px 10px',
            borderRadius: 6,
            background: complete ? 'rgba(34,197,94,0.08)' : 'rgba(255,255,255,0.025)',
            border: `1px solid ${complete ? 'rgba(34,197,94,0.22)' : 'var(--color-border)'}`,
          }}>
            {complete ? <Zap size={14} /> : <Clock3 size={14} />}
            {complete ? 'Pronto para execução' : 'A aguardar filtros'}
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
          {queueItems.length > 0 && (
            <div style={{
              marginBottom: 14,
              border: '1px solid rgba(34,197,94,0.16)',
              background: 'rgba(34,197,94,0.06)',
              borderRadius: 8,
              padding: 10,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 12, fontWeight: 700 }}>
                  Fila pronta
                </div>
                <div style={{ color: 'var(--color-text-secondary)', fontSize: 11 }}>
                  {formatCountdown(queueEta)}
                </div>
              </div>
              <div style={{ display: 'grid', gap: 8 }}>
                {queueItems.slice(0, 4).map(item => (
                  <div
                    key={item.thread_id}
                    style={{
                      border: '1px solid var(--color-border)',
                      background: 'rgba(0,0,0,0.18)',
                      borderRadius: 7,
                      padding: 10,
                    }}
                  >
                    <button
                      onClick={() => {
                        const thread = threads.find(entry => entry.id === item.thread_id)
                        if (thread) setActiveThread(thread)
                      }}
                      style={{
                        width: '100%',
                        background: 'transparent',
                        border: 'none',
                        color: 'inherit',
                        textAlign: 'left',
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      <div style={{ color: 'var(--color-text-primary)', fontSize: 12, fontWeight: 700 }}>
                        {item.title}
                      </div>
                      <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginTop: 4, lineHeight: 1.45 }}>
                        {item.query} · {item.cities?.length || 0} cidades · +{item.min_reviews || 0} reviews
                      </div>
                    </button>
                    <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                      <button
                        onClick={() => handleQueueToggle(item.thread_id, item.queue_status !== 'scheduled')}
                        style={{
                          flex: 1,
                          height: 28,
                          borderRadius: 6,
                          border: '1px solid var(--color-border)',
                          background: 'var(--color-bg-surface)',
                          color: 'var(--color-text-primary)',
                          fontSize: 11,
                          cursor: 'pointer',
                        }}
                      >
                        {item.queue_status === 'scheduled' ? 'Pausar' : 'Manter na fila'}
                      </button>
                      <button
                        onClick={() => handleDeleteThread({ id: item.thread_id, title: item.title } as ChatThread)}
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 6,
                          border: '1px solid rgba(239,68,68,0.24)',
                          background: 'rgba(239,68,68,0.10)',
                          color: '#FCA5A5',
                          cursor: 'pointer',
                        }}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, padding: 12 }}>A carregar threads...</div>
          ) : groupedFolders.map(folder => {
            const folderThreads = threads.filter(thread => (thread.folder_id || 'default') === folder.id)
            if (folderThreads.length === 0 && folder.id !== 'default') return null
            return (
              <div key={folder.id} style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 7, color: 'var(--color-text-secondary)', fontSize: 11, fontWeight: 700, padding: '5px 6px 8px' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <Folder size={12} />
                    {folder.name}
                  </span>
                  {folder.id !== 'default' && (
                    <button
                      onClick={() => handleDeleteFolder(folder)}
                      title="Apagar pasta"
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: 5,
                        border: '1px solid transparent',
                        background: 'transparent',
                        color: 'var(--color-text-secondary)',
                        display: 'grid',
                        placeItems: 'center',
                        cursor: 'pointer',
                      }}
                    >
                      <Trash2 size={11} />
                    </button>
                  )}
                </div>
                {folderThreads.map(thread => {
                  const selected = activeThread?.id === thread.id
                  return (
                    <div key={thread.id} style={{ position: 'relative', marginBottom: 7 }}>
                      <button
                        onClick={() => { setActiveThread(thread); setLastExecution(null) }}
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          padding: '12px 36px 12px 12px',
                          borderRadius: 7,
                          border: `1px solid ${selected ? 'rgba(225,29,46,0.38)' : 'transparent'}`,
                          background: selected ? 'linear-gradient(135deg, rgba(225,29,46,0.12), rgba(255,255,255,0.03))' : 'transparent',
                          color: 'var(--color-text-primary)',
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
                          <div style={{
                            width: 7,
                            height: 7,
                            borderRadius: 999,
                            background: selected ? 'var(--color-accent)' : 'var(--color-border-subtle)',
                          }} />
                          <div style={{ fontSize: 13, fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{thread.title}</div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)', fontSize: 11 }}>
                          <span>#{thread.id}</span>
                          <span>{formatThreadDate(thread.updated_at)}</span>
                        </div>
                      </button>
                      <button
                        onClick={() => handleRenameThread(thread)}
                        title="Renomear conversa"
                        style={{
                          position: 'absolute',
                          top: 9,
                          right: 36,
                          width: 26,
                          height: 26,
                          borderRadius: 5,
                          border: '1px solid transparent',
                          background: 'transparent',
                          color: 'var(--color-text-secondary)',
                          display: 'grid',
                          placeItems: 'center',
                          cursor: 'pointer',
                          fontSize: 10,
                          fontWeight: 700,
                        }}
                      >
                        R
                      </button>
                      <button
                        onClick={() => handleDeleteThread(thread)}
                        title="Apagar conversa"
                        style={{
                          position: 'absolute',
                          top: 9,
                          right: 8,
                          width: 26,
                          height: 26,
                          borderRadius: 5,
                          border: '1px solid transparent',
                          background: 'transparent',
                          color: 'var(--color-text-secondary)',
                          display: 'grid',
                          placeItems: 'center',
                          cursor: 'pointer',
                        }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </aside>

      <main style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <header style={{
          height: 68,
          padding: '12px 20px',
          borderBottom: '1px solid var(--color-border)',
          background: 'rgba(11,11,12,0.92)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ color: 'var(--color-text-primary)', fontSize: 15, fontWeight: 750, fontFamily: 'var(--font-display)' }}>
              {activeThread?.title || 'Research Chat'}
            </div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 11, marginTop: 4 }}>
              Chat: gpt-4o-mini · Planner: GPT-5.5 · Voz: gpt-4o-mini-transcribe
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, flexDirection: 'column' }}>
            <button
              onClick={handleGeneratePlacesSnapshot}
              disabled={!activeThread}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                color: 'var(--color-text-primary)',
                fontSize: 12,
                border: '1px solid rgba(59,130,246,0.24)',
                background: 'rgba(59,130,246,0.08)',
                padding: '7px 10px',
                borderRadius: 6,
                cursor: activeThread ? 'pointer' : 'not-allowed',
              }}
            >
              <Sparkles size={14} />
              Insights Maps
            </button>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              color: complete ? 'var(--color-success)' : '#FBBF24',
              fontSize: 12,
              border: `1px solid ${complete ? 'rgba(34,197,94,0.24)' : 'rgba(245,158,11,0.24)'}`,
              background: complete ? 'rgba(34,197,94,0.08)' : 'rgba(245,158,11,0.08)',
              padding: '8px 10px',
              borderRadius: 6,
              whiteSpace: 'nowrap',
            }}>
              {complete ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
              {complete ? 'Briefing completo' : `${missing.length || 4} filtros pendentes`}
            </div>
          </div>
        </header>

        <section style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '22px 28px' }}>
          <div style={{ width: 'min(920px, 100%)', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {messages.length === 0 && (
              <div style={{
                border: '1px solid var(--color-border)',
                background: 'linear-gradient(135deg, rgba(225,29,46,0.08), rgba(255,255,255,0.025))',
                borderRadius: 8,
                padding: 18,
                color: 'var(--color-text-secondary)',
                fontSize: 13,
                lineHeight: 1.6,
              }}>
                <div style={{ color: 'var(--color-text-primary)', fontSize: 14, fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Sparkles size={16} />
                  Briefing de pesquisa
                </div>
                Descreve a categoria, região, quantidade por cidade e mínimo de reviews. Se o contexto ficar completo, o Atlas cria o job automaticamente e evita pesquisas duplicadas pelo histórico.
              </div>
            )}

            {placesSnapshot && (
              <div style={{
                border: '1px solid rgba(59,130,246,0.24)',
                background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(255,255,255,0.02))',
                borderRadius: 8,
                padding: 16,
                color: 'var(--color-text-primary)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 750, marginBottom: 8 }}>
                  <Sparkles size={16} />
                  Snapshot Google Places
                </div>
                <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
                  {placesSnapshot.summary}
                </div>
                {placesSnapshot.top_cities?.length ? (
                  <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
                    {placesSnapshot.top_cities.slice(0, 3).map(row => (
                      <div key={row.city} style={{
                        border: '1px solid var(--color-border)',
                        background: 'rgba(0,0,0,0.18)',
                        borderRadius: 7,
                        padding: 12,
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, fontWeight: 700 }}>
                          <span>{row.city}</span>
                          <span style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>
                            {row.qualified_count} leads com filtro
                          </span>
                        </div>
                        {row.best_businesses?.length > 0 && (
                          <div style={{ marginTop: 8, color: 'var(--color-text-secondary)', fontSize: 12, lineHeight: 1.5 }}>
                            {row.best_businesses.map(business => business.name).filter(Boolean).slice(0, 3).join(' • ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}

            {messages.map(message => {
              const isUser = message.role === 'user'
              return (
                <div key={message.id} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
                  <div style={{
                    maxWidth: isUser ? '72%' : '78%',
                    minWidth: isUser ? 0 : 260,
                    padding: '12px 14px',
                    borderRadius: isUser ? '8px 8px 2px 8px' : '8px 8px 8px 2px',
                    background: isUser ? 'linear-gradient(135deg, rgba(225,29,46,0.20), rgba(127,22,34,0.18))' : 'var(--color-bg-surface)',
                    border: `1px solid ${isUser ? 'rgba(225,29,46,0.28)' : 'var(--color-border)'}`,
                    color: 'var(--color-text-primary)',
                    fontSize: 13,
                    lineHeight: 1.55,
                    whiteSpace: 'pre-wrap',
                    boxShadow: '0 10px 30px rgba(0,0,0,0.16)',
                  }}>
                    {message.content}
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, color: 'var(--color-text-secondary)', fontSize: 10, marginTop: 8 }}>
                      <span>{message.model || (isUser ? 'user' : 'atlas')}</span>
                      <span>{formatThreadDate(message.created_at)}</span>
                    </div>
                  </div>
                </div>
              )
            })}
            <ExecutionNotice execution={lastExecution} />
            <div ref={messagesEndRef} />
          </div>
        </section>

        <footer style={{
          flexShrink: 0,
          borderTop: '1px solid var(--color-border)',
          background: 'linear-gradient(180deg, rgba(11,11,12,0.78), #0B0B0C)',
          padding: '14px 20px 18px',
        }}>
          <div style={{ width: 'min(980px, 100%)', margin: '0 auto' }}>
            {error && (
              <div style={{ color: '#F87171', fontSize: 12, marginBottom: 10 }}>{error}</div>
            )}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '42px minmax(0, 1fr) 46px',
              gap: 10,
              alignItems: 'end',
              border: '1px solid var(--color-border)',
              background: 'var(--color-bg-secondary)',
              borderRadius: 8,
              padding: 10,
              boxShadow: '0 18px 55px rgba(0,0,0,0.28)',
            }}>
              <button
                onClick={recording ? stopRecording : startRecording}
                disabled={sending || transcribing || !activeThread}
                title={recording ? 'Parar gravação' : transcribing ? 'A transcrever áudio' : 'Gravar áudio'}
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: 6,
                  border: `1px solid ${recording ? 'rgba(225,29,46,0.55)' : 'var(--color-border)'}`,
                  background: recording ? 'rgba(225,29,46,0.16)' : 'var(--color-bg-surface)',
                  color: recording ? 'var(--color-accent)' : 'var(--color-text-primary)',
                  display: 'grid',
                  placeItems: 'center',
                  cursor: sending || transcribing ? 'not-allowed' : 'pointer',
                  position: 'relative',
                }}
              >
                {recording && <span style={{ position: 'absolute', top: 6, right: 6, width: 6, height: 6, borderRadius: 999, background: 'var(--color-accent)', animation: 'pulseDot 1.1s ease-in-out infinite' }} />}
                {transcribing ? <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} /> : recording ? <Square size={16} /> : <Mic size={16} />}
              </button>

              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                disabled={sending || !activeThread}
                placeholder="Ex.: Quero 10 studios de tattoo por cidade em Espanha com +200 reviews..."
                style={{
                  width: '100%',
                  minHeight: 42,
                  maxHeight: 126,
                  resize: 'vertical',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--color-text-primary)',
                  padding: '10px 4px',
                  outline: 'none',
                  fontSize: 13,
                  lineHeight: 1.45,
                }}
              />

              <button
                onClick={handleSend}
                disabled={sending || !input.trim()}
                title="Enviar"
                style={{
                  width: 46,
                  height: 42,
                  borderRadius: 6,
                  border: '1px solid rgba(225,29,46,0.34)',
                  background: 'var(--color-accent)',
                  color: 'white',
                  display: 'grid',
                  placeItems: 'center',
                  cursor: sending || !input.trim() ? 'not-allowed' : 'pointer',
                  opacity: sending || !input.trim() ? 0.5 : 1,
                }}
              >
                {sending ? <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={16} />}
              </button>
            </div>
          </div>
        </footer>
      </main>

      <aside style={{
        width: 330,
        borderLeft: '1px solid var(--color-border)',
        background: 'linear-gradient(180deg, #17181B 0%, #101113 100%)',
        padding: 16,
        overflowY: 'auto',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ margin: 0, fontSize: 14, color: 'var(--color-text-primary)', fontFamily: 'var(--font-display)' }}>Contexto</h3>
          <span style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            color: complete ? 'var(--color-success)' : '#FBBF24',
            fontSize: 11,
          }}>
            {complete ? <CheckCircle size={13} /> : <AlertCircle size={13} />}
            {complete ? 'Completo' : 'Incompleto'}
          </span>
        </div>

        <div style={{
          border: '1px solid var(--color-border)',
          background: 'rgba(255,255,255,0.025)',
          borderRadius: 7,
          padding: 12,
          marginBottom: 12,
          display: 'grid',
          gap: 8,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-secondary)', fontSize: 11, fontWeight: 700 }}>
            <Folder size={13} />
            Segmento da conversa
          </div>
          <select
            value={activeThread?.folder_id || 'default'}
            onChange={e => handleMoveActiveThread(e.target.value)}
            disabled={!activeThread}
            style={{
              width: '100%',
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)',
              borderRadius: 6,
              padding: '9px 10px',
              outline: 'none',
              fontSize: 12,
            }}
          >
            {groupedFolders.map(folder => (
              <option key={folder.id} value={folder.id}>{folderMap.get(folder.id)?.name || folder.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <FieldCard label="Categoria" value={context?.category} />
          <FieldCard label="Reviews" value={context?.min_reviews ? `+${context.min_reviews}` : null} />
          <FieldCard label="Leads/cidade" value={context?.leads_per_city} />
          <FieldCard label="Cidades" value={cityCount ? `${cityCount}` : null} />
        </div>

        <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
          <FieldCard label="Query" value={context?.query} />
          <FieldCard label="Região" value={context?.region} />
          <FieldCard label="Objetivo" value={context?.objective} muted />
        </div>

        {missing.length > 0 && (
          <div style={{
            marginTop: 14,
            border: '1px solid rgba(245,158,11,0.22)',
            background: 'rgba(245,158,11,0.07)',
            borderRadius: 7,
            padding: 12,
          }}>
            <div style={{ color: '#FBBF24', fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Filtros em falta</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {missing.map(field => (
                <span key={field} style={{
                  color: '#FCD34D',
                  border: '1px solid rgba(245,158,11,0.22)',
                  background: 'rgba(0,0,0,0.16)',
                  borderRadius: 999,
                  padding: '4px 8px',
                  fontSize: 11,
                }}>
                  {missingLabels[field] || field}
                </span>
              ))}
            </div>
          </div>
        )}

        <div style={{
          marginTop: 14,
          border: '1px solid var(--color-border)',
          background: 'rgba(255,255,255,0.018)',
          borderRadius: 7,
          padding: 12,
        }}>
          <div style={{ color: 'var(--color-text-primary)', fontSize: 13, fontWeight: 750, marginBottom: 10 }}>
            Editar contexto manualmente
          </div>
          <div style={{ display: 'grid', gap: 10 }}>
            <FormField label="Categoria" value={contextDraft.category} onChange={value => setContextDraft(prev => ({ ...prev, category: value }))} />
            <FormField label="Query" value={contextDraft.query} onChange={value => setContextDraft(prev => ({ ...prev, query: value }))} />
            <FormField label="Região" value={contextDraft.region} onChange={value => setContextDraft(prev => ({ ...prev, region: value }))} />
            <FormField label="Cidades" value={contextDraft.cities} onChange={value => setContextDraft(prev => ({ ...prev, cities: value }))} multiline />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <FormField label="Leads/cidade" type="number" value={contextDraft.leads_per_city} onChange={value => setContextDraft(prev => ({ ...prev, leads_per_city: value }))} />
              <FormField label="Reviews mín." type="number" value={contextDraft.min_reviews} onChange={value => setContextDraft(prev => ({ ...prev, min_reviews: value }))} />
            </div>
            <FormField label="Objetivo" value={contextDraft.objective} onChange={value => setContextDraft(prev => ({ ...prev, objective: value }))} multiline />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12 }}>
            <button
              onClick={handleSaveContext}
              disabled={!activeThread}
              style={{
                height: 36,
                borderRadius: 6,
                border: '1px solid rgba(34,197,94,0.25)',
                background: 'rgba(34,197,94,0.10)',
                color: 'var(--color-success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 7,
                fontSize: 12,
                fontWeight: 700,
                cursor: activeThread ? 'pointer' : 'not-allowed',
              }}
            >
              <Save size={14} />
              Guardar
            </button>
            <button
              onClick={handleClearContext}
              disabled={!activeThread}
              style={{
                height: 36,
                borderRadius: 6,
                border: '1px solid rgba(239,68,68,0.24)',
                background: 'rgba(239,68,68,0.09)',
                color: '#FCA5A5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 7,
                fontSize: 12,
                fontWeight: 700,
                cursor: activeThread ? 'pointer' : 'not-allowed',
              }}
            >
              <Trash2 size={14} />
              Limpar
            </button>
          </div>
        </div>

        {complete && (
          <div style={{
            marginTop: 14,
            border: '1px solid rgba(34,197,94,0.22)',
            background: 'rgba(34,197,94,0.07)',
            borderRadius: 7,
            padding: 12,
            color: 'var(--color-success)',
            fontSize: 12,
            lineHeight: 1.5,
          }}>
            O próximo envio completo cria um job no Scraper Control e grava a deduplicação no histórico.
          </div>
        )}

        {lastExecution?.job_id && (
          <div style={{ marginTop: 14, padding: 12, borderRadius: 7, border: '1px solid rgba(34,197,94,0.25)', background: 'rgba(34,197,94,0.08)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-success)', fontSize: 13, fontWeight: 700 }}>
              <Radio size={15} /> Job criado
            </div>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: 12, marginTop: 6 }}>#{lastExecution.job_id}</div>
          </div>
        )}
      </aside>
    </div>
  )
}

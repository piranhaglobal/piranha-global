import type { ChatFolder, ChatMessage, ChatPlacesSnapshot, ChatSendResponse, ChatThread, ResearchContext } from '../types'

export async function fetchChatThreads(): Promise<ChatThread[]> {
  const res = await fetch('/api/chat/threads')
  if (!res.ok) throw new Error('Failed to fetch chat threads')
  return res.json()
}

export async function createChatThread(title = 'Nova pesquisa', folderId?: string | null): Promise<ChatThread> {
  const res = await fetch('/api/chat/threads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, folder_id: folderId }),
  })
  if (!res.ok) throw new Error('Failed to create chat thread')
  return res.json()
}

export async function deleteChatThread(threadId: string): Promise<void> {
  const res = await fetch(`/api/chat/threads/${threadId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete chat thread')
}

export async function moveChatThread(threadId: string, folderId: string | null): Promise<ChatThread> {
  const res = await fetch(`/api/chat/threads/${threadId}/folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder_id: folderId }),
  })
  if (!res.ok) throw new Error('Failed to move chat thread')
  return res.json()
}

export async function fetchChatFolders(): Promise<ChatFolder[]> {
  const res = await fetch('/api/chat/folders')
  if (!res.ok) throw new Error('Failed to fetch chat folders')
  return res.json()
}

export async function createChatFolder(name: string): Promise<ChatFolder> {
  const res = await fetch('/api/chat/folders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error('Failed to create chat folder')
  return res.json()
}

export async function fetchChatMessages(threadId: string): Promise<{ messages: ChatMessage[]; context: ResearchContext | null }> {
  const res = await fetch(`/api/chat/threads/${threadId}/messages`)
  if (!res.ok) throw new Error('Failed to fetch chat messages')
  return res.json()
}

export async function sendChatMessage(threadId: string, content: string): Promise<ChatSendResponse> {
  const res = await fetch(`/api/chat/threads/${threadId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error('Failed to send chat message')
  return res.json()
}

export async function sendChatAudio(threadId: string, audio: Blob): Promise<ChatSendResponse> {
  const form = new FormData()
  form.append('file', audio, 'atlas-voice.webm')
  const res = await fetch(`/api/chat/threads/${threadId}/audio`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to send audio')
  }
  return res.json()
}

export async function transcribeChatAudio(threadId: string, audio: Blob): Promise<{ transcript: string }> {
  const form = new FormData()
  form.append('file', audio, 'atlas-voice.webm')
  const res = await fetch(`/api/chat/threads/${threadId}/transcribe`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error('Failed to transcribe audio')
  return res.json()
}

export async function updateChatContext(threadId: string, context: Partial<ResearchContext>): Promise<ResearchContext> {
  const res = await fetch(`/api/chat/threads/${threadId}/context`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category: context.category || null,
      region: context.region || null,
      cities: context.cities || [],
      leads_per_city: context.leads_per_city || null,
      min_reviews: context.min_reviews || null,
      query: context.query || null,
      objective: context.objective || null,
    }),
  })
  if (!res.ok) throw new Error('Failed to update context')
  return res.json()
}

export async function clearChatContext(threadId: string): Promise<void> {
  const res = await fetch(`/api/chat/threads/${threadId}/context`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to clear context')
}

export async function fetchChatPlacesInsights(threadId: string, prompt?: string): Promise<ChatPlacesSnapshot | null> {
  const res = await fetch(`/api/chat/threads/${threadId}/places-insights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: prompt || null }),
  })
  if (!res.ok) throw new Error('Failed to generate places insights')
  const data = await res.json()
  return data.snapshot ?? null
}

import type { KlaviyoList, KlaviyoSyncResult, Lead, ScraperJob, StatusResponse } from '../types'

export async function triggerKlaviyoSync(): Promise<KlaviyoSyncResult> {
  const res = await fetch('/api/klaviyo/sync', { method: 'POST' })
  if (!res.ok) throw new Error('Sync failed')
  return res.json()
}

export async function triggerSelectedKlaviyoSync(ids: number[], listId: string): Promise<KlaviyoSyncResult> {
  const res = await fetch('/api/klaviyo/sync-selected', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, list_id: listId }),
  })
  if (!res.ok) throw new Error('Selected sync failed')
  return res.json()
}

export async function fetchJobs(): Promise<ScraperJob[]> {
  const res = await fetch('/api/jobs')
  if (!res.ok) throw new Error('Failed to fetch jobs')
  return res.json()
}

export async function fetchJobLeads(jobId: string): Promise<Lead[]> {
  const res = await fetch(`/api/jobs/${jobId}/leads`)
  if (!res.ok) throw new Error('Failed to fetch job leads')
  return res.json()
}

export async function startJob(payload: {
  query: string
  cities: string[]
  enrich_email: boolean
  use_firecrawl: boolean
  validate_and_enrich: boolean
  auto_klaviyo: boolean
}): Promise<{ job_id: string }> {
  const res = await fetch('/api/jobs/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error('Failed to start job')
  return res.json()
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch('/api/status')
  if (!res.ok) throw new Error('Failed to fetch status')
  return res.json()
}

export async function fetchKlaviyoLists(): Promise<{ lists: KlaviyoList[]; default_list_id: string }> {
  const res = await fetch('/api/klaviyo/lists')
  if (!res.ok) throw new Error('Failed to fetch Klaviyo lists')
  return res.json()
}

export async function addKlaviyoList(listId: string): Promise<{ lists: KlaviyoList[]; added: KlaviyoList }> {
  const res = await fetch('/api/klaviyo/lists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ list_id: listId }),
  })
  if (!res.ok) throw new Error('Failed to add Klaviyo list')
  return res.json()
}

export async function removeKlaviyoList(listId: string): Promise<{ lists: KlaviyoList[]; removed: string }> {
  const res = await fetch(`/api/klaviyo/lists/${listId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to remove Klaviyo list')
  return res.json()
}

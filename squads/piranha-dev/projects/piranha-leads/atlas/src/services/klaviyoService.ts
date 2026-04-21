import type { KlaviyoSyncResult, ScraperJob, StatusResponse } from '../types'

export async function triggerKlaviyoSync(): Promise<KlaviyoSyncResult> {
  const res = await fetch('/api/klaviyo/sync', { method: 'POST' })
  if (!res.ok) throw new Error('Sync failed')
  return res.json()
}

export async function fetchJobs(): Promise<ScraperJob[]> {
  const res = await fetch('/api/jobs')
  if (!res.ok) throw new Error('Failed to fetch jobs')
  return res.json()
}

export async function startJob(payload: {
  query: string
  cities: string[]
  enrich_email: boolean
  use_firecrawl: boolean
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

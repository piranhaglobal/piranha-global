import type { Lead } from '../types'

export async function fetchLeads(): Promise<Lead[]> {
  const res = await fetch('/api/leads')
  if (!res.ok) throw new Error('Failed to fetch leads')
  return res.json()
}

export async function fetchLead(id: number): Promise<Lead> {
  const res = await fetch(`/api/leads/${id}`)
  if (!res.ok) throw new Error('Lead not found')
  return res.json()
}

export async function startValidation(ids: number[], autoKlaviyo: boolean): Promise<string> {
  const res = await fetch('/api/leads/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, auto_klaviyo: autoKlaviyo }),
  })
  if (!res.ok) throw new Error('Failed to start validation')
  const data = await res.json()
  return data.validation_id
}

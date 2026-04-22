export interface Lead {
  id: number
  place_id: string
  job_id: string | null
  name: string
  city: string
  address: string | null
  phone: string | null
  website: string | null
  email: string | null
  instagram_url: string | null
  facebook_url: string | null
  rating: number | null
  total_reviews: number | null
  business_status: 'OPERATIONAL' | 'CLOSED_TEMPORARILY' | 'CLOSED_PERMANENTLY'
  source: 'google_places' | 'paginasamarillas'
  status: string
  klaviyo_synced: 0 | 1
  validated_at: string | null
  created_at: string
}

export interface ScraperJob {
  id: string
  query: string
  cities: string
  status: 'running' | 'completed' | 'failed'
  leads_found: number
  leads_with_email: number
  klaviyo_synced: number
  started_at: string
  finished_at: string | null
  duration_seconds: number | null
  error: string | null
}

export interface SSEEvent {
  type: 'city_start' | 'city_progress' | 'klaviyo_start' | 'job_complete' | 'ping' | '__done__'
  city?: string
  city_index?: number
  total_cities?: number
  leads_found?: number
  leads_with_email?: number
  total_leads?: number
  klaviyo_synced?: number
  validated_count?: number
  enriched_count?: number
  error?: string
}

export interface KlaviyoSyncResult {
  synced: number
  skipped: number
  jobs: Array<{ job_id: string; size: number; status: string }>
}

export interface KlaviyoList {
  id: string
  name: string
  source?: string
  created?: string | null
  updated?: string | null
}

export interface StatusResponse {
  google_places: { configured: boolean; key_preview: string }
  klaviyo: { configured: boolean; list_id: string; lists: KlaviyoList[] }
  firecrawl: { online: boolean; url: string }
  serper: { configured: boolean; key_preview: string }
}

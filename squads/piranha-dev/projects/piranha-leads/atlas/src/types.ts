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

export interface ResearchContext {
  thread_id: string
  category: string | null
  region: string | null
  region_band_id: string | null
  cities: string[]
  leads_per_city: number | null
  min_reviews: number | null
  query: string | null
  objective: string | null
  klaviyo_list_id: string | null
  completeness_status: 'complete' | 'incomplete'
  missing_fields: string
  updated_at: string
}

export interface ChatThread {
  id: string
  folder_id: string | null
  title: string
  status: string
  usable_for_cron: 0 | 1
  created_at: string
  updated_at: string
}

export interface ChatFolder {
  id: string
  name: string
  created_at: string
}

export interface ChatQueueItem extends ResearchContext {
  title: string
  folder_id: string | null
  usable_for_cron: 0 | 1
  queue_status: 'scheduled' | 'paused' | 'already_done'
  scheduled_for: string
  seconds_until_run: number
}

export interface ChatMessage {
  id: string
  thread_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  audio_path: string | null
  transcript: string | null
  model: string | null
  created_at: string
}

export interface ChatExecution {
  job_id?: string
  blocked_duplicate?: boolean
  existing_log?: { id: string; job_id: string | null; status: string; created_at: string }
}

export interface ChatPlacesBusiness {
  name: string | null
  reviews: number
  address: string | null
}

export interface ChatPlacesCityInsight {
  city: string
  qualified_count: number
  best_reviews: number
  best_businesses: ChatPlacesBusiness[]
  sampled: number
  score: number
  error?: string
}

export interface ChatPlacesSnapshot {
  available: boolean
  reason?: string
  country?: string
  query?: string
  min_reviews?: number
  cities_tested?: number
  top_cities?: ChatPlacesCityInsight[]
  summary?: string
  generated_at?: string
}

export interface ChatSendResponse {
  message: ChatMessage
  user_message?: ChatMessage
  transcript?: string
  context: ResearchContext
  context_complete: boolean
  can_execute_scrape: boolean
  execution: ChatExecution | null
  places_snapshot?: ChatPlacesSnapshot | null
}

'use server'

import { createClient } from '@/utils/supabase/server'

export interface BusinessSummary {
  id: number
  name: string
  industry: string
  description: string
  website_url: string | null
  logo: string | null
  primary_color: string | null
  created_at: string
  updated_at: string
}

export interface ProcessingStatus {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message: string
  business: BusinessSummary | null
}

const API_URL = () => process.env.NEXT_PUBLIC_API_URL

async function authHeaders() {
  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('Not authenticated')
  }

  return { Authorization: `Bearer ${session.access_token}` }
}

async function readError(response: Response, fallback: string) {
  const data = await response.json().catch(() => null)
  return new Error(data?.message || data?.error || data?.detail || fallback)
}

export async function getBusinesses() {
  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/business/`, {
    headers,
    cache: 'no-store',
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch your businesses')
  }

  return response.json() as Promise<BusinessSummary[]>
}

export async function createBusiness(formData: FormData) {
  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/business/process/`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to start onboarding')
  }

  return response.json() as Promise<{
    status: string
    message: string
    request_id: string
  }>
}

export async function getBusinessProcessingStatus(requestId: string) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/process/status/${requestId}/`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch the onboarding status')
  }

  return response.json() as Promise<ProcessingStatus>
}

'use server'

import { createClient } from '@/utils/supabase/server'

export interface KnowledgeBaseEntry {
  id: number
  name: string
  content: string
  created_at: string
  updated_at: string
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
  return new Error(data?.error || data?.detail || fallback)
}

export async function getKnowledgeBase(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/knowledge-base/${businessId}/`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch the knowledge base')
  }

  return response.json() as Promise<KnowledgeBaseEntry[]>
}

export async function addKnowledgeBaseEntry(
  businessId: number,
  name: string,
  content: string
) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/knowledge-base/${businessId}/add/`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, content }),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to add the entry')
  }

  return response.json() as Promise<KnowledgeBaseEntry>
}

export async function editKnowledgeBaseEntry(
  businessId: number,
  entryId: number,
  name: string,
  content: string
) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/knowledge-base/${businessId}/edit/${entryId}/`,
    {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, content }),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to update the entry')
  }

  return response.json() as Promise<KnowledgeBaseEntry>
}

export async function deleteKnowledgeBaseEntry(businessId: number, entryId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/knowledge-base/${businessId}/delete/${entryId}/`,
    { method: 'DELETE', headers }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to delete the entry')
  }
}

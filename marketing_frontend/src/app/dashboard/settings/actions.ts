'use server'

import { createClient } from '@/utils/supabase/server'

export interface Business {
  id: number
  name: string
  industry: string
  description: string
  website_url: string
  logo: string | null
  phone: string
  primary_color: string
  twitter_url: string
  facebook_url: string
  instagram_url: string
  linkedin_url: string
  knowledge_base_summary: string
  created_at: string
  updated_at: string
}

export interface SystemPrompts {
  id?: number
  social_media_system_prompt: string
  research_system_prompt: string
}

export interface TeamMember {
  id: number
  business: number
  role: string
  user: { id: number; email: string; name: string }
  created_at: string
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

export async function getBusiness(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/business/${businessId}/`, {
    headers,
    cache: 'no-store',
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch the business')
  }

  return response.json() as Promise<Business>
}

export async function updateBusiness(
  businessId: number,
  data: Partial<
    Pick<
      Business,
      'name' | 'industry' | 'description' | 'website_url' | 'phone' | 'primary_color'
    >
  >
) {
  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/business/${businessId}/update/`, {
    method: 'PUT',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to update the business')
  }

  return response.json()
}

export async function uploadLogo(businessId: number, formData: FormData) {
  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/business/${businessId}/logo/`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to upload the logo')
  }

  return response.json() as Promise<{ logo_url: string }>
}

export async function deleteLogo(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/business/${businessId}/logo/delete/`, {
    method: 'DELETE',
    headers,
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to delete the logo')
  }

  return response.json()
}

export async function getSystemPrompts(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/system-prompt/${businessId}/`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch the prompts')
  }

  return response.json() as Promise<SystemPrompts>
}

export async function updateSystemPrompts(
  businessId: number,
  prompts: Partial<SystemPrompts>
) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/system-prompt/${businessId}/update/`,
    {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(prompts),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to update the prompts')
  }

  return response.json()
}

export async function getTeamMembers(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/business-user/${businessId}/`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch team members')
  }

  return response.json() as Promise<TeamMember[]>
}

export async function addTeamMember(businessId: number, email: string, role: string) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/business-user/${businessId}/add/`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, role }),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to add the team member')
  }
}

export async function updateTeamMemberRole(
  businessId: number,
  memberId: number,
  role: string
) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/business-user/${businessId}/edit/${memberId}/`,
    {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to update the role')
  }
}

export async function removeTeamMember(businessId: number, memberId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/business/business-user/${businessId}/delete/${memberId}/`,
    { method: 'DELETE', headers }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to remove the team member')
  }
}

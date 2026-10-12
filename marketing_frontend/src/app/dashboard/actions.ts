'use server'

import { createClient } from '@/utils/supabase/server'

export interface SocialMediaAccount {
  id: number
  business: number
  platform: string
  account_username: string
  account_url: string
  profile_picture_url: string | null
  is_active: boolean
  last_used_at: string | null
  created_at: string
  updated_at: string
}

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

export async function getBusinessDetails(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/business/${businessId}/`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw new Error('Failed to fetch business details')
  }

  return response.json()
}

export async function getSocialMediaAccounts(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/business/social-media-accounts/?business_id=${businessId}`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw new Error('Failed to fetch social media accounts')
  }

  const accounts: SocialMediaAccount[] = await response.json()
  return accounts
}

export async function connectSocialMediaAccount(businessId: number, platform: string) {
  const headers = await authHeaders()

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/auth/${platform}/login/?business_id=${businessId}`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(errorData?.error || 'Failed to start the connection flow')
  }

  return response.json() as Promise<{ url: string }>
}

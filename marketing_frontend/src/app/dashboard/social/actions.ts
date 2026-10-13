'use server'

import { createClient } from '@/utils/supabase/server'

export interface SocialMediaPost {
  id: number
  post_text: string
  post_images_urls: string[]
  post_video_urls: string[]
  posted_link: string | null
  hashtags: string[]
  image_prompt: string
  post_platform: string
  source: string | null
  source_url: string | null
  status: string
  feedback: string
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface PostCreationStatus {
  status: 'completed' | 'no_recent_posts'
  recent_posts?: SocialMediaPost[]
  count?: number
  message?: string
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

export async function getSocialMediaPosts(businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/social-media/social-media-posts/?business_id=${businessId}`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch social media posts')
  }

  return response.json() as Promise<SocialMediaPost[]>
}

export async function createSocialMediaPosts(
  businessId: number,
  topic: string,
  platform: string,
  numPosts: number = 1,
  isResearchNeeded: boolean = true,
  isImageNeeded: boolean = false
) {
  if (!topic || !platform) {
    throw new Error('Topic and platform are required')
  }

  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/social-media/social-media-posts/create/`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        business_id: businessId,
        topic,
        platform,
        num_posts: numPosts,
        is_research_needed: isResearchNeeded,
        is_image_needed: isImageNeeded,
      }),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to create social media posts')
  }

  return response.json()
}

export async function getPostCreationStatus(
  businessId: number
): Promise<PostCreationStatus> {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/social-media/post-creation-status/?business_id=${businessId}`,
    { headers, cache: 'no-store' }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch post creation status')
  }

  return response.json()
}

export async function publishSocialMediaPost(postId: number, businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/social-media/posts/${postId}/publish/?business_id=${businessId}`,
    { method: 'POST', headers }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to publish social media post')
  }

  return response.json() as Promise<{
    message: string
    platform: string
    post_url: string
  }>
}

export async function updateSocialMediaPost(
  postId: number,
  businessId: number,
  updateData: {
    post_text?: string
    hashtags?: string[]
    feedback?: string
    image_prompt?: string
    post_images_urls?: string[]
  }
) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/social-media/social-media-posts/update/${postId}/?business_id=${businessId}`,
    {
      method: 'PATCH',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData),
    }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to update social media post')
  }

  return response.json()
}

export async function updatePostFeedback(
  postId: number,
  businessId: number,
  feedback: string
) {
  return updateSocialMediaPost(postId, businessId, { feedback })
}

export async function deleteSocialMediaPost(postId: number, businessId: number) {
  const headers = await authHeaders()

  const response = await fetch(
    `${API_URL()}/api/social-media/social-media-posts/delete/${postId}/?business_id=${businessId}`,
    { method: 'DELETE', headers }
  )

  if (!response.ok) {
    throw await readError(response, 'Failed to delete social media post')
  }

  return response.json()
}

export async function generateAIImage(prompt: string) {
  if (!prompt) {
    throw new Error('Prompt is required')
  }

  const headers = await authHeaders()

  const response = await fetch(`${API_URL()}/api/social-media/generate-ai-image/`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to generate AI image')
  }

  return response.json() as Promise<{ image_url: string }>
}

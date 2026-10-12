# Marketing Agent

An AI agent that researches a topic, writes platform-native social media posts for your
brand, generates matching images, and publishes them to Twitter, Facebook, Instagram and
LinkedIn.

- `marketing_backend/` — Django + DRF API, the LangGraph post-generation agent, and the
  publishing integrations.
- `marketing_frontend/` — Next.js App Router UI.

## How it works

You create a **business**, and the agent reads your website plus any documents you upload
to build a knowledge base and derive a brand-voice system prompt. From then on you give it
a topic, and a LangGraph pipeline runs three steps:

1. **Research** — pulls current context on the topic via SerpAPI (skipped if no key is set,
   or if you untick "research the topic first").
2. **Post ideas** — turns the research and your business context into distinct angles.
3. **Copy + image** — writes each post to the target platform's limits and tone, and
   generates an image from a prompt it writes itself.

Posts land as **drafts** so you can edit the copy, hashtags and images before publishing.
Generation runs in a background thread; the UI polls for completion.

## Prerequisites

- Python 3.11+ and Node 20+
- A [Supabase](https://supabase.com) project — used for user auth and for media storage
- An [OpenRouter](https://openrouter.ai) API key for the LLM

Optional, each unlocking one feature: a Google AI key (image generation), a SerpAPI key
(topic research), and Facebook / Twitter / LinkedIn app credentials (publishing).

## Backend setup

```bash
cd marketing_backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then fill in the values
python manage.py migrate
python manage.py runserver
```

The API is then on `http://localhost:8000`. `GET /api/health/` should return
`{"status": "ok"}`.

`USE_SQLITE=true` (the default) keeps everything local. Set it to `false` and fill in the
`DB_*` variables to point at Postgres.

## Frontend setup

```bash
cd marketing_frontend
npm install

cp .env.example .env.local      # then fill in the values
npm run dev
```

The UI is then on `http://localhost:3000`. `NEXT_PUBLIC_SUPABASE_URL` must point at the
same Supabase project the backend uses, since the frontend sends the Supabase access token
and the backend verifies it.

## Supabase configuration

1. **Auth** — enable email/password. For the Google button, enable the Google provider and
   add `http://localhost:3000/auth/callback` as a redirect URL.
2. **Storage** — create two buckets, `media` (logos and generated post images) and
   `static`. **Both must be marked public.** Creating a business fails with an empty
   `PutObject` error if `media` does not exist, and the social platforms cannot fetch your
   post images unless the bucket is public, since they download them by URL.
3. **S3 access keys** — under Storage settings, generate S3 credentials and put them in
   `SUPABASE_S3_ACCESS_KEY` / `SUPABASE_S3_SECRET_KEY`. `AWS_S3_ENDPOINT_URL` is the S3
   endpoint shown on that page.

## Connecting publishing accounts

Each platform needs an OAuth app whose redirect URI points back at the API, e.g.
`http://localhost:8000/api/auth/facebook/callback/`. Once the credentials are in `.env`,
connect the accounts from **Settings → Integrations** in the UI.

Instagram publishes through the Facebook connection: connecting a Facebook Page that has a
linked Instagram Business account enables both. Note that Instagram requires an image —
text-only posts are rejected.

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health/` | Liveness check |
| `POST` | `/api/business/process/` | Create a business and start onboarding |
| `GET` | `/api/business/process/status/<id>/` | Poll onboarding progress |
| `GET` | `/api/business/` | List accessible businesses |
| `GET/PUT` | `/api/business/<id>/`, `/update/` | Read and edit a business |
| `GET/POST/PUT/DELETE` | `/api/business/knowledge-base/<id>/...` | Knowledge base entries |
| `GET/PUT` | `/api/business/system-prompt/<id>/...` | Brand voice and research prompts |
| `GET` | `/api/social-media/social-media-posts/` | List posts |
| `POST` | `/api/social-media/social-media-posts/create/` | Generate posts (async) |
| `GET` | `/api/social-media/post-creation-status/` | Poll generation |
| `POST` | `/api/social-media/posts/<id>/publish/` | Publish to the platform |
| `POST` | `/api/social-media/generate-ai-image/` | Generate a standalone image |

All endpoints except `/api/health/` expect an `Authorization: Bearer <supabase-jwt>`
header.

## Notes on running without every key

The app is built to degrade rather than crash. Without an OpenRouter key the server still
starts and migrations still run — the LLM is only constructed on first use. Without a
SerpAPI key, research is skipped and posts are written from your knowledge base alone.
Without a Google AI key, posts are generated as text only.

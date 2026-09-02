export interface VideoInfo {
  video_id: string
  title: string
  error: string | null
}

export interface SessionVideo extends VideoInfo {
  summary: string | null
  flashcards: string | null
  quiz: string | null
}

export interface SessionPayload {
  session_id: string
  videos: SessionVideo[]
  chat: { question: string; answer: string }[]
}

export interface ProcessResponse {
  session_id: string
  videos: VideoInfo[]
}

export interface GenerateResponse {
  session_id: string
  video_id: string
  action: 'summary' | 'flashcards' | 'quiz'
  content: string
}

export interface AskResponse {
  session_id: string
  question: string
  answer: string
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // keep default message
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function getSession(): Promise<SessionPayload> {
  const res = await fetch('/api/session')
  return handle<SessionPayload>(res)
}

export async function releaseSession(): Promise<void> {
  const res = await fetch('/api/release', { method: 'POST' })
  await handle<{ released: boolean }>(res)
}

export async function processUrl(url: string): Promise<ProcessResponse> {
  const res = await fetch('/api/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return handle<ProcessResponse>(res)
}

export async function generate(
  videoId: string,
  action: 'summary' | 'flashcards' | 'quiz',
): Promise<GenerateResponse> {
  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, action }),
  })
  return handle<GenerateResponse>(res)
}

export async function ask(question: string): Promise<AskResponse> {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return handle<AskResponse>(res)
}

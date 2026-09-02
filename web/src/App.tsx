import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Play,
  ArrowRight,
  BookOpen,
  Stack,
  ListChecks,
  ChatCircleText,
  Spinner,
  ArrowClockwise,
  WarningCircle,
} from '@phosphor-icons/react'
import { processUrl, generate, ask, getSession, releaseSession, type SessionVideo, type VideoInfo } from './api'

type TabKey = 'summary' | 'flashcards' | 'quiz'

interface VideoState {
  info: VideoInfo
  content: Partial<Record<TabKey, string>>
}

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

const TAB_META: Record<TabKey, { label: string; icon: typeof BookOpen }> = {
  summary: { label: 'Notes', icon: BookOpen },
  flashcards: { label: 'Flashcards', icon: Stack },
  quiz: { label: 'Quiz', icon: ListChecks },
}

function videoStateFromSessionVideo(v: SessionVideo): VideoState {
  const content: Partial<Record<TabKey, string>> = {}
  if (v.summary) content.summary = v.summary
  if (v.flashcards) content.flashcards = v.flashcards
  if (v.quiz) content.quiz = v.quiz
  return { info: { video_id: v.video_id, title: v.title, error: v.error }, content }
}

function VideoCard({
  video,
  busyTab,
  onGenerate,
}: {
  video: VideoState
  busyTab: TabKey | null
  onGenerate: (videoId: string, action: TabKey) => void
}) {
  const [activeTab, setActiveTab] = useState<TabKey | null>(null)
  const availableTabs = (Object.keys(TAB_META) as TabKey[]).filter((k) => video.content[k])

  if (video.info.error) {
    return (
      <article className="border-l-2 pl-5 py-1" style={{ borderColor: 'var(--rust)' }}>
        <p className="kicker flex items-center gap-2">
          <WarningCircle size={14} /> Transcript unavailable
        </p>
        <h3 className="font-display text-2xl mt-2">{video.info.title}</h3>
        <p className="mt-2 text-sm" style={{ color: 'var(--muted)' }}>
          {video.info.error}
        </p>
      </article>
    )
  }

  return (
    <article>
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 className="font-display text-2xl leading-snug max-w-2xl">{video.info.title}</h3>
        <a
          href={`https://www.youtube.com/watch?v=${video.info.video_id}`}
          target="_blank"
          rel="noreferrer"
          className="font-mono-ui text-xs shrink-0 hover:underline"
          style={{ color: 'var(--muted)' }}
        >
          {video.info.video_id}
        </a>
      </header>

      <div className="mt-4 flex flex-wrap gap-3">
        {(Object.keys(TAB_META) as TabKey[]).map((action) => {
          const Icon = TAB_META[action].icon
          const busy = busyTab === action
          return (
            <button
              key={action}
              disabled={busyTab !== null}
              onClick={() => onGenerate(video.info.video_id, action)}
              className={busy ? 'btn-primary' : 'btn-ghost'}
              style={{ borderRadius: 0, padding: '0.5rem 1rem', fontSize: '0.875rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              {busy ? <Spinner size={15} className="animate-spin" /> : <Icon size={15} />}
              {busy ? 'Working' : TAB_META[action].label}
            </button>
          )
        })}
      </div>

      {busyTab !== null && (
        <p className="mt-3 text-sm" style={{ color: 'var(--muted)' }}>
          Generating. This can take up to a minute.
        </p>
      )}

      {availableTabs.length > 0 && (
        <div className="mt-6">
          <div className="flex gap-6 border-b rule">
            {availableTabs.map((tab) => {
              const Icon = TAB_META[tab].icon
              const active = (activeTab ?? availableTabs[availableTabs.length - 1]) === tab
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex items-center gap-1.5 pb-2 text-sm ${active ? 'tab-active' : 'tab-inactive'}`}
                >
                  <Icon size={14} />
                  {TAB_META[tab].label}
                </button>
              )
            })}
          </div>
          <div className="mt-5 whitespace-pre-wrap text-[0.925rem] leading-relaxed max-w-[70ch]">
            {video.content[(activeTab ?? availableTabs[availableTabs.length - 1]) as TabKey]}
          </div>
        </div>
      )}
    </article>
  )
}

export default function App() {
  const [url, setUrl] = useState('')
  const [videos, setVideos] = useState<VideoState[]>([])
  const [processing, setProcessing] = useState(false)
  const [busyTab, setBusyTab] = useState<TabKey | null>(null)
  const [notice, setNotice] = useState<{ kind: 'error' | 'info'; text: string } | null>(null)
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const hasTranscripts = videos.some((v) => !v.info.error)

  useEffect(() => {
    getSession()
      .then((payload) => {
        setVideos(payload.videos.map(videoStateFromSessionVideo))
        setChat(
          payload.chat.flatMap((m) => [
            { role: 'user' as const, text: m.question },
            { role: 'assistant' as const, text: m.answer },
          ]),
        )
      })
      .catch(() => {
        // First visit: an empty session binds on the first API call anyway.
      })
  }, [])

  const handleProcess = useCallback(async () => {
    if (!url.trim() || processing) return
    setProcessing(true)
    setNotice(null)
    try {
      const res = await processUrl(url.trim())
      setVideos(res.videos.map((info) => ({ info, content: {} })))
      setChat([])
      const failed = res.videos.filter((v) => v.error).length
      if (failed === res.videos.length) {
        setNotice({ kind: 'error', text: 'Could not extract transcripts for any video. Check the URL or API keys.' })
      } else if (failed > 0) {
        setNotice({ kind: 'info', text: `Processed ${res.videos.length - failed} of ${res.videos.length} videos. Some transcripts failed.` })
      }
    } catch (err) {
      setNotice({ kind: 'error', text: err instanceof Error ? err.message : String(err) })
    } finally {
      setProcessing(false)
    }
  }, [url, processing])

  const handleGenerate = useCallback(
    async (videoId: string, action: TabKey) => {
      if (busyTab) return
      setBusyTab(action)
      try {
        const res = await generate(videoId, action)
        setVideos((prev) =>
          prev.map((v) =>
            v.info.video_id === videoId ? { ...v, content: { ...v.content, [action]: res.content } } : v,
          ),
        )
      } catch (err) {
        setNotice({ kind: 'error', text: err instanceof Error ? err.message : String(err) })
      } finally {
        setBusyTab(null)
      }
    },
    [busyTab],
  )

  const handleAsk = useCallback(async () => {
    const q = question.trim()
    if (!q || asking) return
    setQuestion('')
    setChat((prev) => [...prev, { role: 'user', text: q }])
    setAsking(true)
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    try {
      const res = await ask(q)
      setChat((prev) => [...prev, { role: 'assistant', text: res.answer }])
    } catch (err) {
      setChat((prev) => [...prev, { role: 'assistant', text: err instanceof Error ? err.message : String(err) }])
    } finally {
      setAsking(false)
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [question, asking])

  const handleReset = useCallback(async () => {
    try {
      await releaseSession()
    } catch {
      // Still clear the local view; a fresh session binds on the next call.
    }
    setUrl('')
    setVideos([])
    setChat([])
    setNotice(null)
  }, [])

  return (
    <div className="min-h-[100dvh]" style={{ background: 'var(--paper)', color: 'var(--ink)' }}>
      <div className="mx-auto max-w-3xl px-6 pt-20 pb-24">

        {/* Asymmetric editorial hero: left-aligned, no centered hero, no scroll cue */}
        <header>
          <p className="kicker">Study tool</p>
          <h1 className="font-display text-5xl md:text-6xl leading-[1.05] tracking-tight mt-3 max-w-xl">
            Turn any YouTube video into study material.
          </h1>
          <p className="mt-5 text-base leading-relaxed max-w-[58ch]" style={{ color: 'var(--muted)' }}>
            Paste a video or playlist link. Get chapter notes, flashcards, and a quiz. Then ask
            questions grounded in the full transcript, not just the summary.
          </p>
        </header>

        {/* URL entry: underlined input field, print-style, with a rust action button */}
        <section className="mt-12">
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label htmlFor="url" className="kicker block mb-2">
                Video or playlist URL
              </label>
              <input
                id="url"
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleProcess()}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={processing || busyTab !== null}
                className="input-line w-full py-2 text-[0.95rem]"
              />
            </div>
            <button
              onClick={handleProcess}
              disabled={processing || busyTab !== null || !url.trim()}
              className="btn-primary inline-flex items-center gap-2 font-medium"
              style={{ borderRadius: 0, padding: '0.7rem 1.4rem', fontSize: '0.9rem' }}
            >
              {processing ? <Spinner size={16} className="animate-spin" /> : <Play size={15} weight="fill" />}
              {processing ? 'Processing' : 'Process'}
              {!processing && <ArrowRight size={14} />}
            </button>
          </div>

          {notice && (
            <p
              className="mt-4 text-sm border-l-2 pl-3 py-1"
              style={{
                color: notice.kind === 'error' ? 'var(--rust)' : 'var(--muted)',
                borderColor: notice.kind === 'error' ? 'var(--rust)' : 'var(--hairline)',
              }}
            >
              {notice.text}
            </p>
          )}
        </section>

        {/* Video results: hairline-separated editorial stack, no cards */}
        {videos.length > 0 && (
          <section className="mt-16">
            <p className="kicker">
              {videos.length} {videos.length === 1 ? 'video' : 'videos'} loaded
            </p>
            <div className="mt-6 space-y-14 divide-y rule">
              {videos.map((v) => (
                <VideoCard key={v.info.video_id} video={v} busyTab={busyTab} onGenerate={handleGenerate} />
              ))}
            </div>
          </section>
        )}

        {/* RAG chat, only when transcripts exist */}
        {hasTranscripts && (
          <section className="mt-20 border-t-2 pt-8" style={{ borderColor: 'var(--ink)' }}>
            <p className="kicker flex items-center gap-2">
              <ChatCircleText size={14} /> Ask the transcripts
            </p>

            {chat.length > 0 && (
              <div className="mt-6 space-y-3">
                {chat.map((m, i) => (
                  <div
                    key={i}
                    className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed ${
                      m.role === 'user' ? 'chat-user ml-auto' : 'chat-assistant'
                    }`}
                    style={{ borderRadius: 0 }}
                  >
                    {m.text}
                  </div>
                ))}
                {asking && (
                  <p className="text-sm flex items-center gap-2" style={{ color: 'var(--muted)' }}>
                    <Spinner size={14} className="animate-spin" /> Thinking
                  </p>
                )}
                <div ref={chatEndRef} />
              </div>
            )}

            <div className="mt-6 flex items-end gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                  placeholder="Ask anything about the video content"
                  disabled={asking}
                  className="input-line w-full py-2 text-[0.95rem]"
                />
              </div>
              <button
                onClick={handleAsk}
                disabled={asking || !question.trim()}
                className="btn-primary inline-flex items-center gap-2 font-medium"
                style={{ borderRadius: 0, padding: '0.7rem 1.4rem', fontSize: '0.9rem' }}
              >
                {asking ? <Spinner size={15} className="animate-spin" /> : <ArrowRight size={14} weight="bold" />}
                Ask
              </button>
            </div>
          </section>
        )}

        {/* Footer with session controls */}
        {(videos.length > 0 || chat.length > 0) && (
          <footer className="mt-20 border-t rule pt-6 flex items-center justify-between">
            <p className="font-mono-ui text-xs" style={{ color: 'var(--muted)' }}>
              {videos.length} {videos.length === 1 ? 'video' : 'videos'} · {Math.floor(chat.length / 2)}{' '}
              {Math.floor(chat.length / 2) === 1 ? 'question' : 'questions'}
            </p>
            <button
              onClick={handleReset}
              className="text-sm inline-flex items-center gap-1.5 hover:underline"
              style={{ color: 'var(--muted)' }}
            >
              <ArrowClockwise size={14} />
              Clear session
            </button>
          </footer>
        )}
      </div>
    </div>
  )
}

'use client'
import { useState, useRef, useCallback } from 'react'
import JSZip from 'jszip'
import { PipelineProgress } from '@/components/PipelineProgress'
import { FileExplorer } from '@/components/FileExplorer'
import { CodeViewer } from '@/components/CodeViewer'
import type { GeneratedFile, PipelineStep, GameConcept, GenerationEvent } from '@/lib/generator/types'
import { PIPELINE_STEPS } from '@/lib/generator/pipeline'

const EXAMPLES = [
  'An underwater tycoon where players build a deep-sea base, mine minerals, fight sea creatures, and prestige for multipliers',
  'A cozy farming village where players grow rare crops, trade with friends, and unlock seasonal recipes together',
  'A horror escape room with a procedurally placed monster, sanity system, and 5 puzzles to solve before escaping',
  'A cooking competition where players race to complete customer orders, earn combos, and unlock new recipes',
  'A pet simulator where players collect eggs to hatch pets that help them collect coins to unlock new areas',
  'A roleplay café where players choose roles (chef, waiter, customer), complete tasks, and earn reputation',
  'A zombie survival RPG where players scavenge for resources, craft weapons, build shelter, and fight boss zombies at night',
  'A battle royale where 20 players drop onto a shrinking island with loot crates and must be the last one standing',
]

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

interface ChatEvent {
  type: 'explanation' | 'file' | 'text' | 'done' | 'error'
  text?: string
  path?: string
  displayName?: string
  fileType?: string
  content?: string
  isNew?: boolean
  error?: string
}

function initSteps(): PipelineStep[] {
  return PIPELINE_STEPS.map(s => ({ ...s, status: 'pending' as const, files: [] }))
}

type Phase = 'idle' | 'generating' | 'done' | 'error'

export default function Home() {
  const [description, setDescription] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [steps, setSteps] = useState<PipelineStep[]>(initSteps())
  const [files, setFiles] = useState<GeneratedFile[]>([])
  const [concept, setConcept] = useState<GameConcept | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const selectedFile = files.find(f => f.path === selected) ?? null

  const updateStep = useCallback((id: string, patch: Partial<PipelineStep>) => {
    setSteps(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s))
  }, [])

  async function sendChat() {
    if (!chatInput.trim() || chatLoading || !concept) return
    const userMsg = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }])
    setChatLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg,
          files,
          gameName: concept.name,
          gameGenre: concept.genre,
          coreLoop: concept.coreLoop,
        }),
      })
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      let assistantText = ''
      let updatedFiles: GeneratedFile[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const ev: ChatEvent = JSON.parse(line.slice(6))

          if (ev.type === 'explanation' && ev.text) {
            assistantText = ev.text
          }
          if (ev.type === 'text' && ev.text) {
            assistantText = ev.text
          }
          if (ev.type === 'file' && ev.path && ev.content) {
            const newFile: GeneratedFile = {
              path: ev.path,
              displayName: ev.displayName ?? ev.path.split('/').pop() ?? ev.path,
              type: (ev.fileType as GeneratedFile['type']) ?? 'module',
              content: ev.content,
              lines: ev.content.split('\n').length,
            }
            updatedFiles.push(newFile)
            setFiles(prev => {
              const next = [...prev.filter(f => f.path !== ev.path), newFile]
              return next
            })
            setSelected(ev.path)
            if (!assistantText) {
              assistantText = ev.isNew
                ? `Created new file: ${ev.path}`
                : `Updated: ${ev.path}`
            }
          }
          if (ev.type === 'done') {
            const summary = updatedFiles.length > 0
              ? `${assistantText}\n\n✓ ${updatedFiles.length} file(s) updated in the editor above.`
              : assistantText
            setChatMessages(prev => [...prev, { role: 'assistant', text: summary }])
            setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
          }
          if (ev.type === 'error') {
            setChatMessages(prev => [...prev, { role: 'assistant', text: `Error: ${ev.error}` }])
          }
        }
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'assistant', text: `Error: ${String(err)}` }])
    } finally {
      setChatLoading(false)
    }
  }

  async function generate() {
    if (!description.trim() || phase === 'generating') return
    abortRef.current = new AbortController()
    setPhase('generating')
    setFiles([])
    setSelected(null)
    setConcept(null)
    setError(null)
    setSteps(initSteps())

    const stepStartTimes: Record<string, number> = {}

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description }),
        signal: abortRef.current.signal,
      })

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })

        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const ev: GenerationEvent = JSON.parse(line.slice(6))

          if (ev.type === 'concept' && ev.concept) {
            setConcept(ev.concept)
          }

          if (ev.type === 'step_start' && ev.stepId) {
            stepStartTimes[ev.stepId] = Date.now()
            updateStep(ev.stepId, { status: 'running', label: ev.label ?? '' })
          }

          if (ev.type === 'step_done' && ev.stepId) {
            const dur = Date.now() - (stepStartTimes[ev.stepId] ?? Date.now())
            updateStep(ev.stepId, { status: 'done', durationMs: dur })
          }

          if (ev.type === 'file' && ev.path && ev.content) {
            const newFile: GeneratedFile = {
              path: ev.path,
              displayName: ev.displayName ?? ev.path.split('/').pop() ?? ev.path,
              type: ev.fileType ?? 'module',
              content: ev.content,
              lines: ev.content.split('\n').length,
            }
            setFiles(prev => {
              const next = [...prev.filter(f => f.path !== ev.path), newFile]
              return next
            })
            if (!selected) setSelected(ev.path)

            // Add file to its step
            const stepId = ev.fileType === 'config' && ev.path.includes('GameConfig') ? 'config'
              : ev.path.includes('RemoteEvents') || ev.path.includes('DataManager') ? 'data'
              : ev.fileType === 'server' ? 'server'
              : ev.fileType === 'client' ? 'client'
              : ev.path.includes('project.json') ? 'rojo'
              : 'server'
            setSteps(prev => prev.map(s => s.id === stepId
              ? { ...s, files: [...s.files, newFile.displayName] }
              : s
            ))
          }

          if (ev.type === 'complete') {
            setPhase('done')
            updateStep('package', { status: 'done' })
          }

          if (ev.type === 'error') {
            setError(ev.error ?? 'Unknown error')
            setPhase('error')
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return
      setError(String(err))
      setPhase('error')
    }
  }

  async function downloadZip() {
    if (!files.length || !concept) return
    const zip = new JSZip()
    const root = zip.folder(concept.name.replace(/\s+/g, ''))!
    for (const f of files) {
      if (f.path.endsWith('.json')) root.file(f.path, f.content)
      else root.file(f.path, f.content)
    }
    const blob = await zip.generateAsync({ type: 'blob' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${concept.name.replace(/\s+/g, '_')}_Rojo.zip`
    a.click()
    URL.revokeObjectURL(url)
  }

  const showWorkspace = phase === 'generating' || phase === 'done' || phase === 'error'

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── HEADER ────────────────────────────────────────────── */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-purple-500 rounded-lg flex items-center justify-center text-sm font-bold">R</div>
          <div>
            <h1 className="text-sm font-bold text-white">Roblox AI Generator</h1>
            <p className="text-xs text-gray-500">Describe → Build → Download</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {concept && (
            <div className="hidden md:flex items-center gap-2 text-xs text-gray-400 bg-gray-800 px-3 py-1.5 rounded-full">
              <span className="text-cyan-400">{concept.name}</span>
              <span>·</span>
              <span className="capitalize">{concept.genre}</span>
            </div>
          )}
          {phase === 'done' && (
            <button onClick={downloadZip}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-black font-semibold text-sm rounded-lg transition-all">
              ↓ Download Rojo .zip
            </button>
          )}
        </div>
      </header>

      {/* ── HERO (only before generation) ─────────────────────── */}
      {!showWorkspace && (
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
          <div className="text-center mb-10 max-w-2xl">
            <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-4 py-1.5 text-xs text-cyan-400 mb-6">
              ✨ Powered by Claude · 8 game genres · 20+ scripts per game
            </div>
            <h2 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent leading-tight">
              Build any Roblox game<br />without writing a line
            </h2>
            <p className="text-gray-400 text-lg">
              Describe your game idea. AI generates every script, config, and Rojo project — ready to open in Studio.
            </p>
          </div>

          {/* Input */}
          <div className="w-full max-w-2xl">
            <div className="relative">
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) generate() }}
                placeholder="Describe your game... e.g. 'A tycoon where players build underwater bases, collect minerals, and fight sea monsters'"
                rows={4}
                className="w-full bg-gray-900 border border-gray-700 focus:border-cyan-500 rounded-xl px-4 py-4 text-white placeholder-gray-600 text-sm resize-none outline-none transition-colors"
              />
              <div className="absolute bottom-3 right-3 text-xs text-gray-600">
                {description.length > 0 ? `${description.length} chars · Ctrl+Enter to generate` : 'Ctrl+Enter to generate'}
              </div>
            </div>

            <button
              onClick={generate}
              disabled={!description.trim()}
              className="w-full mt-3 py-3.5 bg-gradient-to-r from-cyan-500 via-cyan-500 to-purple-500 hover:from-cyan-400 hover:to-purple-400 disabled:opacity-30 disabled:cursor-not-allowed text-black font-bold text-base rounded-xl transition-all transform hover:scale-[1.01] active:scale-[0.99]"
            >
              🚀 Generate Full Game
            </button>
          </div>

          {/* Examples */}
          <div className="mt-8 w-full max-w-2xl">
            <p className="text-xs text-gray-600 text-center mb-3">Try an example</p>
            <div className="grid grid-cols-1 gap-2">
              {EXAMPLES.map((ex, i) => (
                <button key={i} onClick={() => setDescription(ex)}
                  className="text-left text-xs text-gray-400 hover:text-gray-200 bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 px-4 py-3 rounded-lg transition-all truncate">
                  {ex}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── WORKSPACE (during/after generation) ───────────────── */}
      {showWorkspace && (
        <div className="flex-1 flex overflow-hidden">
          {/* LEFT: Pipeline + description */}
          <div className="w-72 flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden">
            {/* Input bar at top */}
            <div className="p-4 border-b border-gray-800 flex-shrink-0">
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={2}
                className="w-full bg-gray-900 border border-gray-700 focus:border-cyan-500 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-600 resize-none outline-none"
              />
              <button
                onClick={() => { setPhase('idle'); setSteps(initSteps()); setFiles([]); setConcept(null) }}
                className="mt-2 w-full text-xs py-1.5 border border-gray-700 hover:border-gray-600 text-gray-400 hover:text-white rounded-lg transition-colors"
              >
                ← New Game
              </button>
            </div>

            {/* Concept info */}
            {concept && (
              <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
                <div className="text-sm font-semibold text-white">{concept.name}</div>
                <div className="text-xs text-cyan-400 capitalize mb-1">{concept.genre}</div>
                <div className="text-xs text-gray-500 line-clamp-2">{concept.coreLoop}</div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {concept.resources.slice(0, 4).map(r => (
                    <span key={r} className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{r}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Pipeline progress */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Build Pipeline</div>
              <PipelineProgress steps={steps} />

              {phase === 'done' && (
                <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <div className="text-xs text-emerald-400 font-medium mb-1">✓ Generation complete</div>
                  <div className="text-xs text-gray-500">{files.length} files · Ready to download</div>
                </div>
              )}

              {phase === 'error' && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <div className="text-xs text-red-400 font-medium mb-1">Error</div>
                  <div className="text-xs text-gray-500">{error}</div>
                </div>
              )}

              {phase === 'generating' && (
                <div className="mt-4 p-3 bg-cyan-500/5 border border-cyan-500/20 rounded-lg">
                  <div className="text-xs text-cyan-400 flex items-center gap-2">
                    <span className="animate-spin">◌</span>
                    Generating scripts...
                  </div>
                  <div className="text-xs text-gray-600 mt-1">{files.length} files created so far</div>
                </div>
              )}
            </div>

            {/* Download */}
            {phase === 'done' && (
              <div className="p-4 border-t border-gray-800 flex-shrink-0">
                <button onClick={downloadZip}
                  className="w-full py-2.5 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-black font-bold text-sm rounded-lg transition-all">
                  ↓ Download Rojo .zip
                </button>
                <p className="text-xs text-gray-600 text-center mt-2">
                  Extract → rojo serve → Connect in Studio
                </p>
              </div>
            )}
          </div>

          {/* CHAT: AI iterate panel (only shown after done) */}
          {phase === 'done' && concept && (
            <div className="w-72 flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
                <div className="text-xs text-gray-500 uppercase tracking-wider">AI Chat</div>
                <div className="text-xs text-gray-600 mt-0.5">Ask to add, modify, or fix anything</div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {chatMessages.length === 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-600 mb-2">Try asking:</p>
                    {[
                      'Add a daily reward system',
                      'Add an enemy NPC that patrols',
                      'Make the shop prettier with icons',
                      'Add a prestige/rebirth system',
                      'Fix the DataManager auto-save',
                    ].map(s => (
                      <button key={s} onClick={() => setChatInput(s)}
                        className="w-full text-left text-xs text-gray-400 hover:text-white bg-gray-900 hover:bg-gray-800 border border-gray-800 px-3 py-2 rounded-lg transition-colors">
                        {s}
                      </button>
                    ))}
                  </div>
                )}
                {chatMessages.map((m, i) => (
                  <div key={i} className={`flex flex-col gap-1 ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`text-xs px-3 py-2 rounded-lg max-w-[95%] whitespace-pre-wrap leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-cyan-500/20 text-cyan-100 border border-cyan-500/20'
                        : 'bg-gray-800 text-gray-300 border border-gray-700'
                    }`}>
                      {m.text}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex items-center gap-2 text-xs text-gray-500 px-3 py-2 bg-gray-800 rounded-lg border border-gray-700 w-fit">
                    <span className="animate-spin">◌</span> Thinking...
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input */}
              <div className="p-3 border-t border-gray-800 flex-shrink-0">
                <div className="flex gap-2">
                  <input
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
                    placeholder="Add a shop, fix a bug..."
                    disabled={chatLoading}
                    className="flex-1 bg-gray-900 border border-gray-700 focus:border-cyan-500 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-600 outline-none disabled:opacity-50"
                  />
                  <button
                    onClick={sendChat}
                    disabled={chatLoading || !chatInput.trim()}
                    className="px-3 py-2 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-30 text-black text-xs font-bold rounded-lg transition-colors"
                  >
                    →
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* CENTER: File Explorer */}
          <div className="w-56 flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
              <div className="text-xs text-gray-500 uppercase tracking-wider">Files ({files.length})</div>
            </div>
            <div className="flex-1 p-2 overflow-hidden">
              <FileExplorer files={files} selected={selected} onSelect={setSelected} />
            </div>
          </div>

          {/* RIGHT: Code Viewer */}
          <div className="flex-1 flex flex-col overflow-hidden bg-gray-900/30">
            <CodeViewer file={selectedFile} />
          </div>
        </div>
      )}
    </div>
  )
}

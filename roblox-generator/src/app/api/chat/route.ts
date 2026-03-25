import Anthropic from '@anthropic-ai/sdk'
import { ROBLOX_SYSTEM_PROMPT } from '@/lib/generator/prompts'
import type { GeneratedFile } from '@/lib/generator/types'

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

export async function POST(req: Request) {
  const { message, files, gameName, gameGenre, coreLoop } = await req.json() as {
    message: string
    files: GeneratedFile[]
    gameName: string
    gameGenre: string
    coreLoop: string
  }

  if (!message?.trim()) {
    return new Response(JSON.stringify({ error: 'Message required' }), { status: 400 })
  }

  // Build context from existing files (include up to 4 most relevant files to stay within context)
  const relevantFiles = selectRelevantFiles(files, message)
  const fileContext = relevantFiles
    .map(f => `-- ═══ FILE: ${f.path} ═══\n${f.content}`)
    .join('\n\n')

  const systemPrompt = ROBLOX_SYSTEM_PROMPT + `

═══ CHAT MODE — MODIFYING AN EXISTING GAME ═══
You are modifying an existing Roblox game called "${gameName}" (${gameGenre} genre).
Core loop: ${coreLoop}

When the user asks to:
• ADD a feature → generate the new script(s) and explain which file path to use
• MODIFY a script → output the COMPLETE updated file (not a diff)
• FIX a bug → identify the issue and output the corrected file
• EXPLAIN → describe how the code works without outputting full scripts
• GENERATE a new script → create it and specify the correct Roblox path

For file modifications: respond with a JSON object in this format:
{
  "explanation": "What changed and why",
  "files": [
    {
      "path": "ServerScriptService/FileName.server.lua",
      "displayName": "FileName",
      "type": "server|client|module|config",
      "content": "-- full lua code here",
      "isNew": true|false
    }
  ]
}

For explanations (no code changes): respond with plain text.
Detect which mode is needed from the user's request.`

  const userMessage = fileContext
    ? `EXISTING FILES FOR CONTEXT:\n${fileContext}\n\nUSER REQUEST:\n${message}`
    : `USER REQUEST:\n${message}`

  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder()
      const send = (data: object) => {
        controller.enqueue(enc.encode(`data: ${JSON.stringify(data)}\n\n`))
      }

      try {
        const response = await client.messages.create({
          model: 'claude-opus-4-6',
          max_tokens: 8192,
          thinking: { type: 'adaptive' },
          system: systemPrompt,
          messages: [{ role: 'user', content: userMessage }],
        })

        const textBlock = response.content.find(b => b.type === 'text')
        const rawText = textBlock && textBlock.type === 'text' ? textBlock.text.trim() : ''

        // Try to parse as JSON (file modification response)
        try {
          const parsed = JSON.parse(rawText.replace(/^```json\n?/m, '').replace(/\n?```$/m, '').trim())
          if (parsed.files && Array.isArray(parsed.files)) {
            send({ type: 'explanation', text: parsed.explanation ?? '' })
            for (const f of parsed.files) {
              // Strip any accidental markdown fences from code
              const cleanContent = (f.content as string)
                .replace(/^```(?:lua|luau)?\n?/m, '')
                .replace(/\n?```$/m, '')
                .trim()
              send({
                type: 'file',
                path: f.path,
                displayName: f.displayName,
                fileType: f.type,
                content: cleanContent,
                isNew: f.isNew ?? false,
              })
            }
          } else {
            send({ type: 'text', text: rawText })
          }
        } catch {
          // Not JSON — plain text explanation
          send({ type: 'text', text: rawText })
        }

        send({ type: 'done' })
      } catch (err) {
        send({ type: 'error', error: String(err) })
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}

// Pick up to 4 files most relevant to the user's message
function selectRelevantFiles(files: GeneratedFile[], message: string): GeneratedFile[] {
  const lower = message.toLowerCase()
  const keywords = lower.split(/\s+/).filter(w => w.length > 3)

  const scored = files.map(f => {
    let score = 0
    const pathLower = f.path.toLowerCase()
    const contentLower = f.content.toLowerCase()
    for (const kw of keywords) {
      if (pathLower.includes(kw)) score += 3
      if (contentLower.includes(kw)) score += 1
    }
    // Always include GameConfig and RemoteEvents as context
    if (f.path.includes('GameConfig') || f.path.includes('RemoteEvents')) score += 5
    return { file: f, score }
  })

  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
    .map(s => s.file)
}

import Anthropic from '@anthropic-ai/sdk'
import { conceptPrompt, filePrompt, rojoProjectPrompt, ROBLOX_SYSTEM_PROMPT } from '@/lib/generator/prompts'
import { getFileSpecs, stepIdForFile } from '@/lib/generator/pipeline'
import type { GameConcept, GenerationEvent } from '@/lib/generator/types'

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

function send(controller: ReadableStreamDefaultController, event: GenerationEvent) {
  const enc = new TextEncoder()
  controller.enqueue(enc.encode(`data: ${JSON.stringify(event)}\n\n`))
}

async function callClaude(system: string, userMsg: string, maxTokens = 8192): Promise<string> {
  const msg = await client.messages.create({
    model: 'claude-opus-4-6',
    max_tokens: maxTokens,
    thinking: { type: 'adaptive' },
    system,
    messages: [{ role: 'user', content: userMsg }],
  })
  const block = msg.content.find(b => b.type === 'text')
  return block && block.type === 'text' ? block.text.trim() : ''
}

export async function POST(req: Request) {
  const { description } = await req.json()

  if (!description || description.length < 10) {
    return new Response(JSON.stringify({ error: 'Description too short' }), { status: 400 })
  }

  const stream = new ReadableStream({
    async start(controller) {
      try {
        // ── STEP 1: Analyze concept ────────────────────────────────────────
        send(controller, { type: 'step_start', stepId: 'analyze', label: 'Analyzing concept' })

        const conceptRaw = await callClaude(
          'You are a Roblox game designer. Return only valid JSON, no other text.',
          conceptPrompt(description),
          1024,
        )

        let concept: GameConcept
        try {
          concept = JSON.parse(conceptRaw.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim())
        } catch {
          // Fallback concept
          concept = {
            name: 'My Roblox Game',
            genre: 'custom',
            tagline: description.slice(0, 60),
            coreLoop: description,
            mechanics: ['exploration', 'collection'],
            systems: ['DataManager', 'GameManager'],
            resources: ['Coins'],
            zones: ['Zone 1'],
            playerDefaults: { Coins: 100 },
            monetization: ['gamepass: VIP'],
          }
        }

        send(controller, { type: 'concept', concept })
        send(controller, { type: 'step_done', stepId: 'analyze' })

        // ── STEP 2-5: Generate each file ──────────────────────────────────
        const specs = getFileSpecs(concept)
        send(controller, { type: 'step_start', stepId: 'config', label: 'Game Config' })

        const generatedSoFar: Record<string, string> = {}
        let currentStep = 'config'

        for (const spec of specs) {
          const stepId = stepIdForFile(spec)

          if (stepId !== currentStep) {
            send(controller, { type: 'step_done', stepId: currentStep })
            send(controller, { type: 'step_start', stepId, label: spec.displayName })
            currentStep = stepId
          }

          const content = await callClaude(
            ROBLOX_SYSTEM_PROMPT,
            filePrompt(spec, concept, generatedSoFar),
            4096,
          )

          // Strip any accidental markdown fences
          const clean = content.replace(/^```(?:lua|luau)?\n?/m, '').replace(/\n?```$/m, '').trim()
          generatedSoFar[spec.path] = clean

          send(controller, {
            type: 'file',
            path: spec.path,
            displayName: spec.displayName,
            fileType: spec.type,
            content: clean,
          })
        }

        send(controller, { type: 'step_done', stepId: currentStep })

        // ── STEP 6: Rojo config ────────────────────────────────────────────
        send(controller, { type: 'step_start', stepId: 'rojo', label: 'Rojo Config' })

        const rojoRaw = await callClaude(
          'You are a Rojo configuration expert. Return only valid JSON.',
          rojoProjectPrompt(concept, Object.keys(generatedSoFar)),
          1024,
        )

        const rojoClean = rojoRaw.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim()
        send(controller, { type: 'file', path: 'default.project.json', displayName: 'Rojo Config', fileType: 'config', content: rojoClean })
        send(controller, { type: 'step_done', stepId: 'rojo' })

        // ── STEP 7: Complete ───────────────────────────────────────────────
        send(controller, { type: 'step_start', stepId: 'package', label: 'Packaging' })
        send(controller, { type: 'step_done', stepId: 'package' })
        send(controller, { type: 'complete', totalFiles: specs.length + 1 })

      } catch (err) {
        send(controller, { type: 'error', error: String(err) })
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

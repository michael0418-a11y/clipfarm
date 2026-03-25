/**
 * Synchronous (non-streaming) generate endpoint for the Roblox Studio plugin.
 * Returns the full game as JSON once all files are generated.
 */
import Anthropic from '@anthropic-ai/sdk'
import { conceptPrompt, filePrompt, ROBLOX_SYSTEM_PROMPT } from '@/lib/generator/prompts'
import { getFileSpecs } from '@/lib/generator/pipeline'
import type { GameConcept } from '@/lib/generator/types'

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

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
    return Response.json({ error: 'Description too short' }, { status: 400 })
  }

  try {
    // Step 1: Analyze concept
    const conceptRaw = await callClaude(
      'You are a Roblox game designer. Return only valid JSON, no other text.',
      conceptPrompt(description),
      1024,
    )

    let concept: GameConcept
    try {
      concept = JSON.parse(conceptRaw.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim())
    } catch {
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

    // Step 2: Generate all files
    const specs = getFileSpecs(concept)
    const generatedSoFar: Record<string, string> = {}
    const outputFiles: Array<{ path: string; displayName: string; type: string; content: string }> = []

    for (const spec of specs) {
      const content = await callClaude(
        ROBLOX_SYSTEM_PROMPT,
        filePrompt(spec, concept, generatedSoFar),
        8192,
      )
      const clean = content.replace(/^```(?:lua|luau)?\n?/m, '').replace(/\n?```$/m, '').trim()
      generatedSoFar[spec.path] = clean
      outputFiles.push({
        path: spec.path,
        displayName: spec.displayName,
        type: spec.type,
        content: clean,
      })
    }

    return Response.json({
      concept,
      files: outputFiles,
      totalFiles: outputFiles.length,
    })
  } catch (err) {
    return Response.json({ error: String(err) }, { status: 500 })
  }
}

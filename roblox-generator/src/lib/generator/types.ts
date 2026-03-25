export type Genre = 'tycoon' | 'obby' | 'simulator' | 'battle-royale' | 'rpg' | 'shooter' | 'survival' | 'racing' | 'roleplay' | 'horror' | 'cozy' | 'cooking' | 'custom'

export interface GameConcept {
  name: string
  genre: Genre
  tagline: string
  coreLoop: string
  mechanics: string[]
  systems: string[]
  resources: string[]
  zones: string[]
  playerDefaults: Record<string, number>
  monetization: string[]
}

export interface FileSpec {
  path: string           // e.g. "ServerScriptService/GameManager.server.lua"
  displayName: string    // e.g. "GameManager"
  type: 'server' | 'client' | 'module' | 'config'
  description: string    // what this file does, for the prompt
  deps: string[]         // other files this one needs context from
}

export interface GeneratedFile {
  path: string
  displayName: string
  type: FileSpec['type']
  content: string
  lines: number
}

export type StepStatus = 'pending' | 'running' | 'done' | 'error'

export interface PipelineStep {
  id: string
  label: string
  description: string
  status: StepStatus
  files: string[]   // paths of files generated in this step
  durationMs?: number
}

export interface GenerationEvent {
  type: 'step_start' | 'step_done' | 'file' | 'concept' | 'complete' | 'error'
  stepId?: string
  label?: string
  path?: string
  displayName?: string
  fileType?: FileSpec['type']
  content?: string
  concept?: GameConcept
  error?: string
  totalFiles?: number
}

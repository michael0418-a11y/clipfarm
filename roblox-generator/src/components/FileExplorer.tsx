'use client'
import type { GeneratedFile } from '@/lib/generator/types'

const TYPE_COLORS: Record<string, string> = {
  server: 'text-red-400',
  client: 'text-cyan-400',
  module: 'text-yellow-400',
  config: 'text-purple-400',
}

const TYPE_ICONS: Record<string, string> = {
  server: '🖥',
  client: '🎮',
  module: '📦',
  config: '⚙️',
}

interface Props {
  files: GeneratedFile[]
  selected: string | null
  onSelect: (path: string) => void
}

function groupFiles(files: GeneratedFile[]): Record<string, GeneratedFile[]> {
  const groups: Record<string, GeneratedFile[]> = {}
  for (const f of files) {
    const dir = f.path.includes('/') ? f.path.split('/').slice(0, -1).join('/') : 'Root'
    if (!groups[dir]) groups[dir] = []
    groups[dir].push(f)
  }
  return groups
}

export function FileExplorer({ files, selected, onSelect }: Props) {
  const groups = groupFiles(files)

  if (files.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-600 text-sm">
        Files will appear here as they're generated
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto space-y-4 pr-1">
      {Object.entries(groups).map(([dir, groupFiles]) => (
        <div key={dir}>
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1 px-2">{dir}</div>
          {groupFiles.map(f => (
            <button
              key={f.path}
              onClick={() => onSelect(f.path)}
              className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 transition-all duration-150 group animate-fade-in ${
                selected === f.path
                  ? 'bg-cyan-500/15 border border-cyan-500/30'
                  : 'hover:bg-gray-800 border border-transparent'
              }`}
            >
              <span className="text-base flex-shrink-0">{TYPE_ICONS[f.type]}</span>
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium truncate ${TYPE_COLORS[f.type]}`}>
                  {f.displayName}
                </div>
                <div className="text-xs text-gray-600">{f.lines} lines</div>
              </div>
              {selected === f.path && (
                <span className="text-cyan-400 text-xs">→</span>
              )}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}

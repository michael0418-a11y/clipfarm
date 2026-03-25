'use client'
import type { PipelineStep } from '@/lib/generator/types'

const icons: Record<string, string> = {
  analyze: '🔍', config: '⚙️', data: '💾', server: '🖥️',
  client: '🎮', rojo: '🔗', package: '📦',
}

export function PipelineProgress({ steps }: { steps: PipelineStep[] }) {
  return (
    <div className="space-y-2">
      {steps.map((step, i) => (
        <div key={step.id} className="flex items-center gap-3 animate-slide-in" style={{ animationDelay: `${i * 0.05}s` }}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 flex-shrink-0 transition-all duration-300 ${
            step.status === 'done'    ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400' :
            step.status === 'running' ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 animate-pulse' :
            step.status === 'error'   ? 'bg-red-500/20 border-red-500 text-red-400' :
            'bg-gray-800 border-gray-700 text-gray-600'
          }`}>
            {step.status === 'done'    ? '✓' :
             step.status === 'running' ? <span className="animate-spin">◌</span> :
             step.status === 'error'   ? '✗' :
             icons[step.id] || '○'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className={`text-sm font-medium ${
                step.status === 'done'    ? 'text-white' :
                step.status === 'running' ? 'text-cyan-300' :
                step.status === 'error'   ? 'text-red-400' :
                'text-gray-500'
              }`}>{step.label}</span>
              {step.durationMs && (
                <span className="text-xs text-gray-600">{(step.durationMs / 1000).toFixed(1)}s</span>
              )}
            </div>
            <p className="text-xs text-gray-600 truncate">{step.description}</p>
            {step.files.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {step.files.slice(0, 4).map(f => (
                  <span key={f} className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
                    {f.split('/').pop()}
                  </span>
                ))}
                {step.files.length > 4 && (
                  <span className="text-xs text-gray-600">+{step.files.length - 4} more</span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

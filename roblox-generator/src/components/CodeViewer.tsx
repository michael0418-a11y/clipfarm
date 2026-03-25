'use client'
import { useState } from 'react'
import type { GeneratedFile } from '@/lib/generator/types'

interface Props {
  file: GeneratedFile | null
}

const TYPE_BADGE: Record<string, { label: string; color: string }> = {
  server: { label: 'Server',  color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  client: { label: 'Client',  color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  module: { label: 'Module',  color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  config: { label: 'Config',  color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
}

export function CodeViewer({ file }: Props) {
  const [copied, setCopied] = useState(false)

  if (!file) {
    return (
      <div className="h-full flex items-center justify-center text-gray-600">
        <div className="text-center">
          <div className="text-4xl mb-3">📄</div>
          <p className="text-sm">Select a file to preview</p>
        </div>
      </div>
    )
  }

  async function copyToClipboard() {
    await navigator.clipboard.writeText(file!.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const badge = TYPE_BADGE[file.type]
  const lines = file.content.split('\n')

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`text-xs px-2 py-0.5 rounded border font-medium ${badge.color}`}>
            {badge.label}
          </span>
          <span className="text-sm text-white font-mono truncate">{file.path}</span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-gray-500">{file.lines} lines</span>
          <button
            onClick={copyToClipboard}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors border border-gray-700"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Code */}
      <div className="flex-1 overflow-auto">
        <div className="flex min-h-full">
          {/* Line numbers */}
          <div className="select-none flex-shrink-0 text-right pr-4 pl-4 pt-4 text-xs text-gray-700 font-mono leading-5 bg-gray-900/50">
            {lines.map((_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>
          {/* Code content */}
          <pre className="flex-1 overflow-x-auto pt-4 pb-4 pr-4 text-xs font-mono leading-5 text-gray-300 whitespace-pre">
            <LuaHighlight code={file.content} />
          </pre>
        </div>
      </div>
    </div>
  )
}

// Simple Lua syntax highlighter (no deps)
function LuaHighlight({ code }: { code: string }) {
  const lines = code.split('\n').map((line, i) => (
    <div key={i}><HighlightLine line={line} /></div>
  ))
  return <>{lines}</>
}

function HighlightLine({ line }: { line: string }) {
  // Comment
  if (/^\s*--/.test(line)) {
    return <span className="text-gray-500 italic">{line}</span>
  }
  // Simple token coloring via regex replace
  const html = line
    .replace(/\b(local|function|return|end|if|then|else|elseif|for|while|do|repeat|until|in|not|and|or|true|false|nil|break|continue)\b/g,
      '<kw>$1</kw>')
    .replace(/"([^"]*)"/g, '<str>"$1"</str>')
    .replace(/'([^']*)'/g, '<str>\'$1\'</str>')
    .replace(/\b(\d+\.?\d*)\b/g, '<num>$1</num>')
    .replace(/--.*/g, '<cmt>$&</cmt>')

  return <span dangerouslySetInnerHTML={{ __html: colorize(html) }} />
}

function colorize(html: string) {
  return html
    .replace(/<kw>(.*?)<\/kw>/g, '<span style="color:#c792ea">$1</span>')
    .replace(/<str>(.*?)<\/str>/g, '<span style="color:#c3e88d">$1</span>')
    .replace(/<num>(.*?)<\/num>/g, '<span style="color:#f78c6c">$1</span>')
    .replace(/<cmt>(.*?)<\/cmt>/g, '<span style="color:#546e7a;font-style:italic">$1</span>')
}

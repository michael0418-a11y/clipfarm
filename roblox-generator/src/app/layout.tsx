import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Roblox AI Game Generator',
  description: 'Describe your game — AI builds every script automatically.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0a0e1a] text-white antialiased min-h-screen">
        {children}
      </body>
    </html>
  )
}

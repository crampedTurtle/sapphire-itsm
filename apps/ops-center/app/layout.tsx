import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Sapphire Ops Center',
  description: 'Risk and escalation control plane',
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
    >
      {children}
    </Link>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <div className="flex-shrink-0 flex items-center">
                    <h1 className="text-xl font-bold text-gray-900">Sapphire Ops Center</h1>
                  </div>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <NavLink href="/">Dashboard</NavLink>
                    <NavLink href="/cases">Cases</NavLink>
                    <NavLink href="/alerts">Alerts</NavLink>
                    <NavLink href="/metrics">Metrics</NavLink>
                    <div className="relative group">
                      <NavLink href="/kb-review">Knowledge Base</NavLink>
                      <div className="absolute left-0 mt-1 w-48 bg-white rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10 border border-gray-200">
                        <Link href="/kb-review" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                          Review Queue
                        </Link>
                      </div>
                    </div>
                    <div className="relative group">
                      <NavLink href="/ai-training">AI Management</NavLink>
                      <div className="absolute left-0 mt-1 w-48 bg-white rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10 border border-gray-200">
                        <Link href="/ai-training" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                          Training Dataset
                        </Link>
                        <Link href="/ai-logs" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                          AI Logs
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </nav>
          <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}


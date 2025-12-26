'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { KBReviewQueueTable } from '@/components/kb/KBReviewQueueTable'
import { useKBReviewQueue } from '@/hooks/useKBReviewQueue'
import { kbApi } from '@/lib/api'
import { Search, Filter, RefreshCw } from 'lucide-react'

export default function KBReviewPage() {
  const { items, loading, error, refetch, removeItem } = useKBReviewQueue()
  const [searchQuery, setSearchQuery] = useState('')
  const [tagFilter, setTagFilter] = useState<string>('')
  const [scoreThreshold, setScoreThreshold] = useState<string>('')
  const [dateRange, setDateRange] = useState<string>('')

  // Get unique tags from items
  const allTags = useMemo(() => {
    const tags = new Set<string>()
    items.forEach(item => {
      item.tags?.forEach(tag => tags.add(tag))
    })
    return Array.from(tags).sort()
  }, [items])

  // Filter items
  const filteredItems = useMemo(() => {
    let filtered = [...items]

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(query) ||
        item.tags?.some(tag => tag.toLowerCase().includes(query))
      )
    }

    // Tag filter
    if (tagFilter) {
      filtered = filtered.filter(item =>
        item.tags?.includes(tagFilter)
      )
    }

    // Score threshold filter
    if (scoreThreshold) {
      const threshold = parseFloat(scoreThreshold)
      filtered = filtered.filter(item => item.overall_score >= threshold)
    }

    // Date range filter (simplified - can be enhanced)
    if (dateRange) {
      const days = parseInt(dateRange)
      const cutoffDate = new Date()
      cutoffDate.setDate(cutoffDate.getDate() - days)
      filtered = filtered.filter(item => {
        const itemDate = new Date(item.created_at)
        return itemDate >= cutoffDate
      })
    }

    // Sort by overall_score ASC (lowest first)
    filtered.sort((a, b) => a.overall_score - b.overall_score)

    return filtered
  }, [items, searchQuery, tagFilter, scoreThreshold, dateRange])

  const handleApprove = async (documentId: string, publish: boolean = false) => {
    try {
      // Get current user (in production, get from auth context)
      const reviewedBy = 'ops-user' // TODO: Get from auth context
      await kbApi.approveArticle(documentId, reviewedBy, undefined, publish)
      removeItem(documentId)
    } catch (error) {
      console.error('Error approving article:', error)
      alert('Failed to approve article. Please try again.')
    }
  }

  const handleReject = async (documentId: string, reason: string) => {
    try {
      const reviewedBy = 'ops-user' // TODO: Get from auth context
      await kbApi.rejectArticle(documentId, reviewedBy, reason, true)
      removeItem(documentId)
    } catch (error) {
      console.error('Error rejecting article:', error)
      alert('Failed to reject article. Please try again.')
    }
  }

  const handleViewArticle = (documentId: string) => {
    // Open Outline document in new tab
    // TODO: Get Outline URL from config or API
    const outlineUrl = process.env.NEXT_PUBLIC_OUTLINE_URL || 'https://outline.home.lan'
    window.open(`${outlineUrl}/doc/${documentId}`, '_blank')
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Card>
          <CardContent className="p-8">
            <div className="flex items-center justify-center">
              <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
              <span className="ml-2 text-gray-500">Loading review queue...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Card>
          <CardContent className="p-8">
            <div className="text-center text-red-600">
              <p className="font-semibold">Error loading review queue</p>
              <p className="text-sm mt-2">{error}</p>
              <Button onClick={refetch} variant="outline" className="mt-4">
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">KB Review Queue</h1>
          <p className="text-gray-500 mt-1">
            Review and approve auto-generated knowledge base articles
          </p>
        </div>
        <Button onClick={refetch} variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search title or tags..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0A2540]"
              />
            </div>

            {/* Tag Filter */}
            <select
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0A2540]"
            >
              <option value="">All Tags</option>
              {allTags.map(tag => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </select>

            {/* Score Threshold */}
            <select
              value={scoreThreshold}
              onChange={(e) => setScoreThreshold(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0A2540]"
            >
              <option value="">All Scores</option>
              <option value="6.5">Score ≥ 6.5</option>
              <option value="7.0">Score ≥ 7.0</option>
              <option value="7.5">Score ≥ 7.5</option>
              <option value="8.0">Score ≥ 8.0</option>
            </select>

            {/* Date Range */}
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0A2540]"
            >
              <option value="">All Time</option>
              <option value="1">Last 24 hours</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Results Count */}
      <div className="text-sm text-gray-600">
        Showing {filteredItems.length} of {items.length} articles
      </div>

      {/* Table */}
      <KBReviewQueueTable
        items={filteredItems}
        onApprove={handleApprove}
        onReject={handleReject}
        onViewArticle={handleViewArticle}
      />
    </div>
  )
}


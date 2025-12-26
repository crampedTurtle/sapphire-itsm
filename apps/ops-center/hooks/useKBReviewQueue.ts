'use client'

import { useState, useEffect } from 'react'
import { kbApi } from '@/lib/api'

export interface KBReviewItem {
  outline_document_id: string
  title: string
  overall_score: number
  clarity_score: number
  completeness_score: number
  technical_accuracy_score: number
  structure_score: number
  needs_review: boolean
  reason?: string
  created_at: string
  quality_score_id: string
  tags?: string[]
  updated_at?: string
}

export function useKBReviewQueue() {
  const [items, setItems] = useState<KBReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchReviewQueue = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await kbApi.getReviewQueue()
      setItems(response.items)
    } catch (err: any) {
      setError(err.message || 'Failed to load review queue')
      console.error('Error fetching review queue:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReviewQueue()
  }, [])

  const removeItem = (documentId: string) => {
    setItems(prev => prev.filter(item => item.outline_document_id !== documentId))
  }

  return {
    items,
    loading,
    error,
    refetch: fetchReviewQueue,
    removeItem,
  }
}


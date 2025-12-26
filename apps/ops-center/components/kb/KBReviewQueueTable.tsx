'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { KBReviewItem } from '@/hooks/useKBReviewQueue'
import { CheckCircle, XCircle, ExternalLink, Star } from 'lucide-react'

interface KBReviewQueueTableProps {
  items: KBReviewItem[]
  onApprove: (documentId: string, publish?: boolean) => Promise<void>
  onReject: (documentId: string, reason: string) => Promise<void>
  onViewArticle: (documentId: string) => void
}

export function KBReviewQueueTable({
  items,
  onApprove,
  onReject,
  onViewArticle,
}: KBReviewQueueTableProps) {
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [approvingId, setApprovingId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [publishDocumentId, setPublishDocumentId] = useState<string | null>(null)

  const handleRejectClick = (documentId: string) => {
    setRejectingId(documentId)
    setRejectReason('')
    setShowRejectModal(true)
  }

  const handleRejectSubmit = async () => {
    if (!rejectingId || !rejectReason.trim()) return
    await onReject(rejectingId, rejectReason)
    setShowRejectModal(false)
    setRejectingId(null)
    setRejectReason('')
  }

  const handleApproveClick = async (documentId: string, publish: boolean = false) => {
    if (publish) {
      setPublishDocumentId(documentId)
      setShowPublishModal(true)
    } else {
      setApprovingId(documentId)
      await onApprove(documentId, false)
      setApprovingId(null)
    }
  }

  const handlePublishConfirm = async () => {
    if (!publishDocumentId) return
    setApprovingId(publishDocumentId)
    await onApprove(publishDocumentId, true)
    setShowPublishModal(false)
    setPublishDocumentId(null)
    setApprovingId(null)
  }

  const getRowBackgroundColor = (score: number) => {
    if (score < 6.5) return 'bg-red-50/50'
    if (score < 7.5) return 'bg-yellow-50/50'
    return 'bg-white'
  }

  const getStatusBadge = (needsReview: boolean) => {
    if (needsReview) {
      return <Badge variant="destructive">Needs Review</Badge>
    }
    return <Badge className="bg-yellow-100 text-yellow-800">Draft</Badge>
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-gray-500">
          No articles in review queue. All articles have been reviewed or approved.
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Article
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Scores
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tags
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created/Updated
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {items.map((item) => (
                  <tr
                    key={item.outline_document_id}
                    className={`hover:bg-gray-50 transition-colors ${getRowBackgroundColor(item.overall_score)}`}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <button
                          onClick={() => onViewArticle(item.outline_document_id)}
                          className="text-sm font-medium text-[#0A2540] hover:text-[#0d3252] hover:underline flex items-center gap-1"
                        >
                          {item.title}
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">
                        <div className="flex items-center gap-1 mb-1">
                          <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                          <span className="font-semibold">{item.overall_score.toFixed(1)}</span>
                          <span className="text-gray-500">overall</span>
                        </div>
                        <div className="text-xs text-gray-600 space-x-2">
                          <span>Clarity: {item.clarity_score}</span>
                          <span>•</span>
                          <span>Completeness: {item.completeness_score}</span>
                          <span>•</span>
                          <span>Accuracy: {item.technical_accuracy_score}</span>
                          <span>•</span>
                          <span>Structure: {item.structure_score}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {item.tags && item.tags.length > 0 ? (
                          item.tags.map((tag, idx) => (
                            <Badge
                              key={idx}
                              className="bg-gray-200 text-gray-700 text-xs px-2 py-0.5 rounded-full"
                            >
                              {tag}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400">No tags</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(item.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(item.needs_review)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleApproveClick(item.outline_document_id, false)}
                          disabled={approvingId === item.outline_document_id}
                          className="text-xs"
                        >
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleApproveClick(item.outline_document_id, true)}
                          disabled={approvingId === item.outline_document_id}
                          className="text-xs bg-[#0A2540] hover:bg-[#0d3252]"
                        >
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Approve & Publish
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRejectClick(item.outline_document_id)}
                          disabled={rejectingId === item.outline_document_id}
                          className="text-xs"
                        >
                          <XCircle className="w-3 h-3 mr-1" />
                          Reject
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Reject Modal */}
      {showRejectModal && rejectingId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full">
            <CardHeader>
              <CardTitle>Reject Article</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Why is this being rejected?
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Enter rejection reason..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#0A2540]"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowRejectModal(false)
                    setRejectingId(null)
                    setRejectReason('')
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleRejectSubmit}
                  disabled={!rejectReason.trim()}
                >
                  Reject
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Publish Confirmation Modal */}
      {showPublishModal && publishDocumentId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full">
            <CardHeader>
              <CardTitle>Publish Article</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-gray-600">
                Are you sure you want to approve and publish this article? It will be made publicly available in the knowledge base.
              </p>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowPublishModal(false)
                    setPublishDocumentId(null)
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  onClick={handlePublishConfirm}
                  disabled={approvingId === publishDocumentId}
                  className="bg-[#0A2540] hover:bg-[#0d3252]"
                >
                  {approvingId === publishDocumentId ? 'Publishing...' : 'Publish'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  )
}


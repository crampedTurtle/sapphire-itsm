'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { opsApi } from "@/lib/api"
import { CheckCircle2, XCircle, AlertCircle, Brain, MessageSquare } from "lucide-react"
import Link from "next/link"

export default function AILogsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    resolved: undefined as boolean | undefined,
    helpful: undefined as boolean | undefined,
    min_confidence: undefined as number | undefined,
    used_in_training: undefined as boolean | undefined,
    limit: 50,
    offset: 0,
  })

  useEffect(() => {
    loadLogs()
  }, [filters.offset])

  async function loadLogs() {
    setLoading(true)
    try {
      const data = await opsApi.getAILogs(filters)
      setLogs(data.logs)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Error loading AI logs:', error)
      alert(`Error loading AI logs: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  function handleFilterChange(key: string, value: any) {
    setFilters({ ...filters, [key]: value, offset: 0 })
  }

  useEffect(() => {
    loadLogs()
  }, [filters.resolved, filters.helpful, filters.min_confidence, filters.used_in_training])

  if (loading && logs.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Support AI Logs</h1>
          <p className="mt-1 text-sm text-gray-500">View and analyze AI resolution attempts</p>
        </div>
        <div className="text-center py-8">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Support AI Logs</h1>
          <p className="mt-1 text-sm text-gray-500">View and analyze AI resolution attempts</p>
        </div>
        <Button onClick={loadLogs} variant="outline">
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Resolved
              </label>
              <select
                value={filters.resolved === undefined ? '' : String(filters.resolved)}
                onChange={(e) => handleFilterChange('resolved', e.target.value === '' ? undefined : e.target.value === 'true')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Helpful
              </label>
              <select
                value={filters.helpful === undefined ? '' : String(filters.helpful)}
                onChange={(e) => handleFilterChange('helpful', e.target.value === '' ? undefined : e.target.value === 'true')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Confidence
              </label>
              <input
                type="number"
                step="0.01"
                value={filters.min_confidence || ''}
                onChange={(e) => handleFilterChange('min_confidence', e.target.value ? parseFloat(e.target.value) : undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                min="0"
                max="1"
                placeholder="0.0 - 1.0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Used in Training
              </label>
              <select
                value={filters.used_in_training === undefined ? '' : String(filters.used_in_training)}
                onChange={(e) => handleFilterChange('used_in_training', e.target.value === '' ? undefined : e.target.value === 'true')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{total}</div>
            <div className="text-sm text-gray-500">Total Logs</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">
              {logs.filter(l => l.resolved).length}
            </div>
            <div className="text-sm text-gray-500">Resolved</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">
              {logs.filter(l => l.helpful === true).length}
            </div>
            <div className="text-sm text-gray-500">Marked Helpful</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">
              {logs.length > 0
                ? (logs.reduce((sum, l) => sum + l.confidence, 0) / logs.length * 100).toFixed(1)
                : 0}%
            </div>
            <div className="text-sm text-gray-500">Avg Confidence</div>
          </CardContent>
        </Card>
      </div>

      {/* Logs List */}
      <Card>
        <CardHeader>
          <CardTitle>AI Logs ({total})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {logs.map((log) => (
              <div key={log.id} className="p-4 border rounded-lg hover:bg-gray-50">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <MessageSquare className="h-4 w-4 text-gray-400" />
                      <span className="font-mono text-xs text-gray-500">{log.id.slice(0, 8)}</span>
                      {log.subject && (
                        <span className="font-medium text-gray-900">{log.subject}</span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      <div className="font-medium mb-1">User Message:</div>
                      <div className="pl-2 border-l-2 border-gray-200">
                        {log.message.substring(0, 200)}{log.message.length > 200 ? '...' : ''}
                      </div>
                    </div>
                    <div className="text-sm text-gray-600">
                      <div className="font-medium mb-1">AI Answer:</div>
                      <div className="pl-2 border-l-2 border-blue-200 bg-blue-50 rounded p-2">
                        {log.ai_answer.substring(0, 300)}{log.ai_answer.length > 300 ? '...' : ''}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 ml-4">
                    <div className="flex items-center gap-2">
                      {log.resolved && (
                        <CheckCircle2 className="h-5 w-5 text-green-500" title="Resolved" />
                      )}
                      {log.escalation_triggered && (
                        <AlertCircle className="h-5 w-5 text-orange-500" title="Escalated" />
                      )}
                      {log.helpful === true && (
                        <CheckCircle2 className="h-5 w-5 text-blue-500" title="Marked as helpful" />
                      )}
                      {log.helpful === false && (
                        <XCircle className="h-5 w-5 text-red-500" title="Marked as not helpful" />
                      )}
                      {log.used_in_training && (
                        <Brain className="h-5 w-5 text-purple-500" title="Used in training" />
                      )}
                    </div>
                    <Badge variant={log.confidence >= 0.75 ? 'default' : log.confidence >= 0.5 ? 'secondary' : 'destructive'}>
                      {(log.confidence * 100).toFixed(0)}%
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 mt-2">
                  <span>Model: {log.model_used}</span>
                  {log.tier !== null && <span>Tier: {log.tier}</span>}
                  {log.attempt_number > 1 && <span>Attempt: {log.attempt_number}</span>}
                  {log.case_id && (
                    <Link href={`/cases/${log.case_id}`} className="text-blue-600 hover:underline">
                      Case: {log.case_id.slice(0, 8)}
                    </Link>
                  )}
                  {log.kb_document_id && (
                    <span className="text-blue-600">KB: {log.kb_document_id}</span>
                  )}
                  <span>{new Date(log.created_at).toLocaleString()}</span>
                </div>
                {log.citations && Array.isArray(log.citations) && log.citations.length > 0 && (
                  <div className="mt-2 text-xs text-gray-500">
                    Citations: {log.citations.length}
                  </div>
                )}
                {log.user_feedback && (
                  <div className="mt-2 text-xs text-gray-600 bg-yellow-50 p-2 rounded">
                    <strong>Feedback:</strong> {log.user_feedback}
                  </div>
                )}
              </div>
            ))}
          </div>
          {logs.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Brain className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No AI logs found with current filters.</p>
            </div>
          )}
          {total > filters.limit && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <div className="text-sm text-gray-500">
                Showing {filters.offset + 1}-{Math.min(filters.offset + filters.limit, total)} of {total}
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - filters.limit) })}
                  disabled={filters.offset === 0}
                  variant="outline"
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setFilters({ ...filters, offset: filters.offset + filters.limit })}
                  disabled={filters.offset + filters.limit >= total}
                  variant="outline"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}


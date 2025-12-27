'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { aiApi } from "@/lib/api"
import { Download, CheckCircle2, XCircle, Brain } from "lucide-react"

export default function AITrainingPage() {
  const [dataset, setDataset] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [filters, setFilters] = useState({
    limit: 500,
    min_confidence: 0.75,
    min_quality_score: 7,
  })

  useEffect(() => {
    loadDataset()
  }, [])

  async function loadDataset() {
    setLoading(true)
    try {
      const data = await aiApi.getTrainingDataset(filters)
      setDataset(data)
    } catch (error: any) {
      console.error('Error loading dataset:', error)
      alert(`Error loading dataset: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleExport() {
    setExporting(true)
    try {
      const data = await aiApi.getTrainingDataset(filters)
      
      // Create downloadable JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `training-dataset-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error: any) {
      console.error('Error exporting dataset:', error)
      alert(`Error exporting dataset: ${error.message}`)
    } finally {
      setExporting(false)
    }
  }

  async function handleMarkUsed() {
    if (!dataset || dataset.examples.length === 0) return
    
    // In a real implementation, we'd need log IDs from the examples
    // For now, this is a placeholder
    alert('Mark as used functionality requires log IDs from the backend')
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Training Dataset</h1>
          <p className="mt-1 text-sm text-gray-500">Export high-quality resolved cases for model fine-tuning</p>
        </div>
        <div className="text-center py-8">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Training Dataset</h1>
          <p className="mt-1 text-sm text-gray-500">Export high-quality resolved cases for model fine-tuning</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadDataset} variant="outline">
            Refresh
          </Button>
          <Button onClick={handleExport} disabled={exporting || !dataset || dataset.count === 0}>
            <Download className="h-4 w-4 mr-2" />
            {exporting ? 'Exporting...' : 'Export JSON'}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Examples
              </label>
              <input
                type="number"
                value={filters.limit}
                onChange={(e) => setFilters({ ...filters, limit: parseInt(e.target.value) || 500 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                min="1"
                max="1000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Confidence
              </label>
              <input
                type="number"
                step="0.01"
                value={filters.min_confidence}
                onChange={(e) => setFilters({ ...filters, min_confidence: parseFloat(e.target.value) || 0.75 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                min="0"
                max="1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Quality Score
              </label>
              <input
                type="number"
                value={filters.min_quality_score}
                onChange={(e) => setFilters({ ...filters, min_quality_score: parseInt(e.target.value) || 7 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                min="1"
                max="10"
              />
            </div>
          </div>
          <Button onClick={loadDataset} className="mt-4" variant="outline">
            Apply Filters
          </Button>
        </CardContent>
      </Card>

      {/* Dataset Summary */}
      {dataset && (
        <Card>
          <CardHeader>
            <CardTitle>Dataset Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <div className="text-2xl font-bold">{dataset.count}</div>
                <div className="text-sm text-gray-500">Total Examples</div>
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {dataset.examples.filter((e: any) => e.helpful === true).length}
                </div>
                <div className="text-sm text-gray-500">Marked Helpful</div>
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {dataset.examples.filter((e: any) => e.kb_document_id).length}
                </div>
                <div className="text-sm text-gray-500">With KB Articles</div>
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {dataset.examples.length > 0
                    ? (dataset.examples.reduce((sum: number, e: any) => sum + e.confidence, 0) / dataset.examples.length * 100).toFixed(1)
                    : 0}%
                </div>
                <div className="text-sm text-gray-500">Avg Confidence</div>
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500">
              Exported at: {new Date(dataset.exported_at).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Examples List */}
      {dataset && dataset.examples.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Training Examples ({dataset.examples.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {dataset.examples.map((example: any, idx: number) => (
                <div key={idx} className="p-4 border rounded-lg">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{example.issue_title}</div>
                      <div className="text-sm text-gray-500 mt-1">{example.problem_description.substring(0, 150)}...</div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {example.helpful === true && (
                        <CheckCircle2 className="h-5 w-5 text-green-500" title="Marked as helpful" />
                      )}
                      {example.helpful === false && (
                        <XCircle className="h-5 w-5 text-red-500" title="Marked as not helpful" />
                      )}
                      <div className="text-sm font-medium">
                        {(example.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-gray-600">
                    <div className="font-medium mb-1">Answer:</div>
                    <div className="pl-2 border-l-2 border-gray-200">
                      {example.final_answer.substring(0, 200)}...
                    </div>
                  </div>
                  {example.citations && example.citations.length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      Citations: {example.citations.length}
                    </div>
                  )}
                  {example.kb_document_id && (
                    <div className="mt-2 text-xs text-blue-600">
                      KB Article: {example.kb_document_id}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {dataset && dataset.examples.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            <Brain className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No training examples found with current filters.</p>
            <p className="text-sm mt-2">Try adjusting the filters above.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}


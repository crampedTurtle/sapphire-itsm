'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RiskBadge } from "@/components/badges/risk-badge"
import { opsApi } from "@/lib/api"
import type { CaseDetail, AuditEvent } from "@/lib/types"
import { AlertTriangle, Clock, User, FileText, History } from "lucide-react"

export default function CaseDetailPage() {
  const params = useParams()
  const router = useRouter()
  const caseId = params.id as string
  
  const [caseData, setCaseData] = useState<CaseDetail | null>(null)
  const [auditTrail, setAuditTrail] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [updates, setUpdates] = useState({
    status: '',
    priority: '',
    internal_notes: '',
  })
  const [showBreakGlass, setShowBreakGlass] = useState(false)
  const [breakGlassReason, setBreakGlassReason] = useState('')

  useEffect(() => {
    if (caseId) {
      loadCaseData()
    }
  }, [caseId])

  async function loadCaseData() {
    setLoading(true)
    try {
      const [caseRes, auditRes] = await Promise.all([
        opsApi.getCase(caseId),
        opsApi.getCaseAudit(caseId),
      ])
      setCaseData(caseRes)
      setAuditTrail(auditRes)
      setUpdates({
        status: caseRes.status,
        priority: caseRes.priority,
        internal_notes: '',
      })
    } catch (error) {
      console.error('Error loading case:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpdate() {
    try {
      await opsApi.updateCase(caseId, {
        status: updates.status,
        priority: updates.priority,
        internal_notes: updates.internal_notes,
      })
      await loadCaseData()
      alert('Case updated successfully')
    } catch (error) {
      console.error('Error updating case:', error)
      alert('Failed to update case')
    }
  }

  async function handleBreakGlass() {
    if (!breakGlassReason.trim()) {
      alert('Please provide a reason')
      return
    }
    
    try {
      await opsApi.updateCase(caseId, {
        internal_notes: `BREAK GLASS: ${breakGlassReason}`,
      })
      setShowBreakGlass(false)
      setBreakGlassReason('')
      await loadCaseData()
      alert('AI disabled for this case')
    } catch (error) {
      console.error('Error:', error)
      alert('Failed to disable AI')
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading...</div>
  }

  if (!caseData) {
    return <div className="text-center py-8">Case not found</div>
  }

  const slaRemaining = Math.random() * 100 // Mock
  const aiArtifact = caseData.ai_artifacts.find(a => a.artifact_type === 'summary')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{caseData.title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Case ID: <span className="font-mono">{caseData.id}</span>
          </p>
        </div>
        <Button variant="outline" onClick={() => router.back()}>
          Back
        </Button>
      </div>

      {/* Case Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Case Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-500">Status</div>
              <Badge className="mt-1">{caseData.status}</Badge>
            </div>
            <div>
              <div className="text-sm text-gray-500">Priority</div>
              <Badge className="mt-1">{caseData.priority}</Badge>
            </div>
            <div>
              <div className="text-sm text-gray-500">Category</div>
              <div className="mt-1">{caseData.category}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Created</div>
              <div className="mt-1 text-sm">
                {new Date(caseData.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Indicators */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Indicators</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-500" />
                <span>SLA Remaining</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      slaRemaining < 20 ? 'bg-red-500' :
                      slaRemaining < 50 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${slaRemaining}%` }}
                  />
                </div>
                <RiskBadge type="sla" value={slaRemaining / 100} />
              </div>
            </div>
            
            {aiArtifact && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-gray-500" />
                  <span>AI Confidence</span>
                </div>
                <RiskBadge type="confidence" value={aiArtifact.confidence || 0} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* AI Artifacts */}
      {aiArtifact && (
        <Card>
          <CardHeader>
            <CardTitle>AI Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-500 mb-2">Summary</div>
                <p className="text-sm">{aiArtifact.content}</p>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>Model: {aiArtifact.model_used}</span>
                <span>Confidence: {(aiArtifact.confidence || 0) * 100}%</span>
                <span>{new Date(aiArtifact.created_at).toLocaleString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Messages */}
      <Card>
        <CardHeader>
          <CardTitle>Messages ({caseData.messages.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {caseData.messages.map((msg) => (
              <div
                key={msg.id}
                className={`p-4 rounded-lg border ${
                  msg.sender_type === 'customer' ? 'bg-blue-50' :
                  msg.sender_type === 'agent' ? 'bg-green-50' : 'bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span className="font-medium">{msg.sender_email}</span>
                    <Badge variant="outline">{msg.sender_type}</Badge>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(msg.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm whitespace-pre-wrap">{msg.body_text}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Audit Trail */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Trail</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {auditTrail.map((event) => (
              <div key={event.id} className="flex items-start gap-3 p-3 border rounded-lg">
                <History className="h-4 w-4 text-gray-400 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{event.event_type}</span>
                    <span className="text-xs text-gray-500">
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>
                  {Object.keys(event.payload).length > 0 && (
                    <pre className="text-xs text-gray-600 mt-1 bg-gray-50 p-2 rounded">
                      {JSON.stringify(event.payload, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Ops Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Ops Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Status</label>
                <select
                  value={updates.status}
                  onChange={(e) => setUpdates({ ...updates, status: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="new">New</option>
                  <option value="open">Open</option>
                  <option value="pending_customer">Pending Customer</option>
                  <option value="pending_internal">Pending Internal</option>
                  <option value="escalated">Escalated</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Priority</label>
                <select
                  value={updates.priority}
                  onChange={(e) => setUpdates({ ...updates, priority: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Internal Notes</label>
              <textarea
                value={updates.internal_notes}
                onChange={(e) => setUpdates({ ...updates, internal_notes: e.target.value })}
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="Add internal notes..."
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={handleUpdate}>Update Case</Button>
              <Button
                variant="destructive"
                onClick={() => setShowBreakGlass(true)}
              >
                Break Glass (Disable AI)
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Break Glass Modal */}
      {showBreakGlass && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                Break Glass - Disable AI
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                This will disable AI assistance for this case. This action is logged and requires a reason.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Reason *</label>
                  <textarea
                    value={breakGlassReason}
                    onChange={(e) => setBreakGlassReason(e.target.value)}
                    rows={3}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    placeholder="Why are you disabling AI for this case?"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    onClick={handleBreakGlass}
                    disabled={!breakGlassReason.trim()}
                  >
                    Confirm
                  </Button>
                  <Button variant="outline" onClick={() => setShowBreakGlass(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}


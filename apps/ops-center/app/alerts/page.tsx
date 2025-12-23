'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { opsApi } from "@/lib/api"
import type { Alert } from "@/lib/types"
import Link from "next/link"
import { AlertTriangle, Clock, Brain, RefreshCw } from "lucide-react"

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    loadAlerts()
  }, [])

  async function loadAlerts() {
    setLoading(true)
    try {
      const data = await opsApi.getAlerts()
      setAlerts(data)
    } catch (error) {
      console.error('Error loading alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredAlerts = filter === 'all' 
    ? alerts 
    : alerts.filter(a => a.type === filter)

  const slaBreaches = filteredAlerts.filter(a => a.type === 'sla_breach')
  const complianceFlags = filteredAlerts.filter(a => a.type === 'compliance_flag')
  const lowConfidence = filteredAlerts.filter(a => a.type === 'low_confidence')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
          <p className="mt-1 text-sm text-gray-500">Pure signal - no noise</p>
        </div>
        <button
          onClick={loadAlerts}
          className="text-sm text-blue-600 hover:underline"
        >
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${
            filter === 'all' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'
          }`}
        >
          All ({alerts.length})
        </button>
        <button
          onClick={() => setFilter('sla_breach')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${
            filter === 'sla_breach' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'
          }`}
        >
          SLA Breach ({slaBreaches.length})
        </button>
        <button
          onClick={() => setFilter('compliance_flag')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${
            filter === 'compliance_flag' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'
          }`}
        >
          Compliance ({complianceFlags.length})
        </button>
        <button
          onClick={() => setFilter('low_confidence')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${
            filter === 'low_confidence' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'
          }`}
        >
          Low Confidence ({lowConfidence.length})
        </button>
      </div>

      {/* SLA Breach Imminent */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-red-600" />
            SLA Breach Imminent
          </CardTitle>
        </CardHeader>
        <CardContent>
          {slaBreaches.length === 0 ? (
            <p className="text-sm text-gray-500">No SLA breaches</p>
          ) : (
            <div className="space-y-3">
              {slaBreaches.map((alert, idx) => (
                <div key={idx} className="flex items-start justify-between p-3 border border-red-200 bg-red-50 rounded-lg">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">SLA Breach</Badge>
                      <span className="text-sm font-medium">{alert.severity}</span>
                    </div>
                    {alert.case_id && (
                      <Link
                        href={`/cases/${alert.case_id}`}
                        className="text-sm text-blue-600 hover:underline mt-1 block"
                      >
                        {alert.case_title || alert.case_id.slice(0, 8)}
                      </Link>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Compliance / Legal Risk */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            Compliance / Legal Risk
          </CardTitle>
        </CardHeader>
        <CardContent>
          {complianceFlags.length === 0 ? (
            <p className="text-sm text-gray-500">No compliance flags</p>
          ) : (
            <div className="space-y-3">
              {complianceFlags.map((alert, idx) => (
                <div key={idx} className="flex items-start justify-between p-3 border border-red-200 bg-red-50 rounded-lg">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">Compliance Flag</Badge>
                      <span className="text-sm font-medium">{alert.intent}</span>
                    </div>
                    {alert.case_id && (
                      <Link
                        href={`/cases/${alert.case_id}`}
                        className="text-sm text-blue-600 hover:underline mt-1 block"
                      >
                        {alert.case_title || alert.case_id.slice(0, 8)}
                      </Link>
                    )}
                    {alert.from_email && (
                      <p className="text-sm text-gray-600 mt-1">From: {alert.from_email}</p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Low AI Confidence */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-yellow-600" />
            Low AI Confidence
          </CardTitle>
        </CardHeader>
        <CardContent>
          {lowConfidence.length === 0 ? (
            <p className="text-sm text-gray-500">No low confidence alerts</p>
          ) : (
            <div className="space-y-3">
              {lowConfidence.map((alert, idx) => (
                <div key={idx} className="flex items-start justify-between p-3 border border-yellow-200 bg-yellow-50 rounded-lg">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="warning">Low Confidence</Badge>
                      {alert.confidence !== undefined && (
                        <span className="text-sm font-medium">
                          {(alert.confidence * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    {alert.case_id && (
                      <Link
                        href={`/cases/${alert.case_id}`}
                        className="text-sm text-blue-600 hover:underline mt-1 block"
                      >
                        {alert.case_title || alert.case_id.slice(0, 8)}
                      </Link>
                    )}
                    {alert.intake_event_id && (
                      <p className="text-sm text-gray-600 mt-1">
                        Intake: {alert.intake_event_id.slice(0, 8)}
                      </p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}


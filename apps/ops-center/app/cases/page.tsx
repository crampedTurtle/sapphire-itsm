'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { RiskBadge } from "@/components/badges/risk-badge"
import { opsApi } from "@/lib/api"
import type { Case } from "@/lib/types"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    tier: '',
    compliance_flag: '',
    sla_risk: '',
  })

  useEffect(() => {
    loadCases()
  }, [filters])

  async function loadCases() {
    setLoading(true)
    try {
      const params: any = {}
      if (filters.status) params.status = filters.status
      if (filters.priority) params.priority = filters.priority
      if (filters.tier) params.tier = filters.tier
      if (filters.compliance_flag === 'true') params.compliance_flag = true
      if (filters.sla_risk === 'true') params.sla_risk = true

      const result = await opsApi.getCases({ ...params, limit: 100 })
      setCases(result.cases)
    } catch (error) {
      console.error('Error loading cases:', error)
    } finally {
      setLoading(false)
    }
  }

  const priorityColors = {
    low: 'bg-gray-100 text-gray-800',
    normal: 'bg-blue-100 text-blue-800',
    high: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Case Queue</h1>
        <p className="mt-1 text-sm text-gray-500">Cases requiring ops awareness</p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">All</option>
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
                value={filters.priority}
                onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">All</option>
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Tier</label>
              <select
                value={filters.tier}
                onChange={(e) => setFilters({ ...filters, tier: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">All</option>
                <option value="tier1">Tier 1</option>
                <option value="tier2">Tier 2</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Compliance</label>
              <select
                value={filters.compliance_flag}
                onChange={(e) => setFilters({ ...filters, compliance_flag: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">All</option>
                <option value="true">Flagged</option>
                <option value="false">Not Flagged</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">SLA Risk</label>
              <select
                value={filters.sla_risk}
                onChange={(e) => setFilters({ ...filters, sla_risk: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">All</option>
                <option value="true">At Risk</option>
                <option value="false">Safe</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cases Table */}
      <Card>
        <CardHeader>
          <CardTitle>Cases ({cases.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : cases.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No cases found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Case ID</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Tenant</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Category</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Priority</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">SLA</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Risk</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Last Update</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((caseItem) => {
                    const slaRemaining = Math.random() * 100 // Mock - calculate from SLA events
                    return (
                      <tr key={caseItem.id} className="border-b hover:bg-gray-50">
                        <td className="py-3 px-4">
                          <Link
                            href={`/cases/${caseItem.id}`}
                            className="font-mono text-sm text-blue-600 hover:underline"
                          >
                            {caseItem.id.slice(0, 8)}
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-600">
                          {caseItem.tenant_id.slice(0, 8)}
                        </td>
                        <td className="py-3 px-4 text-sm">{caseItem.category}</td>
                        <td className="py-3 px-4">
                          <Badge className={priorityColors[caseItem.priority]}>
                            {caseItem.priority}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-sm">
                          {slaRemaining.toFixed(0)}%
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex gap-2">
                            <RiskBadge type="sla" value={slaRemaining / 100} showLabel={false} />
                            {caseItem.sla_breached && (
                              <Badge variant="destructive">Breached</Badge>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-500">
                          {new Date(caseItem.updated_at).toLocaleDateString()}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}


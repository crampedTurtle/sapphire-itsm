import { KPICard } from "@/components/kpi/kpi-card"
import { RiskBadge } from "@/components/badges/risk-badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { opsApi } from "@/lib/api"
import { AlertTriangle, Clock, Brain, UserCheck } from "lucide-react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"

async function getDashboardData() {
  const [metrics, alerts, cases] = await Promise.all([
    opsApi.getIntakeMetrics(),
    opsApi.getAlerts(),
    opsApi.getCases({ limit: 10 }),
  ])

  // Calculate SLA risk index
  const slaRiskCases = cases.cases.filter(c => {
    // Mock SLA calculation - in production, calculate from SLA events
    return c.sla_breached || Math.random() < 0.15 // Simulate 15% at risk
  })
  const slaRiskPercent = (slaRiskCases.length / cases.cases.length) * 100

  // Compliance flags
  const complianceFlags = alerts.filter(a => a.type === 'compliance_flag').length

  // AI confidence (mock)
  const aiConfidence = await opsApi.getAIConfidenceMetrics()

  // Human intervention rate (mock - calculate from audit events)
  const interventionRate = 0.12 // 12%

  // At-risk cases
  const atRiskCases = cases.cases.slice(0, 10).map(c => ({
    ...c,
    risk_reason: c.sla_breached ? 'SLA Risk' : 
                 alerts.some(a => a.case_id === c.id && a.type === 'compliance_flag') ? 'Compliance Flag' :
                 alerts.some(a => a.case_id === c.id && a.type === 'low_confidence') ? 'Low AI Confidence' :
                 'Escalated',
    sla_remaining: Math.random() * 100, // Mock
  }))

  return {
    slaRiskPercent,
    complianceFlags,
    aiConfidence,
    interventionRate,
    atRiskCases,
    recentEscalations: alerts.filter(a => a.severity === 'high' || a.severity === 'critical').slice(0, 5),
  }
}

export default async function DashboardPage() {
  const data = await getDashboardData()

  const slaRiskVariant = data.slaRiskPercent < 10 ? 'success' : 
                         data.slaRiskPercent < 20 ? 'warning' : 'danger'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Ops Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Risk and escalation control plane</p>
      </div>

      {/* KPI Widgets */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="SLA Risk Index"
          value={`${data.slaRiskPercent.toFixed(1)}%`}
          subtitle="Cases within 20% of breach"
          variant={slaRiskVariant}
          icon={<Clock className="h-4 w-4 text-muted-foreground" />}
        />
        <KPICard
          title="Compliance Flags"
          value={data.complianceFlags}
          subtitle="Open cases requiring review"
          variant={data.complianceFlags > 0 ? 'danger' : 'success'}
          icon={<AlertTriangle className="h-4 w-4 text-muted-foreground" />}
        />
        <KPICard
          title="AI Confidence Health"
          value={`${(data.aiConfidence.rolling_average * 100).toFixed(1)}%`}
          subtitle={`${data.aiConfidence.sample_size} samples`}
          trend={data.aiConfidence.trend}
          icon={<Brain className="h-4 w-4 text-muted-foreground" />}
        />
        <KPICard
          title="Human Intervention Rate"
          value={`${(data.interventionRate * 100).toFixed(1)}%`}
          subtitle="Last 24 hours"
          icon={<UserCheck className="h-4 w-4 text-muted-foreground" />}
        />
      </div>

      {/* At-Risk Cases */}
      <Card>
        <CardHeader>
          <CardTitle>At-Risk Cases</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data.atRiskCases.map((caseItem) => (
              <Link
                key={caseItem.id}
                href={`/cases/${caseItem.id}`}
                className="block p-4 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm text-gray-500">
                        {caseItem.id.slice(0, 8)}
                      </span>
                      <span className="font-medium">{caseItem.title}</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
                      <span>Tenant: {caseItem.tenant_id.slice(0, 8)}</span>
                      <span>•</span>
                      <span>Priority: {caseItem.priority}</span>
                      <span>•</span>
                      <span>SLA: {caseItem.sla_remaining.toFixed(0)}% remaining</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="danger">{caseItem.risk_reason}</Badge>
                    <RiskBadge type="sla" value={caseItem.sla_remaining / 100} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Escalations */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Escalations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data.recentEscalations.length === 0 ? (
              <p className="text-sm text-gray-500">No recent escalations</p>
            ) : (
              data.recentEscalations.map((alert, idx) => (
                <div key={idx} className="flex items-start justify-between p-3 border rounded-lg">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{alert.type}</span>
                      <Badge variant={alert.severity === 'critical' ? 'destructive' : 'warning'}>
                        {alert.severity}
                      </Badge>
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
                  <span className="text-xs text-gray-400">
                    {alert.type === 'sla_breach' ? 'System' : 'System'}
                  </span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


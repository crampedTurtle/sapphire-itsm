import { Badge } from "@/components/ui/badge"
import { getSLARiskLevel, getConfidenceLevel } from "@/lib/thresholds"

interface RiskBadgeProps {
  type: 'sla' | 'confidence' | 'compliance'
  value: number | boolean
  showLabel?: boolean
}

export function RiskBadge({ type, value, showLabel = true }: RiskBadgeProps) {
  if (type === 'compliance') {
    if (value) {
      return <Badge variant="danger">Compliance Risk</Badge>
    }
    return null
  }

  if (type === 'sla') {
    const level = getSLARiskLevel(value as number)
    const labels = {
      low: 'Low Risk',
      medium: 'Medium Risk',
      high: 'High Risk',
      critical: 'Breached',
    }
    const variants = {
      low: 'success' as const,
      medium: 'warning' as const,
      high: 'danger' as const,
      critical: 'destructive' as const,
    }
    return (
      <Badge variant={variants[level]}>
        {showLabel ? labels[level] : `${(value as number * 100).toFixed(0)}%`}
      </Badge>
    )
  }

  if (type === 'confidence') {
    const level = getConfidenceLevel(value as number)
    const labels = {
      low: 'Low Confidence',
      medium: 'Medium Confidence',
      high: 'High Confidence',
    }
    const variants = {
      low: 'danger' as const,
      medium: 'warning' as const,
      high: 'success' as const,
    }
    return (
      <Badge variant={variants[level]}>
        {showLabel ? labels[level] : `${((value as number) * 100).toFixed(0)}%`}
      </Badge>
    )
  }

  return null
}


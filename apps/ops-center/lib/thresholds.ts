/**
 * Risk and confidence threshold utilities
 */

/**
 * Get SLA risk level based on remaining percentage (0-1)
 * - 0.8-1.0: Low risk (20%+ remaining)
 * - 0.5-0.8: Medium risk (20-50% remaining)
 * - 0.2-0.5: High risk (50-80% remaining)
 * - 0-0.2: Critical/Breached (<20% remaining or breached)
 */
export function getSLARiskLevel(remaining: number): 'low' | 'medium' | 'high' | 'critical' {
  if (remaining >= 0.8) return 'low'
  if (remaining >= 0.5) return 'medium'
  if (remaining >= 0.2) return 'high'
  return 'critical'
}

/**
 * Get confidence level based on confidence score (0-1)
 * - 0.8-1.0: High confidence
 * - 0.5-0.8: Medium confidence
 * - 0-0.5: Low confidence
 */
export function getConfidenceLevel(confidence: number): 'low' | 'medium' | 'high' {
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}


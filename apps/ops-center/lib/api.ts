/**
 * Ops Center API client
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}/v1/ops${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`)
  }

  return response.json()
}

export const opsApi = {
  /**
   * Get intake metrics
   */
  async getIntakeMetrics() {
    return apiRequest<{
      time_window: { start: string; end: string }
      total_intake: number
      by_intent: Record<string, number>
      distribution: Record<string, number>
    }>('/metrics/intake')
  },

  /**
   * Get alerts (SLA breaches, compliance flags, low confidence)
   */
  async getAlerts() {
    const response = await apiRequest<{ alerts: any[] }>('/alerts')
    return response.alerts
  },

  /**
   * Get cases with filters
   */
  async getCases(params: {
    status?: string
    priority?: string
    tier?: string
    tenant_id?: string
    compliance_flag?: boolean
    sla_risk?: boolean
    limit?: number
    offset?: number
  } = {}) {
    const queryParams = new URLSearchParams()
    if (params.status) queryParams.append('status', params.status)
    if (params.priority) queryParams.append('priority', params.priority)
    if (params.tier) queryParams.append('tier', params.tier)
    if (params.tenant_id) queryParams.append('tenant_id', params.tenant_id)
    if (params.compliance_flag !== undefined) queryParams.append('compliance_flag', String(params.compliance_flag))
    if (params.sla_risk !== undefined) queryParams.append('sla_risk', String(params.sla_risk))
    if (params.limit) queryParams.append('limit', String(params.limit))
    if (params.offset) queryParams.append('offset', String(params.offset))

    const query = queryParams.toString()
    return apiRequest<{
      total: number
      limit: number
      offset: number
      cases: any[]
    }>(`/cases${query ? `?${query}` : ''}`)
  },

  /**
   * Get AI confidence metrics
   */
  async getAIConfidenceMetrics() {
    // This endpoint doesn't exist yet, return mock data
    // TODO: Implement in backend
    return {
      rolling_average: 0.85,
      sample_size: 150,
      trend: 'stable' as const,
    }
  },

  /**
   * Get case detail
   */
  async getCase(caseId: string) {
    // This endpoint doesn't exist yet, construct from cases endpoint
    // TODO: Implement /v1/ops/cases/{case_id} endpoint
    const response = await apiRequest<{ cases: any[] }>(`/cases?limit=1000`)
    const caseItem = response.cases.find(c => c.id === caseId)
    if (!caseItem) {
      throw new Error('Case not found')
    }
    
    // For now, return basic case data
    // TODO: Fetch full case detail from /v1/cases/{case_id}
    return {
      ...caseItem,
      messages: [],
      ai_artifacts: [],
    }
  },

  /**
   * Get case audit trail
   */
  async getCaseAudit(caseId: string) {
    // This endpoint doesn't exist yet, return empty array
    // TODO: Implement /v1/ops/cases/{case_id}/audit endpoint
    return []
  },

  /**
   * Update case
   */
  async updateCase(caseId: string, updates: {
    status?: string
    priority?: string
    owner_identity_id?: string
    internal_notes?: string
  }) {
    return apiRequest(`/cases/${caseId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  },
}


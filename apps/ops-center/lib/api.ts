/**
 * Ops Center API client
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}/v1/ops${endpoint}`
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText)
      throw new Error(`API request failed (${response.status}): ${errorText}`)
    }

    return response.json()
  } catch (error: any) {
    // Provide more helpful error messages
    if (error.message?.includes('fetch failed') || error.message?.includes('Failed to fetch')) {
      throw new Error(
        `Failed to connect to API at ${url}. ` +
        `Please check that the support-core service is running and accessible. ` +
        `Current API_URL: ${API_URL}`
      )
    }
    throw error
  }
}

async function kbApiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}/v1/kb${endpoint}`
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText)
      throw new Error(`API request failed (${response.status}): ${errorText}`)
    }

    return response.json()
  } catch (error: any) {
    if (error.message?.includes('fetch failed') || error.message?.includes('Failed to fetch')) {
      throw new Error(
        `Failed to connect to API at ${url}. ` +
        `Please check that the support-core service is running and accessible. ` +
        `Current API_URL: ${API_URL}`
      )
    }
    throw error
  }
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
  async getAIConfidenceMetrics(days: number = 7) {
    return apiRequest<{
      rolling_average: number
      sample_size: number
      trend: 'stable' | 'improving' | 'declining'
      time_window_days: number
      min_confidence?: number
      max_confidence?: number
    }>(`/metrics/ai-confidence?days=${days}`)
  },

  /**
   * Get case detail
   */
  async getCase(caseId: string) {
    return apiRequest<{
      id: string
      tenant_id: string
      title: string
      status: string
      priority: string
      category: string
      created_at: string
      updated_at: string
      owner_identity_id?: string
      messages: Array<{
        id: string
        sender_type: string
        sender_email: string
        body_text: string
        attachments?: any
        created_at: string
      }>
      ai_artifacts: Array<{
        id: string
        artifact_type: string
        content: string
        citations?: any
        confidence?: number
        model_used: string
        created_at: string
      }>
      sla_breached: boolean
      sla_remaining?: number
    }>(`/cases/${caseId}`)
  },

  /**
   * Get case audit trail
   */
  async getCaseAudit(caseId: string) {
    return apiRequest<Array<{
      id: string
      event_type: string
      payload?: any
      created_at: string
    }>>(`/cases/${caseId}/audit`)
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

export const kbApi = {
  /**
   * Get KB review queue
   */
  async getReviewQueue() {
    const response = await kbApiRequest<{
      count: number
      items: Array<{
        outline_document_id: string
        title: string
        overall_score: number
        clarity_score: number
        completeness_score: number
        technical_accuracy_score: number
        structure_score: number
        needs_review: boolean
        reason?: string
        created_at: string
        quality_score_id: string
        tags?: string[]
        updated_at?: string
      }>
    }>('/review-queue')
    return response
  },

  /**
   * Approve KB article
   */
  async approveArticle(documentId: string, reviewedBy: string, notes?: string, publish?: boolean) {
    return kbApiRequest(`/review/${documentId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        reviewed_by: reviewedBy,
        notes,
        publish: publish || false,
      }),
    })
  },

  /**
   * Reject KB article
   */
  async rejectArticle(documentId: string, reviewedBy: string, reason: string, disableArticle: boolean = true) {
    return kbApiRequest(`/review/${documentId}/reject`, {
      method: 'POST',
      body: JSON.stringify({
        reviewed_by: reviewedBy,
        reason,
        disable_article: disableArticle,
      }),
    })
  },
}

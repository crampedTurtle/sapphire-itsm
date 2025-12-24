/**
 * Type definitions for Ops Center
 */

export interface Alert {
  type: 'sla_breach' | 'compliance_flag' | 'low_confidence'
  severity: 'critical' | 'high' | 'medium' | 'low'
  case_id?: string
  case_title?: string
  intake_event_id?: string
  from_email?: string
  intent?: string
  confidence?: number
  event_type?: string
  created_at: string
}

export interface Case {
  id: string
  tenant_id: string
  title: string
  status: string
  priority: string
  category: string
  created_at: string
  updated_at: string
  messages_count?: number
  sla_breached?: boolean
  sla_remaining?: number | null
  onboarding?: {
    status: string
    phase: string
    is_onboarding: boolean
  }
}

export interface CaseDetail extends Case {
  messages: CaseMessage[]
  ai_artifacts: AIArtifact[]
  owner_identity_id?: string | null
  sla_remaining?: number | null
}

export interface CaseMessage {
  id: string
  sender_type: 'customer' | 'agent' | 'system'
  sender_email: string
  body_text: string
  created_at: string
  attachments?: Array<{ filename: string; url: string }>
}

export interface AIArtifact {
  id: string
  artifact_type: 'summary' | 'draft_reply' | 'kb_answer'
  content: string
  confidence?: number
  model_used: string
  created_at: string
  citations?: Array<{ title: string; url: string; snippet: string }>
}

export interface AuditEvent {
  id: string
  event_type: string
  payload: Record<string, any>
  created_at: string
  case_id?: string
  intake_event_id?: string
}


# Sapphire Ops Center

Internal-only operations dashboard for risk, control, and escalation management.

## Design Principles

1. **Ops ≠ Support** - This is a command bridge, not an email client
2. **Surface risk, not noise** - Default views show only SLA risk, compliance flags, AI uncertainty
3. **Humans are exception handlers** - Ops users intervene only when thresholds are crossed
4. **Trust through transparency** - AI confidence visible, audit trail one click away

## Features

- **Dashboard**: Risk widgets (SLA Risk Index, Compliance Flags, AI Confidence Health, Human Intervention Rate)
- **Case Queue**: Filtered list of cases requiring ops awareness
- **Case Detail**: Full ops view with intervention controls and audit trail
- **Alerts**: Pure signal - SLA breaches, compliance flags, low confidence
- **Metrics**: Trends and KPIs for weekly/monthly control

## Development

```bash
npm install
npm run dev
```

Access at http://localhost:3001

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Base URL for sapphire-support-core API (default: http://localhost:8000)

## Escalation Playbook

The Ops Center maps to escalation playbooks as follows:

1. **SLA Risk > 20%** → Review case queue, prioritize, reassign if needed
2. **Compliance Flag** → Immediate review, escalate to legal if needed
3. **Low AI Confidence** → Review AI artifacts, consider human override
4. **Break Glass** → Disable AI for case, full human handling

All interventions are logged in audit trail for transparency and compliance.

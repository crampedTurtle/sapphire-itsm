import { SupportIntake } from '../components/support/SupportIntake'
import { AuthGuard } from '../components/AuthGuard'

export default function SupportPage() {
  return (
    <AuthGuard>
      <SupportIntake />
    </AuthGuard>
  )
}


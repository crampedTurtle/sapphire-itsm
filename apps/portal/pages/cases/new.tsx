import { SupportIntake } from '../../components/support/SupportIntake'
import { AuthGuard } from '../../components/AuthGuard'

export default function NewCasePage() {
  return (
    <AuthGuard>
      <SupportIntake />
    </AuthGuard>
  )
}


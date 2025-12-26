import { SupportIntake } from '../components/support/SupportIntake'
import { AuthGuard } from '../components/AuthGuard'

export default function Home() {
  return (
    <AuthGuard>
      <SupportIntake />
    </AuthGuard>
  )
}


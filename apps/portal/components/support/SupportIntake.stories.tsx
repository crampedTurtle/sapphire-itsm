import type { Meta, StoryObj } from '@storybook/react'
import { SupportIntake } from './SupportIntake'

// Mock AuthContext
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    email: 'test@example.com',
    tenantId: 'test-tenant-id',
    isAuthenticated: true
  })
}))

const meta: Meta<typeof SupportIntake> = {
  title: 'Support/SupportIntake',
  component: SupportIntake,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof SupportIntake>

export const Default: Story = {
  args: {},
}

export const WithMessages: Story = {
  args: {},
  decorators: [
    (Story) => {
      // Pre-populate with sample messages
      return <Story />
    }
  ]
}


/**
 * AWS Amplify configuration for Cognito authentication
 * 
 * Configure these environment variables:
 * - NEXT_PUBLIC_COGNITO_REGION: AWS region (e.g., us-east-1)
 * - NEXT_PUBLIC_COGNITO_USER_POOL_ID: Cognito User Pool ID
 * - NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID: Cognito User Pool Client ID
 */
import { Amplify } from 'aws-amplify'

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID || '',
      region: process.env.NEXT_PUBLIC_COGNITO_REGION || 'us-east-1',
      loginWith: {
        email: true,
      },
    },
  },
}

// Only configure Amplify if we have the required environment variables
if (
  process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID &&
  process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID
) {
  Amplify.configure(amplifyConfig)
}

export default amplifyConfig


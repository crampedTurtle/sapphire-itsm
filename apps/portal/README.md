# Sapphire Portal

Next.js customer portal for Tier 0/1/2 support.

## Features

- **Tier 0**: Self-service KB search and AI answers
- **Tier 1/2**: Case creation, status tracking, thread replies
- **AWS Cognito Authentication**: Integrated with platform user authentication

## Authentication

The portal uses AWS Cognito for authentication. All registered platform users can access the support portal using their existing Cognito credentials.

### Setup

1. Create a Cognito User Pool in AWS (or use an existing one)
2. Create a User Pool App Client
3. Configure environment variables:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_COGNITO_REGION=us-east-1
NEXT_PUBLIC_COGNITO_USER_POOL_ID=your-user-pool-id
NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID=your-client-id
```

### How It Works

- Users sign in with their Cognito credentials (email/password)
- The portal extracts the user's email from Cognito
- Tenant resolution happens automatically:
  - If `tenant_id` is stored in Cognito custom attributes, it's used
  - Otherwise, tenant is resolved from email domain via the backend
- All API calls use the authenticated user's email
- The backend automatically resolves the tenant and creates/updates identities

### Tenant Resolution

The backend resolves tenants by email domain:
- If the email domain matches a tenant's `primary_domain`, that tenant is used
- Otherwise, a "prospect" tenant is created/used (Tier 0)

### Optional: Store tenant_id in Cognito

You can store `tenant_id` as a custom attribute in Cognito to avoid domain resolution:
- Add a custom attribute `tenant_id` (String) to your User Pool
- Set it during user registration or via Admin API
- The portal will automatically use it if available

## Development

```bash
npm install
npm run dev
```

Access at http://localhost:3000

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- `NEXT_PUBLIC_COGNITO_REGION`: AWS region for Cognito
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID`: Cognito User Pool Client ID


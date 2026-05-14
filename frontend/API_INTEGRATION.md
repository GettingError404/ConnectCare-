# Frontend-Backend Integration

## Overview
The frontend is now connected to the backend API running on `http://localhost:8000`. All API calls use authenticated tokens stored in localStorage.

## Configuration

### Environment Variables
- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (set in `.env.local`)

### API Structure
- Base URL: `http://localhost:8000/api/v1`
- Authentication: Bearer tokens in Authorization header

## API Services

### Authentication Service (`src/lib/api/services/auth.ts`)
- `login(email, password)` - POST `/auth/login`
- `register(email, password, full_name)` - POST `/auth/register`
- `refresh(refreshToken)` - POST `/auth/refresh`
- `logout(refreshToken)` - POST `/auth/logout`

### Healthcare Service (`src/lib/api/services/healthcare.ts`)
- `getElder(elderId)` - GET `/healthcare/elders/{elderId}`
- `createElder(data)` - POST `/healthcare/elders`
- `updateElder(elderId, data)` - PUT `/healthcare/elders/{elderId}`

### Devices Service (`src/lib/api/services/devices.ts`)
- `getDevices()` - GET `/devices`
- `getDevice(deviceId)` - GET `/devices/{deviceId}`
- `createDevice(data)` - POST `/devices`

### Alerts Service (`src/lib/api/services/alerts.ts`)
- `getAlerts(page, pageSize)` - GET `/alerts?page={page}&page_size={pageSize}`
- `getAlert(alertId)` - GET `/alerts/{alertId}`
- `createAlert(data)` - POST `/alerts`
- `updateAlertStatus(alertId, status)` - PATCH `/alerts/{alertId}`

### Vitals Service (`src/lib/api/services/vitals.ts`)
- `getVitals(elderId, vitalType?)` - GET `/vitals/{elderId}`
- `createVital(data)` - POST `/vitals`

## Authentication Flow

1. User logs in with email and password
2. Backend returns `access_token` and `refresh_token`
3. Tokens are stored in localStorage
4. All subsequent API calls include `Authorization: Bearer {access_token}` header
5. On logout, tokens are cleared from localStorage and backend is notified

## Auth Store Integration

The `useAuthStore` (Zustand) manages:
- Current user data
- Authentication state
- Access and refresh tokens
- Loading and error states

### Usage Example
```typescript
import { useAuthStore } from '@/store/authStore';

const { login, user, isLoading, error } = useAuthStore();

const success = await login('user@example.com', 'password');
if (success) {
  // User is authenticated
  console.log(user);
}
```

## Backend Requirements

The backend must be running on `http://localhost:8000` with:
- Database: PostgreSQL
- CORS: Enabled for all origins
- Authentication: JWT-based with Bearer tokens

Start the backend with:
```bash
docker-compose up
```

or locally:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Security Notes

- Access tokens are stored in localStorage (consider using httpOnly cookies for production)
- All API calls automatically include the access token from localStorage
- Refresh tokens are used to obtain new access tokens when expired
- CORS is enabled to allow cross-origin requests from frontend

## Testing Demo Accounts

The backend may support demo accounts for testing. Check the backend documentation or database seeding for available credentials.

## Future Enhancements

- Implement token refresh logic when token expires
- Add retry logic for failed requests
- Implement WebSocket for real-time alerts
- Add request caching with React Query

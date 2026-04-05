# Contract: Authentication API Endpoints

**Base URL**: `https://api.coquito.gcardona.me`  
**Version**: v1  
**Auth mechanism**: httpOnly cookie (`id_token`), validated by Lambda authorizer

---

## Auth Endpoints (Public — No Authorizer)

### POST /auth/callback

Exchanges a Cognito authorization code for tokens and sets httpOnly session cookies.

**Trigger**: Cognito Managed Login redirects here after successful EMAIL_OTP authentication.

**Request**:
```
POST /auth/callback?code={authorization_code}&state={csrf_state}
Content-Type: application/x-www-form-urlencoded
```

**Success Response** — `302 Found`:
```
Location: https://coquito.gcardona.me/
Set-Cookie: id_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/auth/refresh; Max-Age=2592000
```

**Error Responses**:
| Status | Code | Condition |
|--------|------|-----------|
| 400 | `INVALID_CODE` | Missing or invalid authorization code |
| 400 | `STATE_MISMATCH` | CSRF state parameter does not match |
| 503 | `AUTH_UNAVAILABLE` | Cognito token endpoint unreachable |

---

### POST /auth/refresh

Exchanges the refresh_token cookie for new access and id token cookies.  
Callable only while user is active (FR-009 inactivity enforcement).

**Request**:
```
POST /auth/refresh
Cookie: refresh_token=<jwt>
```

**Success Response** — `200 OK`:
```json
{ "ok": true }
```
```
Set-Cookie: id_token=<new_jwt>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
Set-Cookie: access_token=<new_jwt>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
```

**Error Responses**:
| Status | Code | Condition |
|--------|------|-----------|
| 401 | `REFRESH_EXPIRED` | Refresh token missing, expired, or revoked |
| 503 | `AUTH_UNAVAILABLE` | Cognito unreachable |

---

### POST /auth/logout

Clears session cookies and revokes the Cognito refresh token.

**Request**:
```
POST /auth/logout
Cookie: id_token=<jwt>; refresh_token=<jwt>
```

**Success Response** — `200 OK`:
```json
{ "ok": true }
```
```
Set-Cookie: id_token=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0
Set-Cookie: access_token=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Strict; Path=/auth/refresh; Max-Age=0
```

---

### GET /health

Public health check. No authentication required.

**Response** — `200 OK`:
```json
{ "status": "ok", "service": "coquito-api" }
```

---

## Protected Endpoints — Role: any authenticated user

All protected endpoints require a valid `id_token` cookie. The Lambda authorizer validates the JWT and injects `userId` and `role` into the request context.

**Authorizer behavior**:
- Missing/expired/invalid `id_token` cookie → `401 Unauthorized`
- Invalid role for endpoint → `403 Forbidden`
- Auth service unavailable → `503 Service Unavailable`

**Auth failure log format** (CloudWatch, WARN level):
```json
{
  "level": "WARNING",
  "endpoint": "POST /api/v1/requests",
  "timestamp": "2026-04-04T12:00:00Z",
  "error": "TOKEN_EXPIRED | INVALID_SIGNATURE | UNAUTHORIZED_ROLE",
  "requestId": "<apigw-request-id>"
}
```

---

### POST /api/v1/requests — Role: authorized-user (chef may also call)

Submit a new coquito request.

**Request**:
```
POST /api/v1/requests
Cookie: id_token=<jwt>
Content-Type: application/json

{
  "idempotencyKey": "string (UUID)",
  "batchId": "string",
  "varietyId": "string",
  "requesterName": "string",
  "requesterEmail": "string",
  "pickupDate": "YYYY-MM-DD",
  "pickupTime": "string",
  "exchangeLocation": "string",
  "bottleProvided": boolean,
  "bottleVolumeMl": number | null,
  "costContribution": boolean
}
```

**Success** — `201 Created` (existing contract, unchanged)

**Auth errors**:
- `401`: No valid session cookie
- `403`: Unauthenticated caller (no role — should not reach here past authorizer)

---

### GET /api/v1/requests/{requestId} — Role: authorized-user (own requests), chef (any request)

**Access rule**: An authorized-user may only fetch a request where `userId` matches the requester. A chef may fetch any request. The handler checks `event.requestContext.authorizer.lambda.role` and `userId`.

**Success** — `200 OK` (existing contract, unchanged)

**Auth errors**:
- `401`: No valid session cookie
- `403`: Authorized-user attempting to access another user's request

---

### GET /api/v1/batches/{batchId}/config — Role: chef only

**Access rule**: Lambda handler checks `role == "chef"`. Returns `403` otherwise.

---

### GET /api/v1/varieties — Role: any authenticated user

---

### PUT /api/v1/requests/{requestId} — Role: chef only

---

### POST /api/v1/requests/{requestId}/cancel — Role: authorized-user (own), chef (any)

---

### GET /api/v1/batches/{batchId}/ingredients — Role: chef only

---

### PUT /api/v1/batches/{batchId}/ingredients/{ingredientId}/acquired — Role: chef only

---

### POST /api/v1/requests/{requestId}/reminder — Role: chef only

---

## Lambda Authorizer Contract

**Input** (HTTP API request authorizer payload format 2.0):
```json
{
  "type": "REQUEST",
  "identitySource": "$request.header.Cookie",
  "routeArn": "arn:aws:execute-api:...",
  "headers": {
    "cookie": "id_token=<jwt>; other=..."
  }
}
```

**Output** (simple response format for HTTP API):
```json
{
  "isAuthorized": true,
  "context": {
    "userId": "<cognito-sub>",
    "role": "chef" | "authorized-user",
    "email": "<user-email>"
  }
}
```

**JWKS caching**: The authorizer caches Cognito's public keys for 15 minutes to avoid repeated HTTPS calls on every request.

**Authorizer caching**: API Gateway caches the authorizer result for 5 minutes by identity source (cookie value). Cache should be disabled in dev/test environments.

---

## CORS Configuration (HTTP API)

All API routes allow:
```
Access-Control-Allow-Origin: https://coquito.gcardona.me
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
```

`Access-Control-Allow-Credentials: true` is required for cookies to be sent cross-origin.
The `Origin` header is not wildcarded (`*`) because credentials are included.

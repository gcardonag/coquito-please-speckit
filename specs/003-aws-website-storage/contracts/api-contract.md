# API Contract: Coquito Application

**Feature**: 003-aws-website-storage  
**Date**: 2026-04-05  
**Base URL**: `https://api.{domain}` (e.g., `https://api.coquito.gcardona.me`)  
**Protocol**: HTTPS only (TLS 1.2 minimum)  
**Auth**: Cookie-based JWT (set by `/auth/callback`). Protected routes require a valid session cookie.

> **Note**: All routes listed here are existing implementations. This feature provisions the storage layer that makes them operational — no new routes are added.

---

## Authentication

### POST /auth/callback
Exchange Cognito authorization code for session tokens.  
**Auth**: Public  
**Request body**: `{ "code": "<authorization_code>", "state": "<state_param>" }`  
**Response 200**: Sets `HttpOnly` session cookie; returns `{ "redirectUrl": "/dashboard" }`  

### POST /auth/logout
Clear session cookies.  
**Auth**: Public  
**Response 200**: Clears cookies

### POST /auth/refresh
Refresh the session using the refresh token cookie.  
**Auth**: Public  
**Response 200**: Sets new session cookie

---

## Health

### GET /health
**Auth**: Public  
**Response 200**: `{ "status": "ok" }`

---

## Varieties

### GET /api/v1/varieties
List all active coquito varieties.  
**Auth**: Protected  
**Query params**: `batchId` (optional) — filter to varieties available in a specific batch  
**Response 200**:
```json
{
  "varieties": [
    {
      "varietyId": "classic",
      "name": "Classic Coquito",
      "description": "Traditional Puerto Rican coquito...",
      "imageUrl": "https://coquito.gcardona.me/assets/classic.jpg"
    }
  ]
}
```
**Response 404**: `{ "code": "BATCH_NOT_FOUND", "message": "Batch '{batchId}' not found" }` (when batchId provided and not found)

---

## Requests

### POST /api/v1/requests
Create a new coquito order.  
**Auth**: Protected  
**Request body**:
```json
{
  "idempotencyKey": "<client-generated UUID>",
  "batchId": "batch-test-2026",
  "varietyId": "classic",
  "requesterName": "Jane Doe",
  "requesterEmail": "jane@example.com",
  "pickupDate": "2026-06-01",
  "pickupTime": "14:00",
  "exchangeLocation": "Main office lobby",
  "bottleProvided": false,
  "costContribution": true
}
```
**Response 201**: Full request object (see GET /api/v1/requests/{id})  
**Response 400**: `{ "code": "VALIDATION_ERROR" | "BATCH_CLOSED" | "BOTTLE_VOLUME_EXCEEDED", "message": "..." }`  
**Response 404**: `{ "code": "BATCH_NOT_FOUND" | "VARIETY_NOT_FOUND", "message": "..." }`

### GET /api/v1/requests/{id}
Get a single request by ID.  
**Auth**: Protected  
**Response 200**:
```json
{
  "requestId": "<uuid>",
  "status": "CONFIRMED",
  "requesterName": "Jane Doe",
  "variety": { "varietyId": "classic", "name": "Classic Coquito" },
  "pickupDate": "2026-06-01",
  "pickupTime": "14:00",
  "exchangeLocation": "Main office lobby",
  "bottleProvided": false,
  "bottleVolumeMl": null,
  "costContribution": true,
  "reminders": [],
  "createdAt": "2026-04-05T12:00:00Z"
}
```

### PUT /api/v1/requests/{id}
Update a request.  
**Auth**: Protected

### POST /api/v1/requests/{id}/cancel
Cancel a request.  
**Auth**: Protected  
**Response 200**: Updated request object with `"status": "CANCELLED"`

### POST /api/v1/requests/{id}/reminder
Manually trigger a reminder for a request.  
**Auth**: Protected

---

## Batches

### GET /api/v1/batches/{id}/config
Get batch configuration.  
**Auth**: Protected  
**Response 200**: Full batch object

### GET /api/v1/batches/{id}/ingredients
Get ingredient list for a batch.  
**Auth**: Protected

### PUT /api/v1/batches/{id}/ingredients/{ingredId}/acquired
Mark an ingredient as acquired.  
**Auth**: Protected

---

## Users

### POST /api/v1/users
Create a new user in Cognito.  
**Auth**: Protected (admin only)  
**Request body**: `{ "email": "newuser@example.com" }`

---

## Error Response Format

All error responses follow:
```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable description of the error and what to do next"
}
```

## Common HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Validation failure or business rule violation |
| 401 | Authentication required or session expired |
| 404 | Resource not found |
| 500 | Internal server error |

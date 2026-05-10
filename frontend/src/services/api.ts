// ---------------------------------------------------------------------------
// Typed API client — all contract endpoints
// Reads VITE_API_BASE_URL from environment (set via .env.local)
// ---------------------------------------------------------------------------

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1';

// ---- Error type ----

export interface ApiError {
  code: string;
  message: string;
  status: number;
}

export class ApiRequestError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(error: ApiError) {
    super(error.message);
    this.name = 'ApiRequestError';
    this.code = error.code;
    this.status = error.status;
  }
}

// ---- Domain types ----

export interface VarietySummary {
  varietyId: string;
  name: string;
  description: string;
  imageUrl: string;
}

export interface BatchConfig {
  batchId: string;
  batchName: string;
  cutoffDate: string;
  maxBottleVolumeMl: number;
  status: 'OPEN' | 'CLOSED' | 'COMPLETED';
  availableVarieties: VarietySummary[];
}

export interface ReminderSummary {
  scheduledFor: string;
  status: 'SCHEDULED' | 'SENT' | 'CANCELLED';
}

export interface RequestResponse {
  requestId: string;
  status: 'PENDING' | 'CONFIRMED' | 'CANCELLED';
  requesterName: string;
  variety: { varietyId: string; name: string };
  pickupDate: string;
  pickupTime: string;
  exchangeLocation: string;
  bottleProvided: boolean;
  bottleVolumeMl: number | null;
  costContribution: boolean;
  reminders: ReminderSummary[];
  createdAt: string;
  updatedAt?: string;
  batch?: {
    batchId: string;
    batchName: string;
    cutoffDate: string;
    maxBottleVolumeMl: number;
  };
  editable?: boolean;
}

export interface CreateRequestPayload {
  idempotencyKey: string;
  requesterName: string;
  requesterEmail: string;
  batchId: string;
  varietyId: string;
  pickupDate: string;
  pickupTime: string;
  exchangeLocation: string;
  bottleProvided: boolean;
  bottleVolumeMl: number | null;
  costContribution: boolean;
}

export interface UpdateRequestPayload {
  varietyId?: string;
  pickupDate?: string;
  pickupTime?: string;
  exchangeLocation?: string;
  bottleProvided?: boolean;
  bottleVolumeMl?: number | null;
  costContribution?: boolean;
}

export interface IngredientItem {
  ingredientId: string;
  name: string;
  totalQuantity: number;
  unit: string;
  category: string;
  acquired: boolean;
}

export interface VarietyIngredients {
  varietyId: string;
  varietyName: string;
  confirmedCount: number;
  ingredients: IngredientItem[];
}

export interface IngredientListResponse {
  batchId: string;
  batchName: string;
  isFinalized: boolean;
  totalConfirmedRequests: number;
  byVariety: VarietyIngredients[];
  totals: Array<{ name: string; totalQuantity: number; unit: string; category: string }>;
}

// ---- Fetch helper ----

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let code = 'UNKNOWN_ERROR';
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      code = body.code ?? code;
      message = body.message ?? message;
    } catch {
      // body not JSON — use defaults
    }
    throw new ApiRequestError({ code, message, status: response.status });
  }

  return response.json() as Promise<T>;
}

// ---- Endpoints ----

export function listVarieties(batchId?: string): Promise<{ varieties: VarietySummary[] }> {
  const qs = batchId ? `?batchId=${encodeURIComponent(batchId)}` : '';
  return request(`/varieties${qs}`);
}

export function getBatchConfig(batchId: string): Promise<BatchConfig> {
  return request(`/batches/${encodeURIComponent(batchId)}/config`);
}

export function createRequest(payload: CreateRequestPayload): Promise<RequestResponse> {
  return request('/requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getRequest(requestId: string): Promise<RequestResponse> {
  return request(`/requests/${encodeURIComponent(requestId)}`);
}

export function updateRequest(
  requestId: string,
  payload: UpdateRequestPayload
): Promise<RequestResponse> {
  return request(`/requests/${encodeURIComponent(requestId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function cancelRequest(
  requestId: string
): Promise<{ requestId: string; status: 'CANCELLED'; cancelledAt: string }> {
  return request(`/requests/${encodeURIComponent(requestId)}/cancel`, {
    method: 'POST',
  });
}

// ---- Chef batch management types ----

export interface CurrentUser {
  userId: string;
  role: string;
  email: string;
}

export interface BatchSummary {
  batchId: string;
  batchName: string;
  cutoffDate: string;
  maxBottleVolumeMl: number;
  status: 'OPEN' | 'CLOSED' | 'COMPLETED';
  availableVarietyIds: string[];
  activeRequestCount: number;
  createdAt: string;
}

export interface CreateBatchPayload {
  batchName: string;
  cutoffDate: string;
  maxBottleVolumeMl: number;
  availableVarietyIds: string[];
}

export interface UpdateBatchPayload {
  batchName?: string;
  cutoffDate?: string;
  maxBottleVolumeMl?: number;
  availableVarietyIds?: string[];
}

export interface UpdateBatchStatusPayload {
  status: 'CLOSED' | 'COMPLETED';
}

// ---- Chef batch management endpoints ----

export function getMe(): Promise<CurrentUser> {
  return request('/me');
}

export function listBatches(): Promise<{ batches: BatchSummary[] }> {
  return request('/batches');
}

export function createBatch(payload: CreateBatchPayload): Promise<BatchSummary> {
  return request('/batches', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateBatch(id: string, payload: UpdateBatchPayload): Promise<BatchSummary> {
  return request(`/batches/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function updateBatchStatus(
  id: string,
  status: 'CLOSED' | 'COMPLETED'
): Promise<BatchSummary> {
  return request(`/batches/${encodeURIComponent(id)}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  });
}

export function getIngredientList(batchId: string): Promise<IngredientListResponse> {
  return request(`/batches/${encodeURIComponent(batchId)}/ingredients`);
}

export function markIngredientAcquired(
  batchId: string,
  ingredientId: string,
  acquired: boolean
): Promise<{ ingredientId: string; acquired: boolean; updatedAt: string }> {
  return request(
    `/batches/${encodeURIComponent(batchId)}/ingredients/${encodeURIComponent(ingredientId)}/acquired`,
    {
      method: 'PUT',
      body: JSON.stringify({ acquired }),
    }
  );
}

// ---- Chef variety management types ----

export interface ChefIngredientDetail {
  ingredientId: string;
  name: string;
  quantityPerBottle: number;
  unit: string;
  category: string;
}

export interface ChefVarietyDetail {
  varietyId: string;
  name: string;
  description: string;
  imageKey: string;
  bottleYieldMl: number;
  active: boolean;
  ingredients: ChefIngredientDetail[];
}

export interface IngredientPayload {
  ingredientId?: string;
  name: string;
  quantityPerBottle: number;
  unit: string;
  category: string;
}

export interface CreateVarietyPayload {
  name: string;
  description?: string;
  imageKey?: string;
  bottleYieldMl: number;
  active?: boolean;
  ingredients?: IngredientPayload[];
}

export interface UpdateVarietyPayload {
  name?: string;
  description?: string;
  imageKey?: string;
  bottleYieldMl?: number;
  active?: boolean;
  ingredients?: IngredientPayload[];
}

// ---- Chef variety management endpoints ----

export function chefListVarieties(): Promise<{ varieties: ChefVarietyDetail[] }> {
  return request('/chef/varieties');
}

export function chefCreateVariety(
  payload: CreateVarietyPayload
): Promise<{ variety: ChefVarietyDetail }> {
  return request('/chef/varieties', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function chefUpdateVariety(
  id: string,
  payload: UpdateVarietyPayload
): Promise<{ variety: ChefVarietyDetail }> {
  return request(`/chef/varieties/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

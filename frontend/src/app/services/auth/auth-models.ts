/**
 * Response from registration/login begin endpoints
 * Options are JSON-serialized WebAuthn options from the backend
 */
export interface AuthBeginResponse {
  challenge_id: string;
  options: Record<string, unknown>;
}

/**
 * Request for registration/login complete endpoints
 */
export interface AuthCompleteRequest {
  challenge_id: string;
  credential: Record<string, unknown>;
}

/**
 * Response from registration/login complete endpoints
 */
export interface AuthCompleteResponse {
  user_id: string;
  message: string;
}

/**
 * Response from logout endpoint
 */
export interface LogoutResponse {
  message: string;
}

/**
 * Response from /auth/me endpoint
 */
export interface MeResponse {
  user_id: string;
  display_name: string | null;
  created_ts: number;
}


/**
 * User interface - matches backend response.
 * Field names are preserved exactly as received from API.
 */
export interface User {
  user_id: string;
  display_name: string | null;
  default_currency: string;
  created_ts: number;
  updated_ts: number;
}

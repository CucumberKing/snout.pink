import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';

export interface McpToken {
  token_id: string;
  name: string;
  token_prefix: string;
  scopes: string[];
  created_at_ts: number;
  last_used_at_ts: number | null;
}

export interface McpTokenListResponse {
  mcp_tokens: McpToken[];
  total: number;
}

export interface McpTokenCreated extends McpToken {
  token: string;
  mcp_url: string;
  client_config: {
    mcpServers: {
      snout: {
        url: string;
        headers: { Authorization: string };
      };
    };
  };
}

export interface McpTokenCreateRequest {
  name: string;
  scopes: string[];
}

export const MCP_SCOPE_READ = 'subscriptions:read';
export const MCP_SCOPE_WRITE = 'subscriptions:write';

@Injectable({
  providedIn: 'root',
})
export class McpTokenService {
  private readonly http = inject(HttpClient);
  private readonly api_url = `${environment.api_url}/users/mcp-tokens`;

  list(): Promise<McpTokenListResponse> {
    return firstValueFrom(
      this.http.get<McpTokenListResponse>(this.api_url, { withCredentials: true }),
    );
  }

  create(data: McpTokenCreateRequest): Promise<McpTokenCreated> {
    return firstValueFrom(
      this.http.post<McpTokenCreated>(this.api_url, data, { withCredentials: true }),
    );
  }

  delete(token_id: string): Promise<void> {
    return firstValueFrom(
      this.http.delete<void>(`${this.api_url}/${token_id}`, { withCredentials: true }),
    );
  }
}

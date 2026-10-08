import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  IonButton,
  IonIcon,
  IonInput,
  IonSelect,
  IonSelectOption,
} from '@ionic/angular';
import { addIcons } from 'ionicons';
import { copyOutline, keyOutline, trashOutline } from 'ionicons/icons';

import { AuthService } from '../../../../services/auth';
import {
  MCP_SCOPE_READ,
  MCP_SCOPE_WRITE,
  McpToken,
  McpTokenCreated,
  McpTokenService,
} from '../../../../services/mcp-token.service';

type AccessChoice = 'read' | 'read_write';

@Component({
  selector: 'app-mcp-access',
  imports: [IonButton, IonIcon, IonInput, IonSelect, IonSelectOption],
  templateUrl: './mcp-access.html',
  styleUrl: './mcp-access.scss',
})
export class McpAccessComponent implements OnInit {
  private readonly mcp_tokens = inject(McpTokenService);
  protected readonly auth_service = inject(AuthService);

  protected readonly tokens = signal<McpToken[]>([]);
  protected readonly name = signal('');
  protected readonly access = signal<AccessChoice>('read_write');
  protected readonly created = signal<McpTokenCreated | null>(null);
  protected readonly error_message = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly copied = signal<'url' | 'config' | null>(null);

  constructor() {
    addIcons({ copyOutline, keyOutline, trashOutline });
  }

  ngOnInit(): void {
    if (this.auth_service.is_authenticated()) {
      void this.reload();
    }
  }

  protected on_name_input(event: CustomEvent): void {
    this.name.set(String(event.detail.value ?? ''));
  }

  protected on_access_change(event: CustomEvent): void {
    const value = event.detail.value;
    if (value === 'read' || value === 'read_write') {
      this.access.set(value);
    }
  }

  protected scope_label(scopes: string[]): string {
    return scopes.includes(MCP_SCOPE_WRITE) ? 'Read and write' : 'Read';
  }

  protected format_last_used(last_used_at_ts: number | null): string {
    if (last_used_at_ts === null) {
      return 'Never used';
    }
    return new Date(last_used_at_ts * 1000).toLocaleString();
  }

  protected client_config_text(): string {
    const created = this.created();
    if (!created) {
      return '';
    }
    return JSON.stringify(created.client_config, null, 2);
  }

  protected async create_token(): Promise<void> {
    const name = this.name().trim();
    if (!name || this.loading()) {
      return;
    }
    this.loading.set(true);
    this.error_message.set(null);
    this.copied.set(null);
    const scopes =
      this.access() === 'read_write'
        ? [MCP_SCOPE_READ, MCP_SCOPE_WRITE]
        : [MCP_SCOPE_READ];
    try {
      const created = await this.mcp_tokens.create({ name, scopes });
      this.created.set(created);
      this.name.set('');
      await this.reload();
    } catch (err: unknown) {
      this.error_message.set(http_error_message(err));
    } finally {
      this.loading.set(false);
    }
  }

  protected async revoke(token_id: string): Promise<void> {
    if (!window.confirm('Revoke this MCP access? Clients using it will stop working.')) {
      return;
    }
    this.error_message.set(null);
    try {
      await this.mcp_tokens.delete(token_id);
      await this.reload();
    } catch (err: unknown) {
      this.error_message.set(http_error_message(err));
    }
  }

  protected async copy_text(value: string, which: 'url' | 'config'): Promise<void> {
    try {
      await navigator.clipboard.writeText(value);
      this.copied.set(which);
    } catch {
      this.error_message.set('Could not copy. Select the text and copy it manually.');
    }
  }

  protected dismiss_secret(): void {
    this.created.set(null);
    this.copied.set(null);
  }

  private async reload(): Promise<void> {
    const response = await this.mcp_tokens.list();
    this.tokens.set(response.mcp_tokens);
  }
}

function http_error_message(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    const detail = err.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    return `Request failed (${err.status})`;
  }
  return 'Something went wrong';
}

/**
 * WebMCP Service - Exposes structured tools for AI agents via navigator.modelContext
 *
 * WebMCP is a proposed web standard (Chrome 146+) that lets websites declare
 * tools that AI agents can discover and call, replacing screen-scraping with
 * explicit, structured API calls.
 *
 * Spec: https://github.com/webmachinelearning/webmcp
 */
import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { SubscriptionService } from './subscription.service';
import { CurrencyService } from './currency.service';
import { Subscription, SubscriptionColor } from '../models/subscription.model';

// ── WebMCP browser API type declarations ──────────────────────

interface ModelContextToolResult {
  content: Array<{ type: 'text'; text: string }>;
  isError?: boolean;
}

interface ModelContextToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
  annotations?: {
    readOnlyHint?: string;
    title?: string;
  };
  execute: (params: Record<string, unknown>) => ModelContextToolResult | Promise<ModelContextToolResult>;
}

declare global {
  interface Navigator {
    modelContext?: {
      registerTool(definition: ModelContextToolDefinition): void;
      unregisterTool(name: string): void;
      clearContext(): void;
    };
  }
}

// ── Valid colors for input validation ─────────────────────────

const VALID_COLORS: SubscriptionColor[] = [
  'purple', 'blue', 'cyan', 'green',
  'yellow', 'orange', 'pink', 'rose',
  'slate', 'indigo', 'teal', 'amber',
];

const VALID_CYCLES = ['Monthly', 'Yearly', 'Weekly'] as const;

// ── Service ───────────────────────────────────────────────────

@Injectable({
  providedIn: 'root'
})
export class WebMcpService {
  private readonly platform_id = inject(PLATFORM_ID);
  private readonly is_browser = isPlatformBrowser(this.platform_id);
  private readonly subs = inject(SubscriptionService);
  private readonly currency = inject(CurrencyService);

  init(): void {
    if (!this.is_browser) return;
    if (!navigator.modelContext) {
      console.log('[WebMCP] navigator.modelContext not available');
      return;
    }

    this.register_list_subscriptions();
    this.register_add_subscription();
    this.register_update_subscription();
    this.register_delete_subscription();
    this.register_get_spending_summary();
    this.register_export_subscriptions();

    console.log('[WebMCP] 6 tools registered');
  }

  // ── Read tools ──────────────────────────────────────────────

  private register_list_subscriptions(): void {
    navigator.modelContext!.registerTool({
      name: 'list_subscriptions',
      description: 'List all tracked subscriptions with their name, price, billing cycle, and currency. Also returns the total monthly and yearly cost across all subscriptions.',
      inputSchema: {
        type: 'object',
        properties: {}
      },
      annotations: { readOnlyHint: 'true' },
      execute: () => {
        try {
          const subscriptions = this.subs.subscriptions();
          if (subscriptions.length === 0) {
            return this.success_result('No subscriptions tracked yet.');
          }
          return this.success_result(this.format_subscription_list(subscriptions));
        } catch (err) {
          return this.error_result(`Failed to list subscriptions: ${this.err_msg(err)}`);
        }
      }
    });
  }

  private register_get_spending_summary(): void {
    navigator.modelContext!.registerTool({
      name: 'get_spending_summary',
      description: 'Get a spending summary with total monthly and yearly costs, subscription count, and the top 3 most expensive subscriptions ranked by monthly cost.',
      inputSchema: {
        type: 'object',
        properties: {}
      },
      annotations: { readOnlyHint: 'true' },
      execute: () => {
        try {
          const subscriptions = this.subs.subscriptions();
          if (subscriptions.length === 0) {
            return this.success_result('No subscriptions tracked yet. Add some to see spending insights.');
          }

          const monthly = this.subs.monthly_total();
          const yearly = this.subs.yearly_total();
          const top3 = this.subs.get_sorted_by_cost().slice(0, 3);

          const lines: string[] = [];
          lines.push('Spending Summary');
          lines.push('');
          lines.push(`Total subscriptions: ${subscriptions.length}`);
          lines.push(`Monthly total: ${this.currency.format(monthly)}`);
          lines.push(`Yearly total: ${this.currency.format(yearly)}`);
          lines.push('');
          lines.push('Top 3 most expensive:');

          for (let i = 0; i < top3.length; i++) {
            const sub = top3[i];
            const monthly_cost = this.subs.to_monthly_original(sub);
            lines.push(`  ${i + 1}. ${sub.name} - ${this.currency.format_original(monthly_cost, sub.currency)}/month (${sub.cycle}, ${this.currency.format_original(sub.price, sub.currency)}/${sub.cycle.toLowerCase()})`);
          }

          return this.success_result(lines.join('\n'));
        } catch (err) {
          return this.error_result(`Failed to get summary: ${this.err_msg(err)}`);
        }
      }
    });
  }

  // ── Write tools ─────────────────────────────────────────────

  private register_add_subscription(): void {
    navigator.modelContext!.registerTool({
      name: 'add_subscription',
      description: 'Add a new subscription to track. Requires name, price, currency code, and billing cycle. Optionally accepts a URL, color theme, and earliest cancellation date.',
      inputSchema: {
        type: 'object',
        properties: {
          name: {
            type: 'string',
            description: 'Name of the subscription service (e.g. "Netflix", "Spotify").'
          },
          price: {
            type: 'number',
            description: 'Price per billing cycle (e.g. 12.99).'
          },
          currency: {
            type: 'string',
            description: 'ISO 4217 currency code (e.g. "EUR", "USD", "GBP").'
          },
          cycle: {
            type: 'string',
            enum: ['Monthly', 'Yearly', 'Weekly'],
            description: 'Billing cycle frequency.'
          },
          url: {
            type: 'string',
            description: 'Optional website URL of the service (e.g. "https://netflix.com").'
          },
          color: {
            type: 'string',
            enum: VALID_COLORS,
            description: 'Optional color theme. One of: purple, blue, cyan, green, yellow, orange, pink, rose, slate, indigo, teal, amber. A random color is chosen if not specified.'
          },
          earliest_cancellation_date: {
            type: 'string',
            description: 'Optional earliest cancellation date in ISO format (YYYY-MM-DD). Useful for tracking contract lock-in periods.'
          }
        },
        required: ['name', 'price', 'currency', 'cycle']
      },
      execute: async (params) => {
        try {
          const name = params['name'] as string;
          const price = params['price'] as number;
          const currency = (params['currency'] as string).toUpperCase();
          const cycle = params['cycle'] as string;
          const url = (params['url'] as string | undefined) ?? null;
          const color = (params['color'] as SubscriptionColor | undefined) ?? VALID_COLORS[Math.floor(Math.random() * VALID_COLORS.length)];

          if (!name || name.trim().length === 0) {
            return this.error_result('Name is required.');
          }
          if (price <= 0) {
            return this.error_result('Price must be greater than 0.');
          }
          if (!VALID_CYCLES.includes(cycle as typeof VALID_CYCLES[number])) {
            return this.error_result(`Invalid cycle. Must be one of: ${VALID_CYCLES.join(', ')}`);
          }

          let earliest_cancellation_ts: number | null = null;
          if (params['earliest_cancellation_date']) {
            const date = new Date(params['earliest_cancellation_date'] as string);
            if (isNaN(date.getTime())) {
              return this.error_result('Invalid date format. Use YYYY-MM-DD.');
            }
            earliest_cancellation_ts = date.getTime() / 1000;
          }

          const sub = await this.subs.add({
            name: name.trim(),
            price,
            currency,
            cycle: cycle as typeof VALID_CYCLES[number],
            url,
            color,
            earliest_cancellation_ts,
          });

          const monthly = this.subs.to_monthly_original(sub);
          return this.success_result(
            `Added "${sub.name}" - ${this.currency.format_original(sub.price, sub.currency)}/${sub.cycle.toLowerCase()} (${this.currency.format_original(monthly, sub.currency)}/month). ID: ${sub.subscription_id}`
          );
        } catch (err) {
          return this.error_result(`Failed to add subscription: ${this.err_msg(err)}`);
        }
      }
    });
  }

  private register_update_subscription(): void {
    navigator.modelContext!.registerTool({
      name: 'update_subscription',
      description: 'Update an existing subscription. Use list_subscriptions first to get subscription IDs. Only the fields you provide will be updated.',
      inputSchema: {
        type: 'object',
        properties: {
          subscription_id: {
            type: 'string',
            description: 'The subscription ID to update. Use list_subscriptions to find IDs.'
          },
          name: {
            type: 'string',
            description: 'New name for the subscription.'
          },
          price: {
            type: 'number',
            description: 'New price per billing cycle.'
          },
          currency: {
            type: 'string',
            description: 'New ISO 4217 currency code.'
          },
          cycle: {
            type: 'string',
            enum: ['Monthly', 'Yearly', 'Weekly'],
            description: 'New billing cycle.'
          },
          url: {
            type: 'string',
            description: 'New website URL (pass empty string to clear).'
          },
          color: {
            type: 'string',
            enum: VALID_COLORS,
            description: 'New color theme.'
          },
          earliest_cancellation_date: {
            type: 'string',
            description: 'New earliest cancellation date (YYYY-MM-DD). Pass empty string to clear.'
          }
        },
        required: ['subscription_id']
      },
      execute: async (params) => {
        try {
          const subscription_id = params['subscription_id'] as string;

          const existing = this.subs.get(subscription_id);
          if (!existing) {
            return this.error_result(`Subscription "${subscription_id}" not found. Use list_subscriptions to see available IDs.`);
          }

          const updates: Record<string, unknown> = {};

          if (params['name'] !== undefined) updates['name'] = (params['name'] as string).trim();
          if (params['price'] !== undefined) {
            const price = params['price'] as number;
            if (price <= 0) return this.error_result('Price must be greater than 0.');
            updates['price'] = price;
          }
          if (params['currency'] !== undefined) updates['currency'] = (params['currency'] as string).toUpperCase();
          if (params['cycle'] !== undefined) {
            const cycle = params['cycle'] as string;
            if (!VALID_CYCLES.includes(cycle as typeof VALID_CYCLES[number])) {
              return this.error_result(`Invalid cycle. Must be one of: ${VALID_CYCLES.join(', ')}`);
            }
            updates['cycle'] = cycle;
          }
          if (params['url'] !== undefined) {
            const url = params['url'] as string;
            updates['url'] = url === '' ? null : url;
          }
          if (params['color'] !== undefined) updates['color'] = params['color'];
          if (params['earliest_cancellation_date'] !== undefined) {
            const date_str = params['earliest_cancellation_date'] as string;
            if (date_str === '') {
              updates['earliest_cancellation_ts'] = null;
            } else {
              const date = new Date(date_str);
              if (isNaN(date.getTime())) {
                return this.error_result('Invalid date format. Use YYYY-MM-DD.');
              }
              updates['earliest_cancellation_ts'] = date.getTime() / 1000;
            }
          }

          if (Object.keys(updates).length === 0) {
            return this.error_result('No fields to update. Provide at least one field to change.');
          }

          const updated = await this.subs.update(subscription_id, updates);
          if (!updated) {
            return this.error_result('Update failed.');
          }

          return this.success_result(`Updated "${updated.name}" successfully.`);
        } catch (err) {
          return this.error_result(`Failed to update subscription: ${this.err_msg(err)}`);
        }
      }
    });
  }

  private register_delete_subscription(): void {
    navigator.modelContext!.registerTool({
      name: 'delete_subscription',
      description: 'Delete a subscription by its ID. Use list_subscriptions first to get subscription IDs. This action cannot be undone.',
      inputSchema: {
        type: 'object',
        properties: {
          subscription_id: {
            type: 'string',
            description: 'The subscription ID to delete. Use list_subscriptions to find IDs.'
          }
        },
        required: ['subscription_id']
      },
      execute: async (params) => {
        try {
          const subscription_id = params['subscription_id'] as string;

          const existing = this.subs.get(subscription_id);
          if (!existing) {
            return this.error_result(`Subscription "${subscription_id}" not found. Use list_subscriptions to see available IDs.`);
          }

          const name = existing.name;
          const removed = await this.subs.remove(subscription_id);
          if (!removed) {
            return this.error_result('Delete failed.');
          }

          return this.success_result(`Deleted "${name}". ${this.subs.subscription_count()} subscriptions remaining.`);
        } catch (err) {
          return this.error_result(`Failed to delete subscription: ${this.err_msg(err)}`);
        }
      }
    });
  }

  private register_export_subscriptions(): void {
    navigator.modelContext!.registerTool({
      name: 'export_subscriptions',
      description: 'Export all subscriptions as a JSON backup. Returns the full subscription data that can be saved or imported later.',
      inputSchema: {
        type: 'object',
        properties: {}
      },
      annotations: { readOnlyHint: 'true' },
      execute: () => {
        try {
          const subscriptions = this.subs.subscriptions();
          if (subscriptions.length === 0) {
            return this.success_result('No subscriptions to export.');
          }

          const json = this.subs.export_data();
          return this.success_result(`Exported ${subscriptions.length} subscriptions:\n\n${json}`);
        } catch (err) {
          return this.error_result(`Failed to export: ${this.err_msg(err)}`);
        }
      }
    });
  }

  // ── Formatting helpers ────────────────────────────────────

  private format_subscription_list(subscriptions: Subscription[]): string {
    const monthly = this.subs.monthly_total();
    const yearly = this.subs.yearly_total();

    const lines: string[] = [];
    lines.push(`${subscriptions.length} subscriptions (Monthly: ${this.currency.format(monthly)} | Yearly: ${this.currency.format(yearly)}):`);
    lines.push('');

    for (let i = 0; i < subscriptions.length; i++) {
      const sub = subscriptions[i];
      const monthly_cost = this.subs.to_monthly_original(sub);
      lines.push(`${i + 1}. ${sub.name}`);
      lines.push(`   Price: ${this.currency.format_original(sub.price, sub.currency)}/${sub.cycle.toLowerCase()}`);
      lines.push(`   Monthly: ${this.currency.format_original(monthly_cost, sub.currency)}`);
      if (sub.url) lines.push(`   URL: ${sub.url}`);
      if (sub.earliest_cancellation_ts) {
        lines.push(`   Earliest cancellation: ${this.format_date(sub.earliest_cancellation_ts)}`);
      }
      lines.push(`   ID: ${sub.subscription_id}`);
      lines.push('');
    }

    return lines.join('\n');
  }

  private success_result(text: string): ModelContextToolResult {
    return { content: [{ type: 'text', text }] };
  }

  private error_result(message: string): ModelContextToolResult {
    return { content: [{ type: 'text', text: `Error: ${message}` }], isError: true };
  }

  private err_msg(err: unknown): string {
    return err instanceof Error ? err.message : String(err);
  }

  private format_date(ts: number): string {
    return new Date(ts * 1000).toISOString().split('T')[0];
  }
}

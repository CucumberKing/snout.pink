import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import {
  Subscription,
  SubscriptionCreateInput,
  SubscriptionUpdateInput,
  SubscriptionListResponse,
  random_color,
} from '../models/subscription.model';
import { environment } from '../../environments/environment';

const STORAGE_KEY = 'snout_subscriptions';

function generate_local_id(): string {
  return 'local_' + crypto.randomUUID();
}

@Injectable({
  providedIn: 'root',
})
export class SubscriptionService {
  private readonly http = inject(HttpClient);
  private readonly api_url = `${environment.api_url}/subscriptions`;

  private readonly _subscriptions = signal<Subscription[]>([]);
  private readonly _monthly_total = signal<number>(0);
  private readonly _yearly_total = signal<number>(0);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _is_authenticated = signal<boolean>(false);

  readonly subscriptions = this._subscriptions.asReadonly();
  readonly subscription_count = computed(() => this._subscriptions().length);
  readonly has_subscriptions = computed(() => this._subscriptions().length > 0);
  readonly monthly_total = this._monthly_total.asReadonly();
  readonly yearly_total = this._yearly_total.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();

  constructor() {
    this.load_from_storage();
  }

  // ============================================
  // Auth State Management
  // ============================================

  /**
   * Called when user logs in - load from server
   */
  async on_login(): Promise<void> {
    this._is_authenticated.set(true);
    await this.load_from_server();
  }

  /**
   * Called when user logs out - keep local data, switch to local mode
   */
  on_logout(): void {
    this._is_authenticated.set(false);
    // Data stays in localStorage, user can continue using locally
  }

  /**
   * Refresh data from server (if authenticated)
   */
  async refresh(): Promise<void> {
    if (this._is_authenticated()) {
      await this.load_from_server();
    }
  }

  // ============================================
  // CRUD Operations (auto-sync when authenticated)
  // ============================================

  /**
   * Create a new subscription
   */
  async add(input: SubscriptionCreateInput): Promise<Subscription> {
    if (this._is_authenticated()) {
      return this.add_remote(input);
    }
    return this.add_local(input);
  }

  /**
   * Update an existing subscription
   */
  async update(
    subscription_id: string,
    updates: SubscriptionUpdateInput
  ): Promise<Subscription | null> {
    if (this._is_authenticated()) {
      return this.update_remote(subscription_id, updates);
    }
    return this.update_local(subscription_id, updates);
  }

  /**
   * Delete a subscription
   */
  async remove(subscription_id: string): Promise<boolean> {
    if (this._is_authenticated()) {
      return this.remove_remote(subscription_id);
    }
    return this.remove_local(subscription_id);
  }

  /**
   * Get a subscription by ID
   */
  get(subscription_id: string): Subscription | undefined {
    return this._subscriptions().find((sub) => sub.subscription_id === subscription_id);
  }

  // ============================================
  // Local Storage Operations
  // ============================================

  private add_local(input: SubscriptionCreateInput): Subscription {
    const now = Date.now() / 1000;
    const subscription: Subscription = {
      subscription_id: generate_local_id(),
      user_id: 'local',
      name: input.name,
      price: input.price,
      currency: input.currency,
      cycle: input.cycle,
      url: input.url,
      color: input.color,
      created_ts: now,
      updated_ts: now,
    };

    this._subscriptions.update((subs) => [...subs, subscription]);
    this.recalculate_totals();
    this.save_to_storage();

    return subscription;
  }

  private update_local(
    subscription_id: string,
    updates: SubscriptionUpdateInput
  ): Subscription | null {
    let updated_sub: Subscription | null = null;

    this._subscriptions.update((subs) =>
      subs.map((sub) => {
        if (sub.subscription_id === subscription_id) {
          updated_sub = {
            ...sub,
            ...updates,
            updated_ts: Date.now() / 1000,
          };
          return updated_sub;
        }
        return sub;
      })
    );

    if (updated_sub) {
      this.recalculate_totals();
      this.save_to_storage();
    }

    return updated_sub;
  }

  private remove_local(subscription_id: string): boolean {
    const before = this._subscriptions().length;

    this._subscriptions.update((subs) =>
      subs.filter((sub) => sub.subscription_id !== subscription_id)
    );

    const removed = this._subscriptions().length < before;

    if (removed) {
      this.recalculate_totals();
      this.save_to_storage();
    }

    return removed;
  }

  private load_from_storage(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data = JSON.parse(stored) as Subscription[];
        this._subscriptions.set(data);
        this.recalculate_totals();
      }
    } catch (err) {
      console.error('Failed to load from localStorage:', err);
    }
  }

  private save_to_storage(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this._subscriptions()));
    } catch (err) {
      console.error('Failed to save to localStorage:', err);
    }
  }

  // ============================================
  // Remote API Operations
  // ============================================

  private async add_remote(input: SubscriptionCreateInput): Promise<Subscription> {
    this._loading.set(true);
    try {
      const subscription = await firstValueFrom(
        this.http.post<Subscription>(this.api_url, input, { withCredentials: true })
      );

      this._subscriptions.update((subs) => [...subs, subscription]);
      this.recalculate_totals();
      this.save_to_storage();

      return subscription;
    } catch (err) {
      console.error('Failed to add subscription:', err);
      // Fallback to local
      return this.add_local(input);
    } finally {
      this._loading.set(false);
    }
  }

  private async update_remote(
    subscription_id: string,
    updates: SubscriptionUpdateInput
  ): Promise<Subscription | null> {
    this._loading.set(true);
    try {
      const subscription = await firstValueFrom(
        this.http.patch<Subscription>(`${this.api_url}/${subscription_id}`, updates, {
          withCredentials: true,
        })
      );

      this._subscriptions.update((subs) =>
        subs.map((sub) => (sub.subscription_id === subscription_id ? subscription : sub))
      );
      this.recalculate_totals();
      this.save_to_storage();

      return subscription;
    } catch (err) {
      console.error('Failed to update subscription:', err);
      // Fallback to local
      return this.update_local(subscription_id, updates);
    } finally {
      this._loading.set(false);
    }
  }

  private async remove_remote(subscription_id: string): Promise<boolean> {
    this._loading.set(true);
    try {
      await firstValueFrom(
        this.http.delete(`${this.api_url}/${subscription_id}`, { withCredentials: true })
      );

      this._subscriptions.update((subs) =>
        subs.filter((sub) => sub.subscription_id !== subscription_id)
      );
      this.recalculate_totals();
      this.save_to_storage();

      return true;
    } catch (err) {
      console.error('Failed to delete subscription:', err);
      // Fallback to local
      return this.remove_local(subscription_id);
    } finally {
      this._loading.set(false);
    }
  }

  private async load_from_server(): Promise<void> {
    this._loading.set(true);
    try {
      const response = await firstValueFrom(
        this.http.get<SubscriptionListResponse>(this.api_url, { withCredentials: true })
      );

      this._subscriptions.set(response.subscriptions);
      this._monthly_total.set(response.monthly_total);
      this._yearly_total.set(response.yearly_total);
      this.save_to_storage();
    } catch (err) {
      console.error('Failed to load from server:', err);
      this._error.set('Failed to load subscriptions');
    } finally {
      this._loading.set(false);
    }
  }

  // ============================================
  // Utility Methods
  // ============================================

  to_monthly_original(sub: Subscription): number {
    let monthly = sub.price;
    if (sub.cycle === 'Yearly') monthly = sub.price / 12;
    if (sub.cycle === 'Weekly') monthly = sub.price * 4.33;
    return monthly;
  }

  to_yearly_original(sub: Subscription): number {
    let yearly = sub.price * 12;
    if (sub.cycle === 'Yearly') yearly = sub.price;
    if (sub.cycle === 'Weekly') yearly = sub.price * 52;
    return yearly;
  }

  get_sorted_by_cost(): Subscription[] {
    return [...this._subscriptions()].sort(
      (a, b) => this.to_monthly_original(b) - this.to_monthly_original(a)
    );
  }

  private recalculate_totals(): void {
    const subs = this._subscriptions();
    const monthly = subs.reduce((total, sub) => total + this.to_monthly_original(sub), 0);
    this._monthly_total.set(monthly);
    this._yearly_total.set(monthly * 12);
  }

  // ============================================
  // Import/Export (local backup)
  // ============================================

  import_data(
    subscriptions: SubscriptionCreateInput[],
    replace = true
  ): { success: boolean; count: number; error?: string } {
    try {
      const now = Date.now() / 1000;
      const new_subs: Subscription[] = subscriptions.map((input) => ({
        subscription_id: generate_local_id(),
        user_id: 'local',
        name: input.name,
        price: input.price,
        currency: input.currency,
        cycle: input.cycle,
        url: input.url,
        color: input.color || random_color(),
        created_ts: now,
        updated_ts: now,
      }));

      if (replace) {
        this._subscriptions.set(new_subs);
      } else {
        this._subscriptions.update((subs) => [...subs, ...new_subs]);
      }

      this.recalculate_totals();
      this.save_to_storage();

      return { success: true, count: new_subs.length };
    } catch (err) {
      console.error('Failed to import subscriptions:', err);
      return { success: false, count: 0, error: 'Failed to import' };
    }
  }

  export_data(): string {
    const data = {
      version: 1,
      exported_ts: Date.now() / 1000,
      subscriptions: this._subscriptions(),
    };
    return JSON.stringify(data, null, 2);
  }
}

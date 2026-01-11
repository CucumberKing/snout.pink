import { Injectable, signal, computed, inject, Injector, runInInjectionContext } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import {
  startRegistration,
  startAuthentication,
  type PublicKeyCredentialCreationOptionsJSON,
  type PublicKeyCredentialRequestOptionsJSON,
} from '@simplewebauthn/browser';

import { User } from '../../models/user.model';
import { environment } from '../../../environments/environment';
import {
  MeResponse,
  AuthBeginResponse,
  AuthCompleteResponse,
  LogoutResponse,
} from './auth-models';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly injector = inject(Injector);
  private readonly api_url = `${environment.api_url}/auth`;

  private readonly _user = signal<User | null>(null);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _initialized = signal<boolean>(false);

  readonly user = this._user.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly initialized = this._initialized.asReadonly();

  readonly is_authenticated = computed(() => this._user() !== null);

  /**
   * Check if user is authenticated on app startup
   */
  async init(): Promise<void> {
    if (this._initialized()) return;

    try {
      const me = await firstValueFrom(
        this.http.get<MeResponse>(`${this.api_url}/me`, { withCredentials: true })
      );
      this._user.set({
        user_id: me.user_id,
        display_name: me.display_name,
        default_currency: 'EUR',
        created_ts: me.created_ts,
        updated_ts: me.created_ts,
      });
      // Notify subscription service about login
      await this.notify_subscription_service_login();
    } catch {
      // Not authenticated - that's fine
      this._user.set(null);
    } finally {
      this._initialized.set(true);
    }
  }

  /**
   * Register a new user with passkey
   */
  async register(): Promise<boolean> {
    this._loading.set(true);
    this._error.set(null);

    try {
      // Step 1: Get registration options from server
      const begin_response = await firstValueFrom(
        this.http.post<AuthBeginResponse>(
          `${this.api_url}/register/begin`,
          {},
          { withCredentials: true }
        )
      );

      // Step 2: Create credential using WebAuthn
      const credential = await startRegistration({
        optionsJSON: begin_response.options as unknown as PublicKeyCredentialCreationOptionsJSON,
      });

      // Step 3: Complete registration on server
      await firstValueFrom(
        this.http.post<AuthCompleteResponse>(
          `${this.api_url}/register/complete`,
          {
            challenge_id: begin_response.challenge_id,
            credential: credential,
          },
          { withCredentials: true }
        )
      );

      // Step 4: Fetch user profile and sync subscriptions
      await this.fetch_current_user();
      await this.notify_subscription_service_login();

      return true;
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Registration failed';
      this._error.set(message);
      console.error('Registration failed:', err);
      return false;
    } finally {
      this._loading.set(false);
    }
  }

  /**
   * Login with existing passkey
   */
  async login(): Promise<boolean> {
    this._loading.set(true);
    this._error.set(null);

    try {
      // Step 1: Get authentication options from server
      const begin_response = await firstValueFrom(
        this.http.post<AuthBeginResponse>(
          `${this.api_url}/login/begin`,
          {},
          { withCredentials: true }
        )
      );

      // Step 2: Authenticate using WebAuthn
      const credential = await startAuthentication({
        optionsJSON: begin_response.options as unknown as PublicKeyCredentialRequestOptionsJSON,
      });

      // Step 3: Complete authentication on server
      await firstValueFrom(
        this.http.post<AuthCompleteResponse>(
          `${this.api_url}/login/complete`,
          {
            challenge_id: begin_response.challenge_id,
            credential: credential,
          },
          { withCredentials: true }
        )
      );

      // Step 4: Fetch user profile and sync subscriptions
      await this.fetch_current_user();
      await this.notify_subscription_service_login();

      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      this._error.set(message);
      console.error('Login failed:', err);
      return false;
    } finally {
      this._loading.set(false);
    }
  }

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    try {
      await firstValueFrom(
        this.http.post<LogoutResponse>(
          `${this.api_url}/logout`,
          {},
          { withCredentials: true }
        )
      );
    } catch {
      // Ignore errors on logout
    } finally {
      this._user.set(null);
      this.notify_subscription_service_logout();
    }
  }

  /**
   * Fetch current user profile
   */
  private async fetch_current_user(): Promise<void> {
    const me = await firstValueFrom(
      this.http.get<MeResponse>(`${this.api_url}/me`, { withCredentials: true })
    );
    this._user.set({
      user_id: me.user_id,
      display_name: me.display_name,
      default_currency: 'EUR',
      created_ts: me.created_ts,
      updated_ts: me.created_ts,
    });
  }

  /**
   * Clear any authentication error
   */
  clear_error(): void {
    this._error.set(null);
  }

  /**
   * Notify subscription service about login (lazy import to avoid circular dependency)
   */
  private async notify_subscription_service_login(): Promise<void> {
    const { SubscriptionService } = await import('../subscription.service');
    runInInjectionContext(this.injector, () => {
      const subscription_service = inject(SubscriptionService);
      subscription_service.on_login();
    });
  }

  /**
   * Notify subscription service about logout (lazy import to avoid circular dependency)
   */
  private notify_subscription_service_logout(): void {
    import('../subscription.service').then(({ SubscriptionService }) => {
      runInInjectionContext(this.injector, () => {
        const subscription_service = inject(SubscriptionService);
        subscription_service.on_logout();
      });
    });
  }
}


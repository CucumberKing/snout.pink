/**
 * Analytics Service - Umami Integration
 *
 * Loads Umami tracking script dynamically based on backend config.
 * If config is not set, tracking is disabled.
 *
 * Official Umami docs: https://umami.is/docs
 */
import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { environment } from '../../environments/environment';

declare global {
  interface Window {
    umami?: {
      track: (event_name: string, event_data?: Record<string, string | number>) => void;
    };
  }
}

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private readonly platform_id = inject(PLATFORM_ID);
  private readonly is_browser = isPlatformBrowser(this.platform_id);
  private initialized = false;

  /**
   * Initialize Umami tracking by fetching config from backend.
   * If config is not set, tracking remains disabled.
   */
  async init(): Promise<void> {
    if (!this.is_browser) {
      return;
    }

    try {
      const response = await fetch(`${environment.api_url}/app-info`);
      const config = await response.json();

      if (!config.umami_website_id || !config.umami_host_url) {
        console.log('[Analytics] Disabled - no config');
        return;
      }

      await this.load_script(config.umami_host_url, config.umami_website_id);
      this.initialized = true;
      console.log('[Analytics] Initialized');
    } catch (err) {
      console.error('[Analytics] Failed to initialize:', err);
    }
  }

  /**
   * Load Umami script dynamically.
   */
  private load_script(host_url: string, website_id: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.defer = true;
      script.src = `${host_url}/script.js`;
      script.setAttribute('data-website-id', website_id);

      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load Umami script'));

      document.head.appendChild(script);
    });
  }

  /**
   * Track a custom event.
   */
  private track(event_name: string, event_data?: Record<string, string | number>): void {
    if (!this.initialized || !window.umami) {
      return;
    }
    window.umami.track(event_name, event_data);
  }

  /**
   * Track subscription creation.
   */
  track_subscription_create(name: string): void {
    this.track('subscription_create', { name: name.substring(0, 50) });
  }

  /**
   * Track subscription update.
   */
  track_subscription_update(subscription_id: string): void {
    this.track('subscription_update', { subscription_id });
  }

  /**
   * Track subscription deletion.
   */
  track_subscription_delete(subscription_id: string): void {
    this.track('subscription_delete', { subscription_id });
  }

  /**
   * Track page view (for SPA navigation).
   */
  track_page_view(page: string): void {
    this.track('page_view', { page });
  }
}

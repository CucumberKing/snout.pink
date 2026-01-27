import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';

export interface AppInfo {
  imprint_url: string | null;
  privacy_url: string | null;
  github_url: string | null;
  umami_website_id: string | null;
  umami_host_url: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class AppInfoService {
  private readonly _app_info = signal<AppInfo | null>(null);
  private _loaded = false;

  readonly app_info = this._app_info.asReadonly();

  constructor(private readonly http: HttpClient) {}

  async load(): Promise<void> {
    if (this._loaded) return;

    try {
      const info = await this.http
        .get<AppInfo>(`${environment.api_url}/app-info`)
        .toPromise();
      this._app_info.set(info ?? null);
      this._loaded = true;
    } catch {
      // Silently fail - URLs just won't be shown
      this._loaded = true;
    }
  }

  has_any_link(): boolean {
    const info = this._app_info();
    if (!info) return false;
    return !!(info.imprint_url || info.privacy_url || info.github_url);
  }
}

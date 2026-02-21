import { Component, inject } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs';
import { AnalyticsService } from './services/analytics.service';
import { WebMcpService } from './services/webmcp.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [IonApp, IonRouterOutlet],
  template: `
    <ion-app>
      <ion-router-outlet />
    </ion-app>
  `,
  styles: [`
    :host {
      display: block;
    }
  `],
})
export class App {
  protected title = 'PinkGrid';
  private readonly sw_update = inject(SwUpdate, { optional: true });
  private readonly analytics = inject(AnalyticsService);
  private readonly webmcp = inject(WebMcpService);

  constructor() {
    // Auto-reload when new version is available
    if (this.sw_update?.isEnabled) {
      this.sw_update.versionUpdates
        .pipe(filter((evt): evt is VersionReadyEvent => evt.type === 'VERSION_READY'))
        .subscribe(() => {
          document.location.reload();
        });
    }

    this.analytics.init();
    this.webmcp.init();
  }
}

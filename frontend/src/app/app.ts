import { Component, inject } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';
import { AnalyticsService } from './services/analytics.service';

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
  private readonly analytics = inject(AnalyticsService);

  constructor() {
    this.analytics.init();
  }
}

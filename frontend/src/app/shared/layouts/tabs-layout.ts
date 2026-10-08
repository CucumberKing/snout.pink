import { Component, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import {
  IonTabs,
  IonTabBar,
  IonTabButton,
  IonIcon,
  IonLabel,
  AlertController,
} from '@ionic/angular';
import { addIcons } from 'ionicons';
import {
  listOutline,
  gridOutline,
  statsChartOutline,
  lockClosedOutline,
} from 'ionicons/icons';

import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-tabs-layout',
  imports: [RouterModule, IonTabs, IonTabBar, IonTabButton, IonIcon, IonLabel],
  templateUrl: './tabs-layout.html',
  styleUrl: './tabs-layout.scss',
})
export class TabsLayoutComponent {
  protected readonly auth_service = inject(AuthService);
  private readonly alert_controller = inject(AlertController);
  private readonly router = inject(Router);

  constructor() {
    addIcons({ listOutline, gridOutline, statsChartOutline, lockClosedOutline });
  }

  protected async on_insights_click(event: Event): Promise<void> {
    if (!this.auth_service.is_authenticated()) {
      event.preventDefault();
      event.stopPropagation();

      const alert = await this.alert_controller.create({
        header: 'Sign In Required',
        message: 'Insights are available after signing in. Sign in to sync your data and view detailed analytics.',
        buttons: [
          {
            text: 'Cancel',
            role: 'cancel',
          },
          {
            text: 'Sign In',
            handler: () => {
              this.router.navigate(['/login']);
            },
          },
        ],
      });

      await alert.present();
    }
  }
}

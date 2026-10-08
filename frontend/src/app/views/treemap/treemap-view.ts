import { Component, inject, computed } from '@angular/core';

import { IonHeader, IonToolbar, IonContent } from '@ionic/angular';

import { SubscriptionService } from '../../services/subscription.service';
import { CurrencyService } from '../../services/currency.service';
import { TreemapComponent } from './components/treemap/treemap';

@Component({
  selector: 'app-treemap-view',
  imports: [IonHeader, IonToolbar, IonContent, TreemapComponent],
  templateUrl: './treemap-view.html',
  styleUrl: './treemap-view.scss',
})
export class TreemapViewComponent {
  protected readonly subscription_service = inject(SubscriptionService);
  protected readonly currency_service = inject(CurrencyService);

  protected readonly formatted_monthly = computed(() =>
    this.currency_service.format(this.subscription_service.monthly_total())
  );

  protected readonly formatted_yearly = computed(() =>
    this.currency_service.format(this.subscription_service.yearly_total())
  );
}


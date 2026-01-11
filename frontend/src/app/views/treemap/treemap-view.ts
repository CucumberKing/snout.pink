import { Component, inject, computed, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonHeader, IonToolbar, IonContent } from '@ionic/angular/standalone';

import { SubscriptionService } from '../../services/subscription.service';
import { CurrencyService } from '../../services/currency.service';
import { TreemapComponent } from './components/treemap/treemap';

@Component({
  selector: 'app-treemap-view',
  standalone: true,
  imports: [CommonModule, IonHeader, IonToolbar, IonContent, TreemapComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
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


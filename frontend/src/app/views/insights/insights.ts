import { Component, inject, computed, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonHeader, IonToolbar, IonContent, IonIcon } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { sparklesOutline } from 'ionicons/icons';

import { SubscriptionService } from '../../services/subscription.service';
import { CurrencyService } from '../../services/currency.service';
import { Subscription } from '../../models/subscription.model';

@Component({
  selector: 'app-insights',
  standalone: true,
  imports: [CommonModule, IonHeader, IonToolbar, IonContent, IonIcon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './insights.html',
  styleUrl: './insights.scss',
})
export class InsightsComponent {
  protected readonly subscription_service = inject(SubscriptionService);
  protected readonly currency_service = inject(CurrencyService);

  protected readonly formatted_monthly = computed(() =>
    this.currency_service.format(this.subscription_service.monthly_total())
  );

  protected readonly formatted_yearly = computed(() =>
    this.currency_service.format(this.subscription_service.yearly_total())
  );

  protected readonly top_subscriptions = computed(() =>
    this.subscription_service.get_sorted_by_cost().slice(0, 3)
  );

  constructor() {
    addIcons({ sparklesOutline });
  }

  protected get_percent(sub: Subscription): number {
    const monthly = this.subscription_service.monthly_total();
    if (monthly === 0) return 0;
    const sub_monthly = this.subscription_service.to_monthly_original(sub);
    return Math.round((sub_monthly / monthly) * 100);
  }

  protected format_sub_monthly(sub: Subscription): string {
    return this.currency_service.format_original(
      this.subscription_service.to_monthly_original(sub),
      sub.currency
    );
  }
}


import { Component, input, output, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonIcon } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { createOutline, trashOutline } from 'ionicons/icons';
import { Haptics, ImpactStyle } from '@capacitor/haptics';

import { Subscription, get_color_palette } from '../../../../models/subscription.model';
import { CurrencyService } from '../../../../services/currency.service';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-subscription-card',
  standalone: true,
  imports: [CommonModule, IonIcon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './subscription-card.html',
  styleUrl: './subscription-card.scss',
})
export class SubscriptionCardComponent {
  private readonly currency_service = inject(CurrencyService);

  subscription = input.required<Subscription>();
  animation_delay = input<number>(0);

  edit = output<Subscription>();
  delete = output<Subscription>();

  constructor() {
    addIcons({ createOutline, trashOutline });
  }

  protected gradient_style(): string {
    const palette = get_color_palette(this.subscription().color);
    return `linear-gradient(180deg, ${palette.bg} 0%, ${palette.accent} 100%)`;
  }

  protected logo_url(): string {
    const url = this.subscription().url;
    if (!url) return '';
    const domain = url.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0];
    return `${environment.api_url}/logos/${domain}`;
  }

  protected formatted_price(): string {
    const sub = this.subscription();
    return this.currency_service.format_original(sub.price, sub.currency);
  }

  protected cycle_short(): string {
    const cycle = this.subscription().cycle;
    if (cycle === 'Monthly') return 'mo';
    if (cycle === 'Yearly') return 'yr';
    return 'wk';
  }

  protected async on_tap(): Promise<void> {
    await this.trigger_haptic();
    this.edit.emit(this.subscription());
  }

  protected async on_edit(event: Event): Promise<void> {
    event.stopPropagation();
    await this.trigger_haptic();
    this.edit.emit(this.subscription());
  }

  protected async on_delete(event: Event): Promise<void> {
    event.stopPropagation();
    await this.trigger_haptic();
    this.delete.emit(this.subscription());
  }

  private async trigger_haptic(): Promise<void> {
    try {
      await Haptics.impact({ style: ImpactStyle.Light });
    } catch {
      // Haptics not available
    }
  }
}


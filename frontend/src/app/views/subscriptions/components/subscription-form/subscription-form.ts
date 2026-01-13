import { Component, inject, signal, Input, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  IonHeader,
  IonToolbar,
  IonTitle,
  IonContent,
  IonButton,
  IonIcon,
  IonInput,
  IonSelect,
  IonSelectOption,
  ModalController,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { closeOutline, globeOutline, checkmarkOutline } from 'ionicons/icons';
import { Haptics, ImpactStyle } from '@capacitor/haptics';

import { SubscriptionService } from '../../../../services/subscription.service';
import { CurrencyService } from '../../../../services/currency.service';
import {
  Subscription,
  BillingCycle,
  SubscriptionColor,
  SUBSCRIPTION_COLORS,
  random_color,
  extract_dominant_color,
  rgb_to_palette_color,
} from '../../../../models/subscription.model';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-subscription-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButton,
    IonIcon,
    IonInput,
    IonSelect,
    IonSelectOption,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './subscription-form.html',
  styleUrl: './subscription-form.scss',
})
export class SubscriptionFormComponent implements OnInit {
  private readonly modal_controller = inject(ModalController);
  private readonly subscription_service = inject(SubscriptionService);
  protected readonly currency_service = inject(CurrencyService);

  @Input() mode: 'add' | 'edit' = 'add';
  @Input() subscription?: Subscription;

  protected readonly colors = SUBSCRIPTION_COLORS;
  protected readonly favicon_url = signal<string>('');
  protected readonly favicon_failed = signal(false);
  private favicon_debounce: ReturnType<typeof setTimeout> | null = null;

  protected form_data = {
    name: '',
    price: 0,
    currency: 'USD',
    cycle: 'Monthly' as BillingCycle,
    url: '',
    color: random_color(),
    earliest_cancellation_date: '',
  };

  constructor() {
    addIcons({ closeOutline, globeOutline, checkmarkOutline });
  }

  ngOnInit(): void {
    this.form_data.currency = this.currency_service.selected_currency();

    if (this.mode === 'edit' && this.subscription) {
      this.form_data = {
        name: this.subscription.name,
        price: this.subscription.price,
        currency: this.subscription.currency,
        cycle: this.subscription.cycle,
        url: this.subscription.url ?? '',
        color: this.subscription.color,
        earliest_cancellation_date: this.subscription.earliest_cancellation_ts
          ? this.ts_to_date_string(this.subscription.earliest_cancellation_ts)
          : '',
      };
      this.update_favicon();
    }
  }

  protected dismiss(): void {
    this.modal_controller.dismiss();
  }

  protected update_favicon(): void {
    if (this.favicon_debounce) {
      clearTimeout(this.favicon_debounce);
    }

    this.favicon_debounce = setTimeout(() => {
      const url = this.form_data.url;
      if (!url || url.length < 4) {
        this.favicon_url.set('');
        this.favicon_failed.set(false);
        return;
      }

      const domain = url.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0];
      if (domain.length > 3) {
        this.favicon_failed.set(false);
        this.favicon_url.set(`${environment.api_url}/logos/${domain}`);

        // Auto-fill name from domain if name is empty (only in add mode)
        if (this.mode === 'add' && !this.form_data.name.trim()) {
          const name_part = domain.split('.')[0];
          this.form_data.name = name_part.charAt(0).toUpperCase() + name_part.slice(1);
        }
      }
    }, 400);
  }

  protected on_favicon_error(): void {
    this.favicon_failed.set(true);
  }

  protected on_favicon_load(event: Event): void {
    if (this.mode !== 'add') return;

    const img = event.target as HTMLImageElement;
    const rgb = extract_dominant_color(img);

    if (rgb) {
      this.form_data.color = rgb_to_palette_color(rgb.r, rgb.g, rgb.b);
    }
  }

  protected get_gradient(color: { bg: string; accent: string }): string {
    return `linear-gradient(135deg, ${color.bg} 0%, ${color.accent} 100%)`;
  }

  protected async select_color(color_id: SubscriptionColor): Promise<void> {
    this.form_data.color = color_id;
    try {
      await Haptics.impact({ style: ImpactStyle.Light });
    } catch {
      // Haptics not available
    }
  }

  protected is_valid(): boolean {
    return this.form_data.name.trim().length > 0 && this.form_data.price > 0;
  }

  private ts_to_date_string(ts: number): string {
    const date = new Date(ts * 1000);
    return date.toISOString().split('T')[0];
  }

  private date_string_to_ts(date_str: string): number | undefined {
    if (!date_str) return undefined;
    const date = new Date(date_str);
    return Math.floor(date.getTime() / 1000);
  }

  protected clear_cancellation_date(): void {
    this.form_data.earliest_cancellation_date = '';
  }

  protected async save(): Promise<void> {
    if (!this.is_valid()) return;

    try {
      await Haptics.impact({ style: ImpactStyle.Medium });
    } catch {
      // Haptics not available
    }

    const cancellation_ts = this.date_string_to_ts(this.form_data.earliest_cancellation_date);

    if (this.mode === 'add') {
      this.subscription_service.add({
        name: this.form_data.name.trim(),
        price: this.form_data.price,
        currency: this.form_data.currency,
        cycle: this.form_data.cycle,
        url: this.form_data.url.trim() || undefined,
        color: this.form_data.color,
        earliest_cancellation_ts: cancellation_ts,
      });
    } else if (this.subscription) {
      this.subscription_service.update(this.subscription.subscription_id, {
        name: this.form_data.name.trim(),
        price: this.form_data.price,
        currency: this.form_data.currency,
        cycle: this.form_data.cycle,
        url: this.form_data.url.trim() || undefined,
        color: this.form_data.color,
        earliest_cancellation_ts: cancellation_ts,
      });
    }

    this.modal_controller.dismiss();
  }
}


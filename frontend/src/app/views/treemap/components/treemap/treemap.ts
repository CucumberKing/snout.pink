import {
  Component,
  inject,
  signal,
  computed,
  ElementRef,
  viewChild,
  afterNextRender,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonIcon } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { gridOutline } from 'ionicons/icons';

import { SubscriptionService } from '../../../../services/subscription.service';
import { CurrencyService } from '../../../../services/currency.service';
import { TreemapService } from '../../../../services/treemap.service';
import { VoronoiCell } from '../../../../models/treemap.model';
import { get_color_palette, Subscription } from '../../../../models/subscription.model';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-treemap',
  standalone: true,
  imports: [CommonModule, IonIcon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './treemap.html',
  styleUrl: './treemap.scss',
})
export class TreemapComponent {
  private readonly subscription_service = inject(SubscriptionService);
  private readonly currency_service = inject(CurrencyService);
  private readonly treemap_service = inject(TreemapService);

  private readonly container = viewChild<ElementRef<HTMLDivElement>>('container');

  protected readonly dimensions = signal({ width: 400, height: 400 });

  protected readonly cells = computed(() => {
    const dim = this.dimensions();
    this.subscription_service.subscriptions();
    return this.treemap_service.generate_voronoi_layout(dim.width, dim.height);
  });

  constructor() {
    addIcons({ gridOutline });

    afterNextRender(() => {
      this.update_dimensions();
      const observer = new ResizeObserver(() => this.update_dimensions());
      const el = this.container()?.nativeElement;
      if (el) {
        observer.observe(el);
      }
    });
  }

  private update_dimensions(): void {
    const el = this.container()?.nativeElement;
    if (el) {
      const bounds = el.getBoundingClientRect();
      this.dimensions.set({
        width: bounds.width || 400,
        height: bounds.height || 400,
      });
    }
  }

  protected get_subscription(id: string): Subscription | undefined {
    return this.subscription_service.get(id);
  }

  protected get_color(cell: VoronoiCell) {
    return get_color_palette(cell.color as any);
  }

  protected get_style(cell: VoronoiCell) {
    return this.treemap_service.get_cell_style(cell);
  }

  protected get_logo_url(url: string): string {
    const domain = url.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0];
    return `${environment.api_url}/logos/${domain}`;
  }

  protected format_price(cell: VoronoiCell): string {
    const sub = this.get_subscription(cell.id);
    if (!sub) return '';
    return this.currency_service.format_original_short(
      this.subscription_service.to_monthly_original(sub),
      sub.currency
    );
  }
}


import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  IonHeader,
  IonToolbar,
  IonContent,
  IonButton,
  IonIcon,
  IonFab,
  IonFabButton,
  IonRefresher,
  IonRefresherContent,
  ModalController,
  ViewWillEnter,
  RefresherCustomEvent,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { addOutline, settingsOutline, arrowForwardOutline, arrowDownOutline } from 'ionicons/icons';

import { SubscriptionService } from '../../services/subscription.service';
import { SubscriptionCardComponent } from './components/subscription-card/subscription-card';
import { SubscriptionFormComponent } from './components/subscription-form/subscription-form';
import { SettingsModalComponent } from './components/settings-modal/settings-modal';
import { Subscription } from '../../models/subscription.model';

@Component({
  selector: 'app-subscriptions',
  standalone: true,
  imports: [
    CommonModule,
    IonHeader,
    IonToolbar,
    IonContent,
    IonButton,
    IonIcon,
    IonFab,
    IonFabButton,
    IonRefresher,
    IonRefresherContent,
    SubscriptionCardComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './subscriptions.html',
  styleUrl: './subscriptions.scss',
})
export class SubscriptionsComponent implements ViewWillEnter {
  private readonly modal_controller = inject(ModalController);
  protected readonly subscription_service = inject(SubscriptionService);

  constructor() {
    addIcons({ addOutline, settingsOutline, arrowForwardOutline, arrowDownOutline });
  }

  ionViewWillEnter(): void {
    this.subscription_service.refresh();
  }

  protected async handle_refresh(event: RefresherCustomEvent): Promise<void> {
    await this.subscription_service.refresh();
    event.target.complete();
  }

  protected async open_add_subscription(): Promise<void> {
    const modal = await this.modal_controller.create({
      component: SubscriptionFormComponent,
      componentProps: { mode: 'add' },
      breakpoints: [0, 1],
      initialBreakpoint: 1,
      handle: true,
      showBackdrop: true,
    });
    await modal.present();
  }

  protected async open_edit_subscription(subscription: Subscription): Promise<void> {
    const modal = await this.modal_controller.create({
      component: SubscriptionFormComponent,
      componentProps: {
        mode: 'edit',
        subscription: subscription,
      },
      breakpoints: [0, 1],
      initialBreakpoint: 1,
      handle: true,
      showBackdrop: true,
    });
    await modal.present();
  }

  protected async open_settings(): Promise<void> {
    const modal = await this.modal_controller.create({
      component: SettingsModalComponent,
      breakpoints: [0, 0.75, 1],
      initialBreakpoint: 0.75,
      handle: true,
      showBackdrop: true,
    });
    await modal.present();
  }
}


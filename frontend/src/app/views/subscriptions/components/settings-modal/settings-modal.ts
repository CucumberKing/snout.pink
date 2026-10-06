import { Component, inject, signal, ChangeDetectionStrategy, viewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  IonHeader,
  IonToolbar,
  IonTitle,
  IonContent,
  IonButton,
  IonIcon,
  IonSelect,
  IonSelectOption,
  ModalController,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import {
  closeOutline,
  downloadOutline,
  cloudUploadOutline,
  checkmarkCircleOutline,
  alertCircleOutline,
  gridOutline,
  logInOutline,
  cloudDoneOutline,
  logOutOutline,
  openOutline,
  logoGithub,
} from 'ionicons/icons';
import { Haptics, ImpactStyle } from '@capacitor/haptics';

import { CurrencyService } from '../../../../services/currency.service';
import { SubscriptionService } from '../../../../services/subscription.service';
import { AuthService } from '../../../../services/auth';
import { AppInfoService } from '../../../../services/app-info.service';
import { McpAccessComponent } from '../mcp-access/mcp-access';

@Component({
  selector: 'app-settings-modal',
  imports: [
    CommonModule,
    FormsModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButton,
    IonIcon,
    IonSelect,
    IonSelectOption,
    McpAccessComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './settings-modal.html',
  styleUrl: './settings-modal.scss',
})
export class SettingsModalComponent {
  private readonly modal_controller = inject(ModalController);
  private readonly router = inject(Router);
  protected readonly currency_service = inject(CurrencyService);
  protected readonly subscription_service = inject(SubscriptionService);
  protected readonly auth_service = inject(AuthService);
  protected readonly app_info_service = inject(AppInfoService);

  protected readonly import_status = signal<{
    success: boolean;
    count: number;
    error?: string;
  } | null>(null);

  private readonly file_input = viewChild<ElementRef<HTMLInputElement>>('file_input');

  constructor() {
    addIcons({
      closeOutline,
      downloadOutline,
      cloudUploadOutline,
      checkmarkCircleOutline,
      alertCircleOutline,
      gridOutline,
      logInOutline,
      cloudDoneOutline,
      logOutOutline,
      openOutline,
      logoGithub,
    });

    // Load app info on component init
    this.app_info_service.load();
  }

  protected dismiss(): void {
    this.modal_controller.dismiss();
  }

  protected async on_currency_change(event: CustomEvent): Promise<void> {
    const value = event.detail.value;
    if (value) {
      this.currency_service.set_currency(value);
      try {
        await Haptics.impact({ style: ImpactStyle.Light });
      } catch {
        // Haptics not available
      }
    }
  }

  protected async go_to_login(): Promise<void> {
    await this.modal_controller.dismiss();
    this.router.navigate(['/login']);
  }

  protected async logout(): Promise<void> {
    await this.auth_service.logout();
  }

  protected export_data(): void {
    try {
      Haptics.impact({ style: ImpactStyle.Light });
    } catch {
      // Haptics not available
    }

    const json_str = this.subscription_service.export_data();

    const blob = new Blob([json_str], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `snout-backup-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  }

  protected trigger_import(): void {
    this.file_input()?.nativeElement.click();
  }

  protected handle_import(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target?.result as string;
      if (content) {
        try {
          const parsed = JSON.parse(content);
          const subscriptions = parsed.subscriptions ?? [];
          const result = await this.subscription_service.import_data(subscriptions, true);
          this.import_status.set(result);

          if (result.success) {
            setTimeout(() => {
              this.import_status.set(null);
            }, 3000);
          }
        } catch {
          this.import_status.set({
            success: false,
            count: 0,
            error: 'Invalid JSON file',
          });
        }
      }
    };

    reader.readAsText(file);
    input.value = '';
  }
}

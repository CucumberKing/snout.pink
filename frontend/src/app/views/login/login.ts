import { Component, inject } from '@angular/core';

import { Router } from '@angular/router';
import { IonContent, IonButton, IonIcon, IonSpinner } from '@ionic/angular';
import { addIcons } from 'ionicons';
import { fingerPrintOutline, personAddOutline, alertCircleOutline } from 'ionicons/icons';

import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-login',
  imports: [IonContent, IonButton, IonIcon, IonSpinner],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class LoginComponent {
  protected readonly auth_service = inject(AuthService);
  private readonly router = inject(Router);

  constructor() {
    addIcons({ fingerPrintOutline, personAddOutline, alertCircleOutline });
  }

  protected async login(): Promise<void> {
    this.auth_service.clear_error();
    const success = await this.auth_service.login();
    if (success) {
      this.router.navigate(['/']);
    }
  }

  protected async register(): Promise<void> {
    this.auth_service.clear_error();
    const success = await this.auth_service.register();
    if (success) {
      this.router.navigate(['/']);
    }
  }
}

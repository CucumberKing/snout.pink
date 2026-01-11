import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';

import { AuthService } from '../services/auth';

/**
 * Guard that requires authentication.
 * Redirects to /login if not authenticated.
 */
export const auth_guard: CanActivateFn = async () => {
  const auth_service = inject(AuthService);
  const router = inject(Router);

  // Initialize auth if not already done
  await auth_service.init();

  if (auth_service.is_authenticated()) {
    return true;
  }

  return router.createUrlTree(['/login']);
};

/**
 * Guard that requires NO authentication.
 * Redirects to / if already authenticated.
 */
export const guest_guard: CanActivateFn = async () => {
  const auth_service = inject(AuthService);
  const router = inject(Router);

  // Initialize auth if not already done
  await auth_service.init();

  if (!auth_service.is_authenticated()) {
    return true;
  }

  return router.createUrlTree(['/']);
};


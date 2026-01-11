import { Routes } from '@angular/router';

import { auth_guard, guest_guard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./shared/layouts/tabs-layout').then((m) => m.TabsLayoutComponent),
    children: [
      {
        path: 'subscriptions',
        loadComponent: () =>
          import('./views/subscriptions/subscriptions').then(
            (m) => m.SubscriptionsComponent
          ),
      },
      {
        path: 'treemap',
        loadComponent: () =>
          import('./views/treemap/treemap-view').then(
            (m) => m.TreemapViewComponent
          ),
      },
      {
        path: 'insights',
        loadComponent: () =>
          import('./views/insights/insights').then((m) => m.InsightsComponent),
        canActivate: [auth_guard],
      },
      {
        path: '',
        redirectTo: 'subscriptions',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./views/login/login').then((m) => m.LoginComponent),
    canActivate: [guest_guard],
  },
  {
    path: '**',
    redirectTo: '',
  },
];

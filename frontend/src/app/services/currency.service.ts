import { Injectable, signal, computed } from '@angular/core';

import {
  CURRENCIES,
  Currency,
  get_currency,
  get_currency_list,
} from '../models/currency.model';

const CURRENCY_STORAGE_KEY = 'pinkgrid_currency';

@Injectable({
  providedIn: 'root',
})
export class CurrencyService {
  private readonly _selected_currency = signal<string>(
    this.load_saved_currency()
  );

  readonly selected_currency = this._selected_currency.asReadonly();
  readonly currencies = get_currency_list();

  readonly current_currency = computed<Currency>(() => {
    return get_currency(this._selected_currency());
  });

  private load_saved_currency(): string {
    if (typeof localStorage === 'undefined') return 'EUR';
    const saved = localStorage.getItem(CURRENCY_STORAGE_KEY);
    if (saved && CURRENCIES[saved]) {
      return saved;
    }
    return 'EUR';
  }

  set_currency(code: string): void {
    if (CURRENCIES[code]) {
      this._selected_currency.set(code);
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(CURRENCY_STORAGE_KEY, code);
      }
    }
  }

  /**
   * Format a number with the given currency symbol and locale
   */
  format(amount: number, decimals = 2): string {
    const curr = this.current_currency();
    const dec = curr.is_high_value ? 0 : decimals;

    const formatted = amount.toLocaleString(curr.locale, {
      minimumFractionDigits: dec,
      maximumFractionDigits: dec,
    });

    return curr.symbol + formatted;
  }

  /**
   * Format with short notation for large numbers
   */
  format_short(amount: number): string {
    const curr = this.current_currency();

    if (amount >= 1_000_000) {
      return curr.symbol + (amount / 1_000_000).toFixed(1) + 'M';
    }
    if (amount >= 10_000) {
      return curr.symbol + (amount / 1_000).toFixed(0) + 'k';
    }
    return curr.symbol + Math.round(amount).toLocaleString(curr.locale);
  }

  /**
   * Format in original currency (not the selected one)
   */
  format_original(amount: number, currency_code: string, decimals = 2): string {
    const curr = get_currency(currency_code);
    const dec = curr.is_high_value ? 0 : decimals;

    const formatted = amount.toLocaleString(curr.locale, {
      minimumFractionDigits: dec,
      maximumFractionDigits: dec,
    });

    return curr.symbol + formatted;
  }

  /**
   * Format in original currency with short notation
   */
  format_original_short(amount: number, currency_code: string): string {
    const curr = get_currency(currency_code);

    if (amount >= 1_000_000) {
      return curr.symbol + (amount / 1_000_000).toFixed(1) + 'M';
    }
    if (amount >= 10_000) {
      return curr.symbol + (amount / 1_000).toFixed(0) + 'k';
    }
    return curr.symbol + Math.round(amount).toLocaleString(curr.locale);
  }
}

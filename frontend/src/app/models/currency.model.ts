/**
 * Currency display information.
 * No rates - all subscriptions are stored in the user's default currency.
 */
export interface Currency {
  code: string;
  symbol: string;
  name: string;
  locale: string;
  is_high_value: boolean; // Display without decimals
}

/**
 * Available currencies for display/selection.
 */
export const CURRENCIES: Record<string, Currency> = {
  USD: { code: 'USD', symbol: '$', name: 'US Dollar', locale: 'en-US', is_high_value: false },
  EUR: { code: 'EUR', symbol: '€', name: 'Euro', locale: 'de-DE', is_high_value: false },
  GBP: { code: 'GBP', symbol: '£', name: 'British Pound', locale: 'en-GB', is_high_value: false },
  JPY: { code: 'JPY', symbol: '¥', name: 'Japanese Yen', locale: 'ja-JP', is_high_value: true },
  CNY: { code: 'CNY', symbol: '¥', name: 'Chinese Yuan', locale: 'zh-CN', is_high_value: false },
  KRW: { code: 'KRW', symbol: '₩', name: 'South Korean Won', locale: 'ko-KR', is_high_value: true },
  INR: { code: 'INR', symbol: '₹', name: 'Indian Rupee', locale: 'en-IN', is_high_value: false },
  CAD: { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar', locale: 'en-CA', is_high_value: false },
  AUD: { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', locale: 'en-AU', is_high_value: false },
  CHF: { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', locale: 'de-CH', is_high_value: false },
  HKD: { code: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar', locale: 'zh-HK', is_high_value: false },
  SGD: { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar', locale: 'en-SG', is_high_value: false },
  SEK: { code: 'SEK', symbol: 'kr', name: 'Swedish Krona', locale: 'sv-SE', is_high_value: false },
  NOK: { code: 'NOK', symbol: 'kr', name: 'Norwegian Krone', locale: 'nb-NO', is_high_value: false },
  DKK: { code: 'DKK', symbol: 'kr', name: 'Danish Krone', locale: 'da-DK', is_high_value: false },
  NZD: { code: 'NZD', symbol: 'NZ$', name: 'New Zealand Dollar', locale: 'en-NZ', is_high_value: false },
  MXN: { code: 'MXN', symbol: 'MX$', name: 'Mexican Peso', locale: 'es-MX', is_high_value: false },
  BRL: { code: 'BRL', symbol: 'R$', name: 'Brazilian Real', locale: 'pt-BR', is_high_value: false },
  ZAR: { code: 'ZAR', symbol: 'R', name: 'South African Rand', locale: 'en-ZA', is_high_value: false },
  RUB: { code: 'RUB', symbol: '₽', name: 'Russian Ruble', locale: 'ru-RU', is_high_value: false },
  TRY: { code: 'TRY', symbol: '₺', name: 'Turkish Lira', locale: 'tr-TR', is_high_value: false },
  PLN: { code: 'PLN', symbol: 'zł', name: 'Polish Zloty', locale: 'pl-PL', is_high_value: false },
  THB: { code: 'THB', symbol: '฿', name: 'Thai Baht', locale: 'th-TH', is_high_value: false },
  IDR: { code: 'IDR', symbol: 'Rp', name: 'Indonesian Rupiah', locale: 'id-ID', is_high_value: true },
  MYR: { code: 'MYR', symbol: 'RM', name: 'Malaysian Ringgit', locale: 'ms-MY', is_high_value: false },
  PHP: { code: 'PHP', symbol: '₱', name: 'Philippine Peso', locale: 'en-PH', is_high_value: false },
  VND: { code: 'VND', symbol: '₫', name: 'Vietnamese Dong', locale: 'vi-VN', is_high_value: true },
  TWD: { code: 'TWD', symbol: 'NT$', name: 'Taiwan Dollar', locale: 'zh-TW', is_high_value: false },
  AED: { code: 'AED', symbol: 'د.إ', name: 'UAE Dirham', locale: 'ar-AE', is_high_value: false },
  SAR: { code: 'SAR', symbol: '﷼', name: 'Saudi Riyal', locale: 'ar-SA', is_high_value: false },
  ILS: { code: 'ILS', symbol: '₪', name: 'Israeli Shekel', locale: 'he-IL', is_high_value: false },
  CZK: { code: 'CZK', symbol: 'Kč', name: 'Czech Koruna', locale: 'cs-CZ', is_high_value: false },
  HUF: { code: 'HUF', symbol: 'Ft', name: 'Hungarian Forint', locale: 'hu-HU', is_high_value: true },
  RON: { code: 'RON', symbol: 'lei', name: 'Romanian Leu', locale: 'ro-RO', is_high_value: false },
  BGN: { code: 'BGN', symbol: 'лв', name: 'Bulgarian Lev', locale: 'bg-BG', is_high_value: false },
  HRK: { code: 'HRK', symbol: 'kn', name: 'Croatian Kuna', locale: 'hr-HR', is_high_value: false },
  CLP: { code: 'CLP', symbol: 'CLP$', name: 'Chilean Peso', locale: 'es-CL', is_high_value: true },
  COP: { code: 'COP', symbol: 'COL$', name: 'Colombian Peso', locale: 'es-CO', is_high_value: true },
  ARS: { code: 'ARS', symbol: 'ARS$', name: 'Argentine Peso', locale: 'es-AR', is_high_value: false },
  PEN: { code: 'PEN', symbol: 'S/', name: 'Peruvian Sol', locale: 'es-PE', is_high_value: false },
  EGP: { code: 'EGP', symbol: 'E£', name: 'Egyptian Pound', locale: 'ar-EG', is_high_value: false },
  NGN: { code: 'NGN', symbol: '₦', name: 'Nigerian Naira', locale: 'en-NG', is_high_value: true },
  KES: { code: 'KES', symbol: 'KSh', name: 'Kenyan Shilling', locale: 'en-KE', is_high_value: false },
  PKR: { code: 'PKR', symbol: '₨', name: 'Pakistani Rupee', locale: 'en-PK', is_high_value: true },
  BDT: { code: 'BDT', symbol: '৳', name: 'Bangladeshi Taka', locale: 'bn-BD', is_high_value: false },
  UAH: { code: 'UAH', symbol: '₴', name: 'Ukrainian Hryvnia', locale: 'uk-UA', is_high_value: false },
};

export function get_currency(code: string): Currency {
  return CURRENCIES[code] ?? CURRENCIES['USD'];
}

export function get_currency_list(): Currency[] {
  return Object.values(CURRENCIES);
}

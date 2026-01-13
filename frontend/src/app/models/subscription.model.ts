/**
 * Subscription interface - matches backend response.
 * Field names are preserved exactly as received from API.
 */
export interface Subscription {
  subscription_id: string;
  user_id: string;
  name: string;
  price: number;
  currency: string;
  cycle: BillingCycle;
  url?: string | null;
  color: SubscriptionColor;
  earliest_cancellation_ts?: number | null;
  created_ts: number;
  updated_ts: number;
}

/**
 * Input model for creating a subscription
 */
export interface SubscriptionCreateInput {
  name: string;
  price: number;
  currency: string;
  cycle: BillingCycle;
  url?: string | null;
  color: SubscriptionColor;
  earliest_cancellation_ts?: number | null;
}

/**
 * Input model for updating a subscription
 */
export interface SubscriptionUpdateInput {
  name?: string;
  price?: number;
  currency?: string;
  cycle?: BillingCycle;
  url?: string | null;
  color?: SubscriptionColor;
  earliest_cancellation_ts?: number | null;
}

/**
 * Response from list subscriptions endpoint
 */
export interface SubscriptionListResponse {
  subscriptions: Subscription[];
  total: number;
  monthly_total: number;
  yearly_total: number;
}

export type BillingCycle = 'Monthly' | 'Yearly' | 'Weekly';

export type SubscriptionColor =
  | 'purple' | 'blue' | 'cyan' | 'green'
  | 'yellow' | 'orange' | 'pink' | 'rose'
  | 'slate' | 'indigo' | 'teal' | 'amber';

export interface ColorPalette {
  id: SubscriptionColor;
  bg: string;
  accent: string;
}

export const SUBSCRIPTION_COLORS: ColorPalette[] = [
  { id: 'purple', bg: '#FAF5FF', accent: '#E9D5FF' },
  { id: 'blue', bg: '#EFF6FF', accent: '#BFDBFE' },
  { id: 'cyan', bg: '#ECFEFF', accent: '#A5F3FC' },
  { id: 'green', bg: '#F0FDF4', accent: '#BBF7D0' },
  { id: 'yellow', bg: '#FEFCE8', accent: '#FEF08A' },
  { id: 'orange', bg: '#FFF7ED', accent: '#FED7AA' },
  { id: 'pink', bg: '#FDF2F8', accent: '#FBCFE8' },
  { id: 'rose', bg: '#FFF1F2', accent: '#FECDD3' },
  { id: 'slate', bg: '#F8FAFC', accent: '#E2E8F0' },
  { id: 'indigo', bg: '#EEF2FF', accent: '#C7D2FE' },
  { id: 'teal', bg: '#F0FDFA', accent: '#99F6E4' },
  { id: 'amber', bg: '#FFFBEB', accent: '#FDE68A' },
];

export function get_color_palette(color_id: SubscriptionColor): ColorPalette {
  return SUBSCRIPTION_COLORS.find(c => c.id === color_id) ?? SUBSCRIPTION_COLORS[0];
}

export function random_color(): SubscriptionColor {
  const colors = SUBSCRIPTION_COLORS.map(c => c.id);
  return colors[Math.floor(Math.random() * colors.length)];
}

// Color extraction utilities (frontend-only, uses canvas)

interface RGB {
  r: number;
  g: number;
  b: number;
}

interface HSL {
  h: number;
  s: number;
  l: number;
}

function rgb_to_hsl(r: number, g: number, b: number): HSL {
  r /= 255;
  g /= 255;
  b /= 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;

  if (max === min) {
    return { h: 0, s: 0, l };
  }

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

  let h = 0;
  switch (max) {
    case r:
      h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      break;
    case g:
      h = ((b - r) / d + 2) / 6;
      break;
    case b:
      h = ((r - g) / d + 4) / 6;
      break;
  }

  return { h: h * 360, s, l };
}

function is_vibrant(r: number, g: number, b: number): boolean {
  const { s, l } = rgb_to_hsl(r, g, b);
  // Filter out near-black, near-white, and low saturation colors
  return s > 0.15 && l > 0.15 && l < 0.85;
}

/**
 * Extract the dominant vibrant color from an image.
 * Uses color bucketing to find the most common non-gray color.
 */
export function extract_dominant_color(img: HTMLImageElement): RGB | null {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // Scale down for performance
  const max_size = 50;
  const scale = Math.min(max_size / img.width, max_size / img.height, 1);
  canvas.width = Math.floor(img.width * scale);
  canvas.height = Math.floor(img.height * scale);

  try {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const image_data = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = image_data.data;

    // Color buckets (reduce color space for grouping)
    const bucket_size = 32;
    const buckets = new Map<string, { count: number; r: number; g: number; b: number }>();

    for (let i = 0; i < pixels.length; i += 4) {
      const r = pixels[i];
      const g = pixels[i + 1];
      const b = pixels[i + 2];
      const a = pixels[i + 3];

      // Skip transparent pixels
      if (a < 128) continue;

      // Skip non-vibrant colors
      if (!is_vibrant(r, g, b)) continue;

      // Bucket the color
      const br = Math.floor(r / bucket_size) * bucket_size;
      const bg = Math.floor(g / bucket_size) * bucket_size;
      const bb = Math.floor(b / bucket_size) * bucket_size;
      const key = `${br},${bg},${bb}`;

      const existing = buckets.get(key);
      if (existing) {
        existing.count++;
        // Average the actual colors in this bucket
        existing.r = (existing.r * (existing.count - 1) + r) / existing.count;
        existing.g = (existing.g * (existing.count - 1) + g) / existing.count;
        existing.b = (existing.b * (existing.count - 1) + b) / existing.count;
      } else {
        buckets.set(key, { count: 1, r, g, b });
      }
    }

    // Find the most common bucket
    let max_bucket: { count: number; r: number; g: number; b: number } | null = null;
    for (const bucket of buckets.values()) {
      if (!max_bucket || bucket.count > max_bucket.count) {
        max_bucket = bucket;
      }
    }

    if (!max_bucket) return null;

    return {
      r: Math.round(max_bucket.r),
      g: Math.round(max_bucket.g),
      b: Math.round(max_bucket.b),
    };
  } catch {
    // Canvas tainted by cross-origin data
    return null;
  }
}

/**
 * Map an RGB color to the closest SubscriptionColor using hue matching.
 */
export function rgb_to_palette_color(r: number, g: number, b: number): SubscriptionColor {
  const { h, s } = rgb_to_hsl(r, g, b);

  // Low saturation = slate (grayscale)
  if (s < 0.2) {
    return 'slate';
  }

  // Map hue to palette colors
  // Hue is in degrees (0-360)
  if (h >= 345 || h < 15) {
    // Red range
    return 'rose';
  } else if (h >= 15 && h < 45) {
    // Orange range
    return 'orange';
  } else if (h >= 45 && h < 70) {
    // Yellow/amber range
    return 'amber';
  } else if (h >= 70 && h < 165) {
    // Green/teal range
    return h > 140 ? 'teal' : 'green';
  } else if (h >= 165 && h < 195) {
    // Cyan range
    return 'cyan';
  } else if (h >= 195 && h < 260) {
    // Blue/indigo range
    return h > 230 ? 'indigo' : 'blue';
  } else if (h >= 260 && h < 290) {
    // Purple range
    return 'purple';
  } else {
    // Pink/magenta range (290-345)
    return 'pink';
  }
}

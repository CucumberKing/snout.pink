import { Injectable, inject } from '@angular/core';
import { hierarchy, HierarchyNode } from 'd3-hierarchy';
import { polygonCentroid, polygonArea } from 'd3-polygon';
import { voronoiTreemap } from 'd3-voronoi-treemap';

import { TreemapItem, VoronoiCell } from '../models/treemap.model';
import { SubscriptionService } from './subscription.service';

/**
 * Mulberry32 - Simple seeded PRNG for deterministic layouts
 */
function seeded_random(seed: number): () => number {
  return function() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

/**
 * Voronoi Treemap Layout Service
 * Uses d3-voronoi-treemap for proper weighted Voronoi diagram computation
 */
@Injectable({
  providedIn: 'root'
})
export class TreemapService {
  private readonly subscription_service = inject(SubscriptionService);
  
  // Corner rounding radius (0 = sharp, higher = more rounded)
  private readonly corner_radius = 6;
  
  // Margin from edges
  private readonly margin = 8;

  /**
   * Generate Voronoi treemap layout from current subscriptions
   */
  generate_voronoi_layout(width: number, height: number): VoronoiCell[] {
    const subscriptions = this.subscription_service.get_sorted_by_cost();
    
    if (subscriptions.length === 0) {
      return [];
    }

    // Convert subscriptions to treemap items
    const items: TreemapItem[] = subscriptions.map(sub => ({
      id: sub.subscription_id,
      name: sub.name,
      url: sub.url ?? undefined,
      color: sub.color,
      value: this.subscription_service.to_monthly_original(sub),
      monthly_cost: this.subscription_service.to_monthly_original(sub),
    }));

    return this.compute_voronoi(items, width, height);
  }

  /**
   * Compute weighted Voronoi treemap using d3-voronoi-treemap
   */
  private compute_voronoi(items: TreemapItem[], width: number, height: number): VoronoiCell[] {
    const total = items.reduce((sum, item) => sum + item.value, 0);
    if (total === 0) return [];

    // Create D3 hierarchy from items
    const data = { children: items };
    const root = hierarchy(data)
      .sum((d: any) => d.value || 0);

    // Create clipping polygon (rounded rectangle)
    const clip_polygon = this.create_rounded_rect_clip(width, height, 24);

    // Create and configure the Voronoi treemap
    const treemap = voronoiTreemap()
      .clip(clip_polygon)
      .prng(seeded_random(42))  // Fixed seed for deterministic layouts
      .convergenceRatio(0.001)  // 0.1% area tolerance - very precise
      .maxIterationCount(200)   // More iterations for better convergence
      .minWeightRatio(0.01);    // Allow small cells

    // Compute the layout
    treemap(root);

    // Extract leaf nodes and convert to VoronoiCell format
    const leaves = root.leaves() as HierarchyNode<any>[];
    
    return leaves.map(leaf => {
      const item = leaf.data as TreemapItem;
      const polygon = (leaf as any).polygon as [number, number][];
      
      if (!polygon || polygon.length < 3) {
        return null;
      }

      // Calculate centroid for content positioning
      const centroid = polygonCentroid(polygon);
      
      // Calculate actual area
      const area = Math.abs(polygonArea(polygon));
      
      // Calculate percentage
      const percent = (item.value / total) * 100;

      // Generate SVG path with optional corner rounding
      const path = this.polygon_to_path(polygon, this.corner_radius);

      return {
        id: item.id,
        name: item.name,
        url: item.url,
        color: item.color,
        value: item.value,
        monthly_cost: item.monthly_cost,
        polygon,
        path,
        centroid,
        area,
        percent,
      } as VoronoiCell;
    }).filter((cell): cell is VoronoiCell => cell !== null);
  }

  /**
   * Create a rounded rectangle clipping polygon
   */
  private create_rounded_rect_clip(
    width: number, 
    height: number, 
    radius: number
  ): [number, number][] {
    const points: [number, number][] = [];
    const m = this.margin;
    const w = width - m * 2;
    const h = height - m * 2;
    const r = Math.min(radius, w / 4, h / 4);
    const segments = 8; // Points per corner arc

    // Top-right corner
    for (let i = 0; i <= segments; i++) {
      const angle = -Math.PI / 2 + (i / segments) * (Math.PI / 2);
      points.push([
        m + w - r + Math.cos(angle) * r,
        m + r + Math.sin(angle) * r
      ]);
    }

    // Bottom-right corner
    for (let i = 0; i <= segments; i++) {
      const angle = 0 + (i / segments) * (Math.PI / 2);
      points.push([
        m + w - r + Math.cos(angle) * r,
        m + h - r + Math.sin(angle) * r
      ]);
    }

    // Bottom-left corner
    for (let i = 0; i <= segments; i++) {
      const angle = Math.PI / 2 + (i / segments) * (Math.PI / 2);
      points.push([
        m + r + Math.cos(angle) * r,
        m + h - r + Math.sin(angle) * r
      ]);
    }

    // Top-left corner
    for (let i = 0; i <= segments; i++) {
      const angle = Math.PI + (i / segments) * (Math.PI / 2);
      points.push([
        m + r + Math.cos(angle) * r,
        m + r + Math.sin(angle) * r
      ]);
    }

    return points;
  }

  /**
   * Convert polygon to SVG path with optional corner rounding
   * Uses quadratic Bezier curves at corners for smooth rounding
   */
  private polygon_to_path(polygon: [number, number][], radius: number): string {
    if (polygon.length < 3) return '';
    
    if (radius <= 0) {
      // Sharp corners - simple polygon path
      return 'M ' + polygon.map(p => `${p[0]},${p[1]}`).join(' L ') + ' Z';
    }

    const n = polygon.length;
    let path = '';

    for (let i = 0; i < n; i++) {
      const prev = polygon[(i - 1 + n) % n];
      const curr = polygon[i];
      const next = polygon[(i + 1) % n];

      // Vector from current to previous
      const dx1 = prev[0] - curr[0];
      const dy1 = prev[1] - curr[1];
      const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);

      // Vector from current to next
      const dx2 = next[0] - curr[0];
      const dy2 = next[1] - curr[1];
      const len2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);

      // Limit radius to half the shorter edge
      const r = Math.min(radius, len1 / 2, len2 / 2);

      // Points where the curve starts and ends
      const start_x = curr[0] + (dx1 / len1) * r;
      const start_y = curr[1] + (dy1 / len1) * r;
      const end_x = curr[0] + (dx2 / len2) * r;
      const end_y = curr[1] + (dy2 / len2) * r;

      if (i === 0) {
        path += `M ${start_x},${start_y}`;
      } else {
        path += ` L ${start_x},${start_y}`;
      }

      // Quadratic Bezier curve through the corner
      path += ` Q ${curr[0]},${curr[1]} ${end_x},${end_y}`;
    }

    // Close the path by connecting to the first curve start
    const first = polygon[0];
    const last = polygon[n - 1];
    const second = polygon[1];
    
    const dx = last[0] - first[0];
    const dy = last[1] - first[1];
    const len = Math.sqrt(dx * dx + dy * dy);
    const r = Math.min(radius, len / 2);
    const close_x = first[0] + (dx / len) * r;
    const close_y = first[1] + (dy / len) * r;
    
    path += ` L ${close_x},${close_y} Z`;

    return path;
  }

  /**
   * Calculate the inscribed circle radius for content sizing
   */
  get_inscribed_radius(cell: VoronoiCell): number {
    const polygon = cell.polygon;
    const centroid = cell.centroid;
    
    if (polygon.length < 3) return 0;

    // Find minimum distance from centroid to any edge
    let min_dist = Infinity;

    for (let i = 0; i < polygon.length; i++) {
      const p1 = polygon[i];
      const p2 = polygon[(i + 1) % polygon.length];
      
      // Distance from point to line segment
      const dist = this.point_to_segment_distance(centroid, p1, p2);
      if (dist < min_dist) min_dist = dist;
    }

    return min_dist;
  }

  /**
   * Distance from point to line segment
   */
  private point_to_segment_distance(
    point: [number, number],
    seg_start: [number, number],
    seg_end: [number, number]
  ): number {
    const [px, py] = point;
    const [x1, y1] = seg_start;
    const [x2, y2] = seg_end;

    const dx = x2 - x1;
    const dy = y2 - y1;
    const len_sq = dx * dx + dy * dy;

    if (len_sq === 0) {
      // Segment is a point
      return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
    }

    // Project point onto line
    let t = ((px - x1) * dx + (py - y1) * dy) / len_sq;
    t = Math.max(0, Math.min(1, t));

    const proj_x = x1 + t * dx;
    const proj_y = y1 + t * dy;

    return Math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2);
  }

  /**
   * Get cell styling based on inscribed circle size
   */
  get_cell_style(cell: VoronoiCell): {
    font_size_name: number;
    font_size_price: number;
    icon_size: number;
    show_name: boolean;
    show_price: boolean;
    content_width: number;
    content_height: number;
  } {
    const radius = this.get_inscribed_radius(cell);
    const diameter = radius * 2;

    // Content fits in a square inscribed in the circle
    const content_size = radius * 1.4; // ~sqrt(2) for square in circle

    const is_tiny = diameter < 50;
    const is_small = diameter < 80;

    // Scale fonts and icons based on available space
    const icon_size = Math.max(20, Math.min(56, content_size * 0.45));
    const font_size_name = Math.max(10, Math.min(16, content_size * 0.14));
    const font_size_price = Math.max(12, Math.min(28, content_size * 0.22));

    return {
      font_size_name,
      font_size_price,
      icon_size,
      show_name: !is_tiny,
      show_price: !is_tiny && !is_small,
      content_width: content_size,
      content_height: content_size,
    };
  }
}

/**
 * Input item for treemap generation
 */
export interface TreemapItem {
  id: string;
  name: string;
  url?: string;
  color: string;
  value: number;
  monthly_cost: number;
}

/**
 * Voronoi cell output from D3 treemap algorithm
 */
export interface VoronoiCell {
  // Original item data
  id: string;
  name: string;
  url?: string;
  color: string;
  value: number;
  monthly_cost: number;
  
  // Polygon coordinates from D3 (array of [x, y] tuples)
  polygon: [number, number][];
  
  // SVG path string (with optional corner rounding)
  path: string;
  
  // Centroid for content positioning
  centroid: [number, number];
  
  // Area and percentage
  area: number;
  percent: number;
}

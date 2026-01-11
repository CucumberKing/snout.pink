declare module 'd3-voronoi-treemap' {
  import { HierarchyNode } from 'd3-hierarchy';

  export interface VoronoiTreemapLayout<T> {
    (root: HierarchyNode<T>): HierarchyNode<T>;
    
    clip(): [number, number][];
    clip(polygon: [number, number][]): this;
    
    extent(): [[number, number], [number, number]];
    extent(extent: [[number, number], [number, number]]): this;
    
    size(): [number, number];
    size(size: [number, number]): this;
    
    convergenceRatio(): number;
    convergenceRatio(ratio: number): this;
    
    maxIterationCount(): number;
    maxIterationCount(count: number): this;
    
    minWeightRatio(): number;
    minWeightRatio(ratio: number): this;
    
    prng(): () => number;
    prng(prng: () => number): this;
  }

  export function voronoiTreemap<T = any>(): VoronoiTreemapLayout<T>;
}



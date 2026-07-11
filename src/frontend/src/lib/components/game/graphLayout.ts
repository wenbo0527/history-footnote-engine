/**
 * 🆕 v2.9.x W41: 板块图布局算法
 *
 * 简单 circular layout（按板块数量均匀分布在圆周）
 * - 输入：板块 ID 列表
 * - 输出：每个板块的 (x, y) 坐标 + 半径
 *
 * 不依赖 d3（轻量、零额外依赖）
 */

export interface GraphNode {
  id: string;
  x: number;
  y: number;
}

export interface GraphLayout {
  nodes: GraphNode[];
  width: number;
  height: number;
  centerX: number;
  centerY: number;
  radius: number;
}

export interface LayoutOptions {
  width?: number;     // 默认 400
  height?: number;    // 默认 300
  padding?: number;   // 默认 40
}

/**
 * 圆形布局：板块按 ID 哈希分布在圆周上
 * - 同 ID 永远在同位置（稳定）
 * - 自动适配板块数量（避免重叠）
 */
export function circularLayout(
  plateIds: string[],
  options: LayoutOptions = {}
): GraphLayout {
  const width = options.width ?? 400;
  const height = options.height ?? 300;
  const padding = options.padding ?? 40;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2 - padding;

  const n = Math.max(plateIds.length, 1);
  const nodes: GraphNode[] = plateIds.map((id, i) => {
    // 从 12 点钟方向开始（-π/2），顺时针
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    return {
      id,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  return { nodes, width, height, centerX, centerY, radius };
}

/**
 * 节点查找：按 ID 取坐标
 */
export function findNode(layout: GraphLayout, id: string): GraphNode | undefined {
  return layout.nodes.find((n) => n.id === id);
}

/**
 * 边定义：基于 neighbors
 */
export interface GraphEdge {
  from: string;
  to: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
}

export function buildEdges(
  layout: GraphLayout,
  neighbors: Record<string, string[]>
): GraphEdge[] {
  const edges: GraphEdge[] = [];
  const seen = new Set<string>();
  for (const from of Object.keys(neighbors)) {
    const fromNode = findNode(layout, from);
    if (!fromNode) continue;
    for (const to of neighbors[from]) {
      const toNode = findNode(layout, to);
      if (!toNode) continue;
      // 避免重复（A→B 和 B→A 只画一次）
      const key = [from, to].sort().join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push({
        from,
        to,
        fromX: fromNode.x,
        fromY: fromNode.y,
        toX: toNode.x,
        toY: toNode.y,
      });
    }
  }
  return edges;
}

/**
 * 估算节点尺寸（避免溢出）
 */
export function nodeRadius(plateCount: number): number {
  // 节点半径：8 (1-4) → 12 (5-8) → 14 (9+)
  if (plateCount <= 4) return 28;
  if (plateCount <= 8) return 32;
  return 36;
}

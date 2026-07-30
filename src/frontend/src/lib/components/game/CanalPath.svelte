<script lang="ts">
  /**
   * 🆕 v2.10.x — CanalPath — 京杭大运河（青色 + 水流动效）
   *
   * 视觉：
   * - 底层：青色实线（运河主体）
   * - 中层：双线（运河两岸）
   * - 顶层：白色波纹（流动效果 via stroke-dashoffset）
   */

  interface Props {
    path: string;
  }

  let { path }: Props = $props();
</script>

<g class="canal-group">
  <!-- 底层：运河阴影 -->
  <path
    class="canal-shadow"
    d={path}
    fill="none"
    stroke="rgba(44, 94, 111, 0.3)"
    stroke-width="6"
    stroke-linecap="round"
  />

  <!-- 主体：青色实线 -->
  <path
    class="canal-main"
    d={path}
    fill="none"
    stroke="#2c5e6f"
    stroke-width="3"
    stroke-linecap="round"
    opacity="0.85"
  />

  <!-- 高亮：运河中央亮线 -->
  <path
    class="canal-highlight"
    d={path}
    fill="none"
    stroke="#a8d8e0"
    stroke-width="0.8"
    stroke-linecap="round"
    opacity="0.6"
  />

  <!-- 流动波纹：虚线 + 动画 -->
  <path
    class="canal-flow"
    d={path}
    fill="none"
    stroke="#fff8e1"
    stroke-width="1.5"
    stroke-linecap="round"
    stroke-dasharray="4 8"
    opacity="0.7"
  />
</g>

<style>
  .canal-flow {
    animation: flow 2s linear infinite;
  }

  @keyframes flow {
    0% {
      stroke-dashoffset: 0;
    }
    100% {
      stroke-dashoffset: -12;
    }
  }
</style>

<script lang="ts">
  /**
   * 🆕 v2.10.x — MapOverlay — 完整地图浮层
   *
   * 用法：
   *   <MapOverlay visible={showMap} onClose={() => showMap = false} />
   *
   * 包含：
   * - 顶部 HUD (title + close)
   * - <WorldMapContainer> 全屏地图
   * - ESC 关闭
   * - 遮罩点击关闭
   */

  import WorldMapContainer from './WorldMapContainer.svelte';

  interface Props {
    visible: boolean;
    onClose?: () => void;
  }

  let { visible, onClose }: Props = $props();

  function handleMaskClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      onClose?.();
    }
  }
</script>

<svelte:window onkeydown={(e) => visible && e.key === 'Escape' && onClose?.()} />

{#if visible}
  <div
    class="map-overlay-mask"
    onclick={handleMaskClick}
    role="presentation"
  >
    <div class="map-overlay-panel" role="dialog" aria-modal="true" aria-label="江南輿圖">
      <!-- 顶部 HUD -->
      <div class="map-overlay-hud">
        <div class="hud-title">🗺️ 江南輿圖</div>
        <div class="hud-sub">明萬曆十五年（1587） · 點擊城市查看詳情</div>
        <button
          class="hud-close"
          onclick={() => onClose?.()}
          aria-label="關閉地圖"
        >×</button>
      </div>

      <!-- 地图内容 -->
      <div class="map-overlay-content">
        <WorldMapContainer />
      </div>
    </div>
  </div>
{/if}

<style>
  .map-overlay-mask {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(26, 22, 18, 0.85);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
    animation: overlay-fade-in 0.2s ease-out;
  }

  @keyframes overlay-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .map-overlay-panel {
    position: relative;
    width: 100%;
    max-width: 1280px;
    max-height: 100%;
    background: #e8d8b0;
    border: 3px solid #1a1612;
    border-radius: 4px;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .map-overlay-hud {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 24px;
    background: #1a1612;
    color: #e8d8b0;
    border-bottom: 2px solid #c44536;
  }

  .hud-title {
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 4px;
  }

  .hud-sub {
    flex: 1;
    font-family: 'STKaiti', 'KaiTi', serif;
    font-size: 12px;
    color: rgba(232, 216, 176, 0.7);
  }

  .hud-close {
    background: #c44536;
    color: #e8d8b0;
    border: none;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
    font-family: inherit;
  }

  .hud-close:hover { background: #8b1a1a; }

  .map-overlay-content {
    flex: 1;
    aspect-ratio: 1200 / 800;
    background: #e8d8b0;
    overflow: hidden;
  }
</style>
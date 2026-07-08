<script lang="ts">
  /**
   * ShareCardButton - 金句截图（v2.1 新增）
   *
   * 零依赖方案：客户端用 <canvas> 绘制可下载的 PNG 卡片
   * 不引入 html2canvas / dom-to-image（节省 40KB+）
   *
   * 卡片内容：
   *   - 顶部：万历十五年 / 角色名
   *   - 中部：截取的最强 1 句金句（标点+长句拆 2 行）
   *   - 底部：第 N 回合 · 银两 X · 织机 Y
   *   - 角标："我在万历十五年活成了自己"
   */
  import type { GameState } from '$lib/api/types';
  import { toast } from '$lib/components/design-system/Toast.svelte';

  interface Props {
    game: GameState;
    narrative: string;  // 当前叙事文本（取最强一句）
  }

  let { game, narrative }: Props = $props();

  let busy = $state(false);

  /**
   * 提取"金句"——优先 30-80 字且含标点的句子
   * 太短没分量，太长不适合分享
   */
  function extractGoldenLine(text: string): string {
    const sentences = text
      .split(/[。！？\n]/)
      .map(s => s.trim())
      .filter(s => s.length >= 20 && s.length <= 80);
    if (sentences.length === 0) {
      // fallback: 取前 60 字
      return text.slice(0, 60) + (text.length > 60 ? '……' : '');
    }
    // 优先选含"的/是/在"等实词的（避免空泛短句）
    return sentences.sort((a, b) => {
      const aHas = /[的是在有了]/.test(a) ? 1 : 0;
      const bHas = /[的是在有了]/.test(b) ? 1 : 0;
      return bHas - aHas;
    })[0];
  }

  async function handleShare() {
    if (busy || !narrative) return;
    busy = true;
    try {
      const goldenLine = extractGoldenLine(narrative);
      const dataUrl = renderCard({
        era: '万历十五年',
        role: `${game.identity === 'weaving_male' ? '织工' : game.identity === 'weaving_female' ? '织女' : game.identity === 'merchant_male' ? '牙商' : '佃户'}·${game.character.name}`,
        quote: goldenLine,
        round: game.round_current,
        stats: `💰${game.cash.toFixed(1)} · 🧵${game.looms}织机 · ⭐${game.reputation}声望`
      });

      // 触发下载
      const link = document.createElement('a');
      link.download = `万历十五年_第${game.round_current}回合.png`;
      link.href = dataUrl;
      link.click();

      // 浏览器下载完成，提示用户
      toast.success('金句卡片已生成，可分享到朋友圈');
    } catch (e) {
      toast.error('生成失败：' + (e instanceof Error ? e.message : '未知错误'));
    } finally {
      busy = false;
    }
  }

  /**
   * 核心：Canvas 2D 绘制分享卡
   * 600×800 国风水墨卡（适合微博/小红书/朋友圈 3:4 比例）
   */
  function renderCard(opts: {
    era: string;
    role: string;
    quote: string;
    round: number;
    stats: string;
  }): string {
    const W = 600;
    const H = 800;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d')!;

    // 1. 背景：宣纸色
    ctx.fillStyle = '#f5efd9';
    ctx.fillRect(0, 0, W, H);

    // 2. 边框：朱砂色
    ctx.strokeStyle = '#a52828';
    ctx.lineWidth = 4;
    ctx.strokeRect(20, 20, W - 40, H - 40);
    ctx.lineWidth = 1;
    ctx.strokeRect(32, 32, W - 64, H - 64);

    // 3. 顶部：万历十五年
    ctx.fillStyle = '#3a2a1a';
    ctx.font = 'bold 32px "Songti SC", "STSong", serif';
    ctx.textAlign = 'center';
    ctx.fillText(opts.era, W / 2, 80);

    // 副标题
    ctx.fillStyle = '#7a5a3a';
    ctx.font = '18px "Songti SC", "STSong", serif';
    ctx.fillText(`「${opts.role}」第 ${opts.round} 回合`, W / 2, 115);

    // 4. 分隔线
    ctx.strokeStyle = '#b8860b';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(120, 150);
    ctx.lineTo(W - 120, 150);
    ctx.stroke();

    // 5. 引号（左上）
    ctx.fillStyle = 'rgba(165, 40, 40, 0.25)';
    ctx.font = '120px "Songti SC", "STSong", serif';
    ctx.textAlign = 'left';
    ctx.fillText('「', 60, 240);

    // 6. 金句正文（自动换行）
    ctx.fillStyle = '#3a2a1a';
    ctx.font = '26px "Songti SC", "STSong", serif';
    ctx.textAlign = 'left';
    const lines = wrapText(ctx, opts.quote, W - 160);
    const lineH = 44;
    const startY = 270;
    lines.forEach((line, i) => {
      ctx.fillText(line, 80, startY + i * lineH);
    });

    // 7. 角标：右下
    ctx.fillStyle = '#7a5a3a';
    ctx.font = '16px "Songti SC", "STSong", serif';
    ctx.textAlign = 'right';
    ctx.fillText('— 我在万历十五年活成了自己', W - 60, H - 110);

    // 8. 底部 stats
    ctx.fillStyle = '#5a4a3a';
    ctx.font = '18px "Songti SC", "STSong", serif';
    ctx.textAlign = 'center';
    ctx.fillText(opts.stats, W / 2, H - 70);

    // 9. 印章感的小方块
    ctx.fillStyle = '#a52828';
    ctx.fillRect(W - 100, H - 150, 40, 40);
    ctx.fillStyle = '#f5efd9';
    ctx.font = 'bold 16px "Songti SC", "STSong", serif';
    ctx.textAlign = 'center';
    ctx.fillText('印', W - 80, H - 122);

    return canvas.toDataURL('image/png');
  }

  /**
   * 中文换行（按字符宽度）
   */
  function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
    const lines: string[] = [];
    let current = '';
    for (const ch of text) {
      const test = current + ch;
      if (ctx.measureText(test).width > maxWidth && current.length > 0) {
        lines.push(current);
        current = ch;
      } else {
        current = test;
      }
      // 最多 4 行
      if (lines.length >= 4) break;
    }
    if (current && lines.length < 5) lines.push(current);
    return lines;
  }
</script>

<button
  type="button"
  class="share-card-btn"
  onclick={handleShare}
  disabled={busy || !narrative}
  title="生成可分享的金句卡片"
  aria-label="生成分享卡片"
>
  <span class="share-card-icon" aria-hidden="true">📜</span>
  <span class="share-card-text">{busy ? '绘制中…' : '金句'}</span>
</button>

<style>
  .share-card-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-3);
    background: rgba(245, 239, 225, 0.1);
    border: 1px solid rgba(245, 239, 225, 0.2);
    border-radius: var(--radius-sm);
    color: var(--color-paper);
    font-family: var(--font-display);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: all var(--duration-normal) var(--ease-ink);
  }

  .share-card-btn:hover:not(:disabled) {
    background: rgba(184, 134, 11, 0.25);
    border-color: var(--color-bronze-light);
    transform: translateY(-1px);
  }

  .share-card-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .share-card-icon {
    font-size: var(--text-base);
  }
</style>

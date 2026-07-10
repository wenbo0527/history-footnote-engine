<!--
  InkBurst - 全局墨滴扩散点击反馈（🆕 v2.7+）
  -------------------------------------------------------------
  设计：挂在 layout 顶层，监听所有点击事件，在 click 位置
  生成墨水粒子向外扩散，模拟"墨在宣纸上晕开"的物理感。

  技术：Canvas 2D + 径向渐变粒子（不用 blur，性能更好）
  性能：
    - 单次 burst: 50 粒子（高端）/ 20 粒子（低端）
    - 全局封顶 80 粒
    - 自动帧率检测 < 30fps 时降级
    - prefers-reduced-motion 完全禁用
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  interface Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    life: number;
    decay: number;
    size: number;
    opacity: number;
  }

  let canvas: HTMLCanvasElement | undefined = $state();
  let ctx: CanvasRenderingContext2D | null = null;
  let particles: Particle[] = [];
  let rafId = 0;
  let dpr = 1;
  let isLowPerf = false;
  let isReducedMotion = false;
  let maxParticles = 80;
  let lastClickT = 0;

  // 节流：每 80ms 最多 1 次 burst（避免高频点击时性能雪崩）
  const THROTTLE_MS = 80;

  function onClick(e: MouseEvent) {
    if (isReducedMotion) return;
    const now = performance.now();
    if (now - lastClickT < THROTTLE_MS) return;
    lastClickT = now;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    burst(e.clientX - rect.left, e.clientY - rect.top);
  }

  function burst(x: number, y: number) {
    const count = isLowPerf ? 20 : 50;
    for (let i = 0; i < count && particles.length < maxParticles; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 0.5 + Math.random() * 1.5;
      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1.0,
        decay: 0.012 + Math.random() * 0.018,
        size: 2 + Math.random() * 4,
        opacity: 0.3 + Math.random() * 0.5
      });
    }
  }

  function resize() {
    if (!canvas || !ctx) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }

  function loop() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 读取墨色（CSS 变量）
    const inkRgb = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-ink-rgb')
      .trim() || '44, 36, 22';

    particles = particles.filter((p) => p.life > 0);
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.vx *= 0.97;
      p.vy *= 0.97;
      p.life -= p.decay;
      p.size *= 1.008;

      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
      grad.addColorStop(0, `rgba(${inkRgb}, ${p.opacity * p.life})`);
      grad.addColorStop(1, `rgba(${inkRgb}, 0)`);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    rafId = requestAnimationFrame(loop);
  }

  // 帧率检测：3 次低于 30fps 后降级
  function startPerfCheck() {
    let lastT = performance.now();
    let lowFrames = 0;
    return setInterval(() => {
      const dt = performance.now() - lastT;
      const fps = dt > 0 ? 1000 / dt : 60;
      if (fps < 30) {
        lowFrames++;
        if (lowFrames > 3 && !isLowPerf) {
          isLowPerf = true;
          maxParticles = 30;
        }
      } else {
        lowFrames = 0;
      }
      lastT = performance.now();
    }, 1000);
  }

  onMount(() => {
    if (typeof window === 'undefined') return;

    // 检查 prefers-reduced-motion
    const motionMql = window.matchMedia('(prefers-reduced-motion: reduce)');
    isReducedMotion = motionMql.matches;
    if (isReducedMotion) return;

    if (!canvas) return;
    ctx = canvas.getContext('2d');
    if (!ctx) return;

    resize();
    window.addEventListener('resize', resize);
    // capture 阶段 + passive：确保不会被子元素 stopPropagation 漏掉，且不阻塞滚动
    window.addEventListener('click', onClick, { capture: true, passive: true });
    const perfTimer = startPerfCheck();
    loop();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('click', onClick, { capture: true });
      clearInterval(perfTimer);
      cancelAnimationFrame(rafId);
    };
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      cancelAnimationFrame(rafId);
    }
  });
</script>

<canvas
  bind:this={canvas}
  class="ink-burst"
  aria-hidden="true"
></canvas>

<style>
  .ink-burst {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999; /* 高于 toast，但低于原生 alert/confirm */
  }

  @media (prefers-reduced-motion: reduce) {
    .ink-burst { display: none; }
  }
</style>

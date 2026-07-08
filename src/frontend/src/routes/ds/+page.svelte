<script lang="ts">
  /**
   * 设计系统展示页
   * /_ds
   */
  import {
    Button, Card, Dialog, Toast, toast,
    Spinner, Seal, Chapter, Divider, FirstLetter, Tabs
  } from '$lib/components/design-system';
  import type { Snippet } from 'svelte';

  interface SectionProps { title: string; children: Snippet; }
  let { children }: { children?: Snippet } = $props();

  let dialogOpen = $state(false);
  let activeTab = $state('overview');
  let loadingBtn = $state(false);

  const tabs = [
    { id: 'overview', label: '总览', icon: '📜' },
    { id: 'family',   label: '家族', icon: '👪' },
    { id: 'finance',  label: '财务', icon: '💰' },
  ];

  function simulateLoad() {
    loadingBtn = true;
    setTimeout(() => {
      loadingBtn = false;
      toast.success('保存成功');
    }, 1500);
  }
</script>

<svelte:head>
  <title>设计系统 · 历史注脚</title>
</svelte:head>

<div class="showcase">
  <header class="showcase-header">
    <Chapter title="设计系统总览" level={1} />
    <p class="showcase-subtitle">
      万历十五年 · 国风雅致 · 阶段 1 组件库
    </p>
  </header>

  <section class="demo-section">
    <h2 class="demo-section-title">Button 按钮</h2>
    <div class="demo-section-body">
      <div class="demo-row">
        <Button variant="primary">古铜按钮</Button>
        <Button variant="seal">朱砂印章</Button>
        <Button variant="ghost">透明描边</Button>
        <Button variant="subtle">米黄底色</Button>
      </div>
      <div class="demo-row">
        <Button variant="primary" size="sm">小型</Button>
        <Button variant="primary" size="md">中型</Button>
        <Button variant="primary" size="lg">大型</Button>
        <Button variant="primary" disabled>禁用</Button>
        <Button variant="primary" loading={loadingBtn} onclick={simulateLoad}>
          加载中
        </Button>
      </div>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Seal 朱砂印章</h2>
    <div class="demo-section-body">
      <div class="demo-row">
        <Seal text="行动" size="sm" />
        <Seal text="提 交" size="md" />
        <Seal text="決  定" size="lg" />
        <Seal text="PULSE" size="md" pulse />
        <Seal text="已用" size="md" ink="aged" />
      </div>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Card 卡片</h2>
    <div class="demo-section-body">
      <div class="demo-grid">
        <Card>
          <h4>宣纸卡片</h4>
          <p>默认米黄底 + 1px 古铜边</p>
        </Card>
        <Card variant="aged">
          <h4>旧纸卡片</h4>
          <p>次要色（更深一档）</p>
        </Card>
        <Card variant="dark">
          <h4>深色卡片</h4>
          <p>古铜底 + 浅字（强调）</p>
        </Card>
        <Card shadow="fold" bordered>
          <h4>折痕阴影</h4>
          <p>中等阴影（hover / 选中态）</p>
        </Card>
      </div>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Chapter 章节标题</h2>
    <div class="demo-section-body">
      <Chapter title="开  场" level={1} />
      <Chapter title="来  历" level={2} />
      <Chapter title="开 局 处 境" level={3} />
      <Chapter title="无 装 饰" ornament="none" level={3} />
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Divider 分割线</h2>
    <div class="demo-section-body">
      <Divider variant="solid" />
      <Divider variant="dashed" />
      <Divider variant="dotted" />
      <Divider variant="center" text="你脑海中的声音" />
      <Divider variant="seal" text="印  章" />
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Spinner 加载动画</h2>
    <div class="demo-section-body">
      <div class="demo-row">
        <div class="demo-stack">
          <Spinner mode="brush" />
          <span class="caption">笔触（默认）</span>
        </div>
        <div class="demo-stack">
          <Spinner mode="circle" />
          <span class="caption">圆环（传统）</span>
        </div>
        <div class="demo-stack">
          <Spinner mode="brush" size={48} />
          <span class="caption">48px</span>
        </div>
      </div>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">FirstLetter 首字下沉</h2>
    <div class="demo-section-body">
      <FirstLetter>
        十月夜来得早，沈青山从织机前站起身的时候，膝盖咯吧一响，腰像是被人拿绳子勒过一道。
        张氏在后屋哄二丫头睡着了，灶房里还有一点药味没散——是给老娘熬的最后一副。
      </FirstLetter>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Tabs 标签页</h2>
    <div class="demo-section-body">
      <Tabs bind:value={activeTab} {tabs}>
        {#if activeTab === 'overview'}
          <p>总览：万历十五年的世界</p>
        {:else if activeTab === 'family'}
          <p>家族：妻张氏、子大毛、母钱氏</p>
        {:else}
          <p>财务：现金 1.20 两，欠债 3.60 两</p>
        {/if}
      </Tabs>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Dialog 弹层</h2>
    <div class="demo-section-body">
      <div class="demo-row">
        <Button variant="seal" onclick={() => dialogOpen = true}>
          打开弹层
        </Button>
      </div>
      <Dialog
        bind:open={dialogOpen}
        onclose={() => dialogOpen = false}
        title="确认提交"
        size="sm"
      >
        <p>确定要保存当前游戏进度吗？</p>
        <p style="color: var(--color-ink-light); font-size: var(--text-sm);">
          存档后将覆盖之前的进度。
        </p>
        {#snippet footer()}
          <Button variant="ghost" onclick={() => dialogOpen = false}>取消</Button>
          <Button variant="seal" onclick={() => { dialogOpen = false; toast.success('已保存'); }}>确定</Button>
        {/snippet}
      </Dialog>
    </div>
  </section>

  <section class="demo-section">
    <h2 class="demo-section-title">Toast 通知</h2>
    <div class="demo-section-body">
      <div class="demo-row">
        <Button onclick={() => toast.success('保存成功')}>成功</Button>
        <Button onclick={() => toast.warning('存档已满')}>警告</Button>
        <Button onclick={() => toast.error('网络错误')}>错误</Button>
        <Button onclick={() => toast.info('游戏已暂停')}>信息</Button>
      </div>
    </div>
  </section>

  <Toast />
</div>

<style>
  .showcase {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-7) var(--space-fluid-md);
  }

  .showcase-header {
    text-align: center;
    margin-bottom: var(--space-8);
    padding-bottom: var(--space-6);
    border-bottom: 1px solid var(--color-ink-faint);
  }

  .showcase-subtitle {
    font-family: var(--font-body);
    font-size: var(--text-md);
    color: var(--color-ink-light);
    letter-spacing: var(--tracking-cjk);
  }

  .demo-section {
    margin-bottom: var(--space-8);
  }

  .demo-section-title {
    font-family: var(--font-display);
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-bronze-dark);
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-2);
    border-bottom: 1px dashed var(--color-ink-faint);
    letter-spacing: var(--tracking-wide);
  }

  .demo-section-body {
    padding: var(--space-5);
    background: var(--color-paper-aged);
    border: 1px solid var(--color-ink-faint);
    border-radius: var(--radius-md);
  }

  .demo-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    align-items: center;
    margin-bottom: var(--space-3);
  }
  .demo-row:last-child { margin-bottom: 0; }

  .demo-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--space-4);
  }

  .demo-stack {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
  }

  .caption {
    font-size: var(--text-xs);
    color: var(--color-ink-light);
  }
</style>

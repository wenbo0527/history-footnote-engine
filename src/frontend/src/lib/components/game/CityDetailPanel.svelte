<script lang="ts">
  /**
   * 🆕 v2.10.x — CityDetailPanel — 城市详情弹窗
   *
   * 5 城 × 7 字段数据：
   * - 等级/人口/产业/距离
   * - 史实描述
   * - 城内地点
   * - 已知人物
   * - 史实大事
   *
   * 来源：wanli_map_demo.html Phase 6.1.2 CITY_DETAILS
   */

  interface CityData {
    id: string;
    name: string;
    tier: 'fu' | 'xian';
    x: number;
    y: number;
    days: number;
    desc: string;
    meta: string;
  }

  interface Location {
    id: string;
    name: string;
    icon: string;
    desc: string;
    status?: 'current' | 'visited' | 'heard';
  }

  interface NPC {
    name: string;
    role: string;
    status: string;
    desc: string;
  }

  interface Event {
    year: string;
    name: string;
    desc: string;
  }

  interface Props {
    cityId: string;
    city: CityData | undefined;
    traveling?: boolean;
    onClose?: () => void;
    onTravel?: (cityId: string) => void;
  }

  let { cityId, city, traveling = false, onClose, onTravel }: Props = $props();

  // 5 城详细数据（从 wanli_map_demo.html CITY_DETAILS 提取）
  const CITY_DATA: Record<string, {
    population: string;
    industries: string;
    description: string;
    locations: Location[];
    npcs: NPC[];
    events: Event[];
  }> = {
    shengze: {
      population: '約 5 千戶',
      industries: '絲織業（綢市 + 牙行 + 機戶）',
      description: '蘇州府吳江縣東南要衝，明代中後期江南絲織業核心小鎮。盛澤綢聞名全國，「日出萬綢，衣被天下」之說由來已久。全鎮綢市牙行十餘家，每坊機戶不下百餘。',
      locations: [
        { id: 'home', name: '自家', icon: '🏠', desc: '三間瓦房，妻沈氏操持家務', status: 'current' },
        { id: 'weaving_house', name: '織坊', icon: '🧵', desc: '兩台織機，妻沈氏操機，子阿寶幫忙', status: 'current' },
        { id: 'tooth_market', name: '牙行', icon: '💰', desc: '綢市經紀人，撮合機戶與買家' },
        { id: 'zhou_home', name: '周大娘家', icon: '🏘️', desc: '鄰家寡婦，織娘，關係親近' },
        { id: 'tea_house', name: '茶館', icon: '🍵', desc: '鎮上消息集散地' },
        { id: 'guan_di_temple', name: '關帝廟', icon: '⛩️', desc: '鎮上香火最盛的廟宇' },
        { id: 'silk_market', name: '綢市', icon: '🏪', desc: '每日清晨開市，盛澤綢遠近聞名' },
        { id: 'river_dock', name: '運河碼頭', icon: '⚓', desc: '盛澤鎮對外水運的唯一通道' },
        { id: 'tea_market', name: '茶市', icon: '🍃', desc: '茶葉、布匹、日用雜貨交易' },
        { id: 'rice_market', name: '米行', icon: '🌾', desc: '盛澤鎮糧商聚集' },
      ],
      npcs: [
        { name: '沈氏', role: '妻', status: 'home', desc: '賢內助，操持家務與織機' },
        { name: '阿寶', role: '子', status: 'home', desc: '十二歲，幫忙織坊' },
        { name: '周大娘', role: '鄰居', status: 'heard', desc: '寡婦，織娘，關係親近' },
        { name: '牙行老闆', role: '商人', status: 'heard', desc: '綢市掮客，消息靈通' },
      ],
      events: [
        { year: '1587', name: '綢價波動', desc: '本年綢價較往年低，機戶叫苦' },
        { year: '1586', name: '水災', desc: '太湖溢水，盛澤低窪處受災' },
      ],
    },
    suzhou: {
      population: '約 50 萬',
      industries: '絲織、棉織、印染、商業、文化',
      description: '江南絲織業絕對中心，明萬曆年間民間機戶工匠超過三萬人。閶門碼頭人聲鼎沸，萬曆末年葛成抗稅罷工發生於此。應天巡撫駐地，賦稅占全國十分之一。',
      locations: [
        { id: 'weaving_bureau', name: '織造局', icon: '🏛️', desc: '皇室織造專用，管理絲織工匠' },
        { id: 'shantang_street', name: '山塘街', icon: '🏘️', desc: '虎丘山塘，水陸商街' },
        { id: 'taohuawu', name: '桃花塢', icon: '🎨', desc: '木刻年畫重鎮，萬曆年間已繁盛' },
        { id: 'changmen_dock', name: '閶門碼頭', icon: '⚓', desc: '蘇州對外水運樞紐' },
        { id: 'guanqian', name: '觀前街', icon: '🛍️', desc: '玄妙觀前商業街' },
      ],
      npcs: [
        { name: '葛成', role: '民變領袖', status: 'heard', desc: '萬曆二十九年抗稅罷工首領' },
        { name: '應天巡撫', role: '行政官', status: 'heard', desc: '駐蘇州府，管轄江南' },
      ],
      events: [
        { year: '1601', name: '葛成抗稅', desc: '蘇州機工反稅監孫隆暴動' },
        { year: '1576', name: '織造局擴建', desc: '內織染局擴大，招募工匠' },
      ],
    },
    hangzhou: {
      population: '約 35 萬',
      industries: '絲織、瓷器、茶葉、絲綢大戶',
      description: '南宋舊都，京杭運河南端。明代絲綢生產的源頭城，以大作坊為特色。張毅庵從 1 張織機發展到 20 餘張，萬曆絲商典範。',
      locations: [
        { id: 'qinghe_fang', name: '清河坊', icon: '🛍️', desc: '南宋御街，商業繁華' },
        { id: 'west_lake', name: '西湖', icon: '🏞️', desc: '杭州名勝，萬曆士大夫題詠勝地' },
        { id: 'yongjin_gate', name: '涌金門', icon: '⚓', desc: '西湖外運河碼頭' },
        { id: 'longjing_village', name: '龍井村', icon: '🍃', desc: '龍井茶產地' },
        { id: 'wulin_gate', name: '武林門', icon: '🚪', desc: '北城門，陸路要道' },
      ],
      npcs: [
        { name: '張毅庵', role: '絲商典範', status: 'heard', desc: '從 1 織機到 20 餘張的絲商傳奇' },
      ],
      events: [
        { year: '萬曆中期', name: '張毅庵崛起', desc: '絲商 1 機到 20 機的萬曆絲商典範' },
      ],
    },
    songjiang: {
      population: '約 20 萬',
      industries: '棉紡織（衣被天下）',
      description: '全國棉紡織業中心，萬曆年間「衣被天下」之說由來。黃道婆從海南帶回紡織技術，烏泥涇棉布聞名全國。',
      locations: [
        { id: 'wunijing', name: '烏泥涇', icon: '🌾', desc: '黃道婆故里，棉紡技術發源地' },
        { id: 'huangdaopo_temple', name: '黃道婆祠', icon: '⛩️', desc: '紀念黃道婆的祠廟' },
        { id: 'cotton_field', name: '棉田', icon: '🌱', desc: '松江府棉田，萬曆時期大面積種植' },
        { id: 'songjiang_weaving', name: '松江布行', icon: '🏪', desc: '棉布集散地' },
        { id: 'songjiang_market', name: '府城集市', icon: '🛍️', desc: '松江府城主要商業區' },
      ],
      npcs: [
        { name: '黃道婆', role: '棉紡祖師', status: 'heard', desc: '宋末元初從崖州帶回紡織技術' },
      ],
      events: [
        { year: '黃道婆', name: '紡織技術引進', desc: '從海南崖州帶回攪車、彈弓、紡車、織機' },
        { year: '萬曆中期', name: '松江布聞名', desc: '烏泥涇被聞名天下' },
      ],
    },
    nanjing: {
      population: '約 40-50 萬',
      industries: '官營織造、文化政治、漕運',
      description: '大明留都，天下財賦出於江南，而金陵為其會。萬曆中期科舉黃金時代，秦淮河畔繁華。',
      locations: [
        { id: 'weaving_bureau_nj', name: '織造局', icon: '🏛️', desc: '江南最大官營織造' },
        { id: 'fuzimiao', name: '夫子廟', icon: '⛩️', desc: '秦淮河畔文化中心' },
        { id: 'qinhuai_river', name: '秦淮河', icon: '🌊', desc: '南京母親河，繁華水岸' },
        { id: 'xiaoling', name: '明孝陵', icon: '🏯', desc: '明太祖朱元璋陵墓' },
        { id: 'zhonghua_gate', name: '中華門', icon: '🚪', desc: '南城門，世界最大甕城' },
      ],
      npcs: [
        { name: '南京守備', role: '宦官', status: 'heard', desc: '南京守備太監，管織造局' },
      ],
      events: [
        { year: '萬曆中期', name: '留都繁華', desc: '人口 40-50 萬，秦淮河畔燈火' },
      ],
    },
  };

  const data = $derived(CITY_DATA[cityId]);
  const tierLabel = $derived(city?.tier === 'fu' ? '府城' : '縣城');
  const distanceLabel = $derived(
    city?.days === 0 ? '盛澤本地' : `距盛澤 ${city?.days} 天`
  );

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      onClose?.();
    }
  }

  function handleTravel() {
    onTravel?.(cityId);
  }
</script>

<svelte:window on:keydown={(e) => e.key === 'Escape' && onClose?.()} />

<div
  class="city-modal-mask"
  on:click={handleBackdropClick}
  role="presentation"
>
  <div class="city-modal" role="dialog" aria-modal="true" aria-labelledby="city-modal-title">
    <div class="city-modal-header">
      <div class="city-modal-title" id="city-modal-title">
        {city?.name ?? '城市'}
      </div>
      <button class="city-modal-close" on:click={() => onClose?.()} aria-label="關閉">×</button>
    </div>

    <div class="city-modal-body">
      {#if data}
        <div class="city-modal-meta-grid">
          <div><strong>等級</strong>: {tierLabel}</div>
          <div><strong>人口</strong>: {data.population}</div>
          <div><strong>產業</strong>: {data.industries}</div>
          <div><strong>距離</strong>: {distanceLabel}</div>
        </div>

        <section class="city-modal-section">
          <h4>📜 史實描述</h4>
          <p>{data.description}</p>
        </section>

        {#if data.locations.length > 0}
          <section class="city-modal-section">
            <h4>🏛️ 城內地點（{data.locations.length}）</h4>
            <div class="location-grid">
              {#each data.locations as loc (loc.id)}
                <div class="location-card {loc.status ?? ''}">
                  <span class="location-card-icon">{loc.icon}</span>
                  <span class="location-card-name">{loc.name}</span>
                  <div class="location-card-desc">{loc.desc}</div>
                </div>
              {/each}
            </div>
          </section>
        {/if}

        {#if data.npcs.length > 0}
          <section class="city-modal-section">
            <h4>👤 已知人物（{data.npcs.length}）</h4>
            <ul class="npc-list">
              {#each data.npcs as npc (npc.name)}
                <li>
                  <span class="npc-name">{npc.name}</span>
                  <span class="npc-role">[{npc.role}]</span>
                  <span class="npc-desc">{npc.desc}</span>
                </li>
              {/each}
            </ul>
          </section>
        {/if}

        {#if data.events.length > 0}
          <section class="city-modal-section">
            <h4>📅 史實大事</h4>
            <ul class="event-list">
              {#each data.events as ev (ev.year + ev.name)}
                <li>
                  <span class="event-year">{ev.year}</span>
                  <span class="event-name">{ev.name}</span>
                  <span class="event-desc">— {ev.desc}</span>
                </li>
              {/each}
            </ul>
          </section>
        {/if}
      {:else}
        <p>未找到城市數據。</p>
      {/if}
    </div>

    <div class="city-modal-footer">
      <button class="city-modal-btn" on:click={() => onClose?.()}>關 閉</button>
      <button
        class="city-modal-btn primary"
        on:click={handleTravel}
        disabled={!city || city.days === 0 || traveling}
      >
        {#if traveling}
          啟程中…
        {:else if city?.days === 0}
          當前所在地
        {:else}
          前 往 此 城（{city?.days ?? '?'} 天）
        {/if}
      </button>
    </div>
  </div>
</div>

<style>
  .city-modal-mask {
    position: fixed;
    inset: 0;
    background: rgba(26, 22, 18, 0.6);
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(4px);
  }

  .city-modal {
    width: 90%;
    max-width: 720px;
    max-height: 86vh;
    background: #e8d8b0;
    border: 3px solid #1a1612;
    border-radius: 4px;
    font-family: 'STKaiti', 'KaiTi', serif;
    color: #1a1612;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  }

  .city-modal-header {
    padding: 16px 24px;
    background: #1a1612;
    color: #e8d8b0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #c44536;
  }

  .city-modal-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 4px;
  }

  .city-modal-close {
    background: #c44536;
    color: #e8d8b0;
    border: none;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 18px;
    font-weight: 700;
    line-height: 1;
  }

  .city-modal-close:hover { background: #8b1a1a; }

  .city-modal-body {
    padding: 20px 24px;
    overflow-y: auto;
    flex: 1;
  }

  .city-modal-section {
    margin-bottom: 20px;
  }

  .city-modal-section h4 {
    font-size: 14px;
    color: #c44536;
    margin-bottom: 8px;
    letter-spacing: 2px;
    border-bottom: 1px solid #8a6f47;
    padding-bottom: 4px;
  }

  .city-modal-section p {
    font-size: 13px;
    line-height: 1.7;
  }

  .city-modal-meta-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 24px;
    font-size: 12px;
    margin-bottom: 16px;
  }

  .city-modal-meta-grid div {
    color: #5a4a36;
  }

  .city-modal-meta-grid strong {
    color: #1a1612;
    font-weight: 600;
  }

  .location-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 8px;
  }

  .location-card {
    padding: 8px 10px;
    background: rgba(184, 146, 61, 0.1);
    border: 1px solid #8a6f47;
    border-radius: 2px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .location-card:hover {
    background: rgba(196, 69, 54, 0.15);
    border-color: #c44536;
  }

  .location-card.current {
    background: #c44536;
    color: #fff8e1;
    border-color: #8b1a1a;
  }

  .location-card-icon { font-size: 16px; margin-right: 6px; }
  .location-card-name { font-weight: 600; }
  .location-card-desc {
    font-size: 11px;
    opacity: 0.75;
    margin-top: 4px;
  }

  .npc-list, .event-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .npc-list li, .event-list li {
    padding: 6px 0;
    font-size: 12px;
    border-bottom: 1px dotted #8a6f47;
  }

  .npc-list li:last-child, .event-list li:last-child { border-bottom: none; }

  .npc-name, .event-year {
    font-weight: 600;
    color: #c44536;
    margin-right: 8px;
  }

  .npc-role, .event-name {
    color: #5a4a36;
    margin-right: 8px;
  }

  .npc-desc, .event-desc {
    font-size: 11px;
    color: #5a4a36;
  }

  .city-modal-footer {
    padding: 12px 24px;
    background: #d4c590;
    border-top: 1px solid #1a1612;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .city-modal-btn {
    padding: 8px 20px;
    background: #1a1612;
    color: #e8d8b0;
    border: none;
    font-family: inherit;
    font-size: 13px;
    cursor: pointer;
    letter-spacing: 2px;
  }

  .city-modal-btn:hover:not(:disabled) { opacity: 0.85; }
  .city-modal-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .city-modal-btn.primary { background: #c44536; }
</style>

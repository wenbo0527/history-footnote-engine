// 🆕 v1.7.3 历史注脚体验引擎 - 主脚本
// 拆分自 web_server.py（原 INDEX_HTML 内嵌 JS）
// v1.6+ 起累积：开场 + 游戏循环 + 弹层 + 移动端

let state = {
session_id: null,
identity: null,
gender: null,
era_id: "wanli1587",
// 🆕 v1.7.30 账户体系
account_id: null,
account_username: null,
account_role: "user",
};

const $main = document.getElementById("main");
const $side = document.getElementById("sidebar");

async function api(path, method = "GET", body = null) {
const opts = { method, headers: {"Content-Type": "application/json"} };
if (body) opts.body = JSON.stringify(body);
const resp = await fetch(path, opts);
return await resp.json();
}

let wizard = {
step: 1,  // 1-8
era_id: "wanli1587",
era_data: null,
gender: null,
location: null,      // 盛泽镇内的具体位置
identity_description: "",
life_expectation: "",
character: null,    // LLM 生成的人设
world_dwell: null,  // LLM 生成的世界画卷
};

const STEP_TITLES = [
"", // step 0 unused
"1. 选择时代",        // step 1
"2. 世界画卷",        // step 2
"3. 选择性别",        // step 3
"4. 选择你的位置",    // step 4 NEW
"5. 描述你的身份",    // step 5
"6. 描述期望生活",    // step 6
"7. AI 生成人设",     // step 7
"8. 确认 / 开始",     // step 8
];

// 盛泽镇内的具体位置（基于 era.json 知识条目）
const SHENGZE_LOCATIONS = [
{
  id: "family_workshop",
  name: "自家织坊",
  icon: "🏠",
  desc: "镇中巷子里的两台织机，前面是作坊，后头是灶房。你和家人住在这里。",
  traits: "最经典的小织户起点——日常就是织布、卖丝、纳粮、应付催税的里长。",
  default: true,
},
{
  id: "yaxing_east",
  name: "镇东牙行",
  icon: "🏪",
  desc: "王掌柜的牙行在镇东头，你在这里做事——帮忙看丝、议价、跑腿。",
  traits: "更接近商业。容易听到行情、客商的传闻，但议价和催账是你的日常压力。",
},
{
  id: "market_west",
  name: "镇西市集",
  icon: "🛒",
  desc: "卖桑叶、染料、丝线的市集，茶馆也在这里。",
  traits: "市井气息最浓。各种小道消息、邻居闲聊、季节变化都在这里。",
},
{
  id: "sang_field",
  name: "镇外桑田",
  icon: "🌱",
  desc: "盛泽镇外几亩桑田，靠种桑养蚕为生。",
  traits: "更农耕。节奏跟着季节走，春蚕三眠、夏剪枝、冬埋根，辛苦但稳。",
},
{
  id: "rented_house",
  name: "租住的平房",
  icon: "🏚️",
  desc: "新近迁来盛泽镇，没有自己的作坊，租了间平房安身。",
  traits: "外来者视角。对镇上的事情不熟，没有织机，但也没有历史包袱——可以从头来。",
},
{
  id: "li_jia_house",
  name: "里长老宅",
  icon: "🏛️",
  desc: "里长家的偏院，你在这里帮工（或是里长的亲戚）。",
  traits: "离权力更近——知道镇上谁家纳了税、谁家出了事，但也被里长看得紧。",
},
];

function renderStart() {
// 🆕 v1.7.30：如果已登录，直接显示存档列表；否则显示账户登录
if (restoreAccountFromStorage()) {
  showSavesList();
} else {
  showAccountLogin();
}
}

function renderWizard() {
$side.innerHTML = "<h2>开始游戏</h2>" +
  "<p style='color:#a08858;font-size:12px;line-height:1.7'>" +
  "本体验调用真实 Minimax LLM，每步调用约 5-15 秒。<br>" +
  "设计灵感来自《极乐迪斯科》：<br>" +
  "· 内在声音（你脑海中的声音）<br>" +
  "· 失败也是叙事<br>" +
  "· 行动点系统（耗尽才跳月）" +
  "</p>";
$main.innerHTML = renderWizardStep(wizard.step);
attachWizardHandlers();
}

function renderWizardStep(step) {
let html = `<div class="start-screen">`;
html += `<div style="color:#8b6f47;font-size:13px;margin-bottom:8px">${STEP_TITLES[step]}</div>`;
html += `<h1 style="font-size:32px;margin-bottom:24px">历史注脚</h1>`;

if (step === 1) {
  // Step 1: 选择时代
  html += `<div id="era-list">加载中…</div>`;
  html += `<div style="margin-top:24px"><button class="btn-secondary" onclick="renderWizardStep(0);showArchives()">继续存档</button></div>`;
} else if (step === 2) {
  // Step 2: 世界画卷
  if (!wizard.world_dwell) {
    html += `<div id="dwell-area"><span class="loading">⏳ 正在绘制「${wizard.era_data?.name || '...'}」的世界画卷…</span></div>`;
  } else {
    html += renderWorldDwell(wizard.world_dwell);
    html += `<div style="margin-top:24px;text-align:center">
      <button class="btn-primary" onclick="wizard.step=3;renderWizard()">继续</button>
    </div>`;
  }
} else if (step === 3) {
  // Step 3: 选择性别
  html += `
    <div class="form-group" style="max-width:400px">
      <label>你是男是女？</label>
      <div style="display:flex;gap:16px;margin-top:8px">
        <button class="btn-secondary" style="flex:1" onclick="wizard.gender='male';wizard.step=4;renderWizard()">男</button>
        <button class="btn-secondary" style="flex:1" onclick="wizard.gender='female';wizard.step=4;renderWizard()">女</button>
      </div>
    </div>`;
} else if (step === 4) {
  // Step 4: 选择位置（盛泽镇内的具体地点）
  html += `
    <div style="max-width:600px;margin:0 auto;text-align:left">
      <div style="text-align:center;color:#5a4a30;margin-bottom:16px;line-height:1.7">
        你的故事将发生在 <strong style="color:#8b6f47">苏州府吴江县盛泽镇</strong>——
        万历年间江南最繁华的丝织市镇之一。<br>
        选一个你的「位置」，这决定你日常接触的人和事。
      </div>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">`;
  SHENGZE_LOCATIONS.forEach(loc => {
    html += `<div class="archive-item" style="cursor:pointer" onclick='selectLocation("${loc.id}")'>
      <div class="ar-session" style="font-size:15px">${loc.icon} ${escapeHtml(loc.name)}</div>
      <div class="ar-meta" style="margin-top:4px;line-height:1.5">${escapeHtml(loc.desc)}</div>
      <div class="ar-meta" style="color:#8b6f47;margin-top:4px;font-style:italic">${escapeHtml(loc.traits)}</div>
    </div>`;
  });
  html += `</div></div>`;
} else if (step === 5) {
  // Step 5: 描述身份
  html += `
    <div class="form-group" style="max-width:500px;margin:0 auto">
      <label>你是谁？用一两句话描述你的身份/来历</label>
      <div style="margin-top:4px;color:#8b6f47;font-size:12px">
        你的位置：<strong>${getLocationName(wizard.location)}</strong>
      </div>
      <textarea id="identity_desc" rows="3" style="width:100%;padding:8px;font-size:14px;font-family:inherit;border:1px solid #8b6f47;background:#fff;border-radius:3px;margin-top:8px"
        placeholder="例：盛泽镇的小织户 / 从福建逃难来的破产绸缎商人 / 准备科举的穷书生 / 嫁到本地的年轻媳妇"></textarea>
      <div style="margin-top:8px;color:#8b6f47;font-size:12px">可选：留空将由 AI 自由发挥</div>
    </div>
    <div style="margin-top:16px;text-align:center">
      <button class="btn-secondary" onclick="wizard.step=4;renderWizard()">← 改位置</button>
      <button class="btn-primary" onclick="wizard.identity_description=document.getElementById('identity_desc').value;wizard.step=6;renderWizard()">继续</button>
    </div>`;
} else if (step === 6) {
  // Step 6: 期望生活
  html += `
    <div class="form-group" style="max-width:500px;margin:0 auto">
      <label>你想体验什么样的生活？</label>
      <textarea id="life_exp" rows="3" style="width:100%;padding:8px;font-size:14px;font-family:inherit;border:1px solid #8b6f47;background:#fff;border-radius:3px"
        placeholder="例：想体验小商贩的挣扎求生 / 想做点小生意改变命运 / 想安安稳稳养大孩子 / 想看看万历的繁华与崩塌"></textarea>
      <div style="margin-top:8px;color:#8b6f47;font-size:12px">可选：留空将由 AI 推测</div>
    </div>
    <div style="margin-top:16px;text-align:center">
      <button class="btn-secondary" onclick="wizard.step=5;renderWizard()">← 改身份</button>
      <button class="btn-primary" onclick="wizard.life_expectation=document.getElementById('life_exp').value;wizard.step=7;renderWizard()">继续</button>
    </div>`;
} else if (step === 7) {
  // Step 7: AI 生成人设
  if (!wizard.character) {
    html += `<div id="char-area"><span class="loading">⏳ AI 正在根据你的描述生成专属人设…</span></div>`;
  } else {
    html += renderCharacter(wizard.character);
    html += `<div style="margin-top:24px;text-align:center">
      <button class="btn-secondary" onclick="generateCharacter()">🔄 重新生成</button>
      <button class="btn-primary" onclick="wizard.step=8;renderWizard()">确认</button>
    </div>`;
  }
} else if (step === 8) {
  // Step 8: 确认/开始
  if (!wizard.character) {
    html += `<div class="error">请先生成人设</div>`;
  } else {
    html += renderCharacter(wizard.character);
    html += `<div style="margin-top:24px;text-align:center">
      <button class="btn-secondary" onclick="wizard.step=5;renderWizard()">← 修改身份</button>
      <button class="btn-primary" onclick="startGame()">开始游戏 →</button>
    </div>`;
  }
}

html += `</div>`;
return html;
}

function renderWorldDwell(d) {
let html = `<div style="max-width:600px;margin:0 auto;text-align:left;font-family:serif;line-height:1.9;color:#2c2416">`;
html += `<h2 style="text-align:center;color:#8b6f47;margin-bottom:24px;letter-spacing:4px">${escapeHtml(d.title || '世界画卷')}</h2>`;
(d.paragraphs || []).forEach(p => {
  html += `<p style="margin-bottom:12px;text-indent:2em">${escapeHtml(p)}</p>`;
});
if (d.key_themes && d.key_themes.length) {
  html += `<div style="margin-top:20px;padding:12px;background:rgba(139,111,71,0.1);border-radius:4px">
    <strong>时代主题：</strong>${d.key_themes.map(t => `<span class="insight-tag" style="background:#8b6f47;color:#f5f0e1;padding:2px 8px;margin:2px;border-radius:3px;display:inline-block">${escapeHtml(t)}</span>`).join('')}
  </div>`;
}
html += `</div>`;
return html;
}

function renderCharacter(c) {
let html = `<div style="max-width:600px;margin:0 auto;text-align:left;line-height:1.8">`;
html += `<h2 style="text-align:center;color:#8b6f47">${escapeHtml(c.name || '无名氏')}</h2>`;
if (c.hometown) html += `<div style="text-align:center;color:#5a4a30;font-size:14px">${escapeHtml(c.hometown)} · ${c.age || '?'}岁</div>`;
if (c.background) html += `<div style="margin:16px 0;padding:12px;background:rgba(139,111,71,0.08);border-left:3px solid #8b6f47">${escapeHtml(c.background)}</div>`;
if (c.personality) html += `<div style="margin:8px 0"><strong>性格：</strong>${escapeHtml(c.personality)}</div>`;
if (c.tics) html += `<div style="margin:8px 0"><strong>习惯：</strong>${escapeHtml(c.tics)}</div>`;
if (c.family) {
  html += `<div style="margin:8px 0"><strong>家庭：</strong><br>`;
  // 🆕 v1.6.5 修复：把英文 key 翻译成人话 + 数组格式化成自然语言
  const familyKeyLabels = {
    spouse: "妻子",
    husband: "丈夫",
    children: "子女",
    elderly: "老人",
    siblings: "兄弟姐妹",
    parents: "父母",
    father: "父亲",
    mother: "母亲",
  };
  for (const [k, v] of Object.entries(c.family)) {
    const label = familyKeyLabels[k] || k;
    let display;
    if (Array.isArray(v)) {
      display = v.map(item => escapeHtml(String(item))).join("、");
    } else if (typeof v === 'string') {
      display = escapeHtml(v);
    } else if (v && typeof v === 'object') {
      display = escapeHtml(JSON.stringify(v));
    } else {
      display = escapeHtml(String(v));
    }
    html += `· <span style="color:#5a4a30">${escapeHtml(label)}：</span>${display}<br>`;
  }
  html += `</div>`;
}
if (c.starting_situation) html += `<div style="margin:8px 0;padding:8px;background:rgba(196,168,120,0.15);border-radius:3px"><strong>开局处境：</strong>${escapeHtml(c.starting_situation)}</div>`;
if (c.voices && c.voices.length) {
  html += `<div style="margin:16px 0"><strong>🎭 内在声音：</strong>`;
  c.voices.forEach(v => {
    html += `<div style="margin:6px 0;padding:8px;background:rgba(60,48,24,0.85);color:#f0d8a0;border-radius:3px">
      <strong>${escapeHtml(v.name || '?')}</strong> <span style="color:#a08858;font-size:11px">(${escapeHtml(v.trigger || '')})</span><br>
      <span style="font-size:13px">${escapeHtml(v.description || '')}</span><br>
      <span style="color:#c4a878;font-size:12px;font-style:italic">「${escapeHtml(v.first_words || '')}」</span>
    </div>`;
  });
  html += `</div>`;
}
if (c.skills && c.skills.length) {
  html += `<div style="margin:16px 0"><strong>⚔️ 初始技能：</strong>`;
  c.skills.forEach(s => {
    const stars = "★".repeat(s.level || 1) + "☆".repeat(5 - (s.level || 1));
    html += `<div style="margin:4px 0">${stars} <strong>${escapeHtml(s.name || '?')}</strong> <span style="color:#8b6f47;font-size:12px">— ${escapeHtml(s.description || '')}</span></div>`;
  });
  html += `</div>`;
}
if (c.opening_paragraph) {
  html += `<div style="margin:16px 0;padding:12px;background:rgba(60,48,24,0.05);border-radius:3px">
    <strong>📜 开场白：</strong><br>${escapeHtml(c.opening_paragraph)}
  </div>`;
}
html += `</div>`;
return html;
}

async function attachWizardHandlers() {
if (wizard.step === 1) {
  const data = await api("/api/eras");
  const $el = document.getElementById("era-list");
  $el.innerHTML = data.eras.map(e => `
    <div class="archive-item" onclick='selectEra("${e.id}", ${JSON.stringify(e).replace(/'/g, "&#39;")})'>
      <div class="ar-session">${escapeHtml(e.name)} <span style="color:#a08858;font-size:12px">(${escapeHtml(e.year_range)})</span></div>
      <div class="ar-meta">${escapeHtml(e.description || '')}</div>
      <div class="ar-meta">可选身份：${e.identities_count} 个</div>
    </div>
  `).join("");
} else if (wizard.step === 2) {
  if (!wizard.world_dwell && !wizard._generating_dwell) {
    wizard._generating_dwell = true;
    const data = await api("/api/generate_world_dwell", "POST", {era_id: wizard.era_id});
    wizard._generating_dwell = false;
    if (data.error) {
      const $el = document.getElementById("dwell-area");
      if ($el) $el.innerHTML = "<div class='error'>" + data.error + "</div>";
    } else {
      wizard.world_dwell = data.world_dwell;
      // 用局部重渲染避免触发 attachWizardHandlers
      const $main = document.getElementById("main");
      $main.innerHTML = renderWizardStep(2);
    }
  }
} else if (wizard.step === 7) {
  if (!wizard.character && !wizard._generating_character) {
    // 不 await（fire-and-forget），让 generateCharacter 自己管理渲染
    generateCharacter().catch(err => console.error("generateCharacter failed:", err));
  }
}
}

async function selectEra(era_id, era_data) {
wizard.era_id = era_id;
wizard.era_data = era_data;
wizard.world_dwell = null;
wizard.character = null;
wizard.step = 2;
renderWizard();
}

function getLocationName(loc_id) {
if (!loc_id) return "未选择";
const loc = SHENGZE_LOCATIONS.find(l => l.id === loc_id);
return loc ? loc.icon + " " + loc.name : loc_id;
}

function getLocationDescription(loc_id) {
const loc = SHENGZE_LOCATIONS.find(l => l.id === loc_id);
return loc ? loc.desc + " " + loc.traits : "";
}

async function selectLocation(loc_id) {
wizard.location = loc_id;
wizard.character = null;  // 改了位置就重置人设
wizard.step = 5;
renderWizard();
}

async function generateCharacter() {
// 防止重入：如果已经在生成中，直接返回
if (wizard._generating_character) return;
wizard._generating_character = true;

wizard.character = null;
// 重新渲染（显示"生成中"）
if (wizard.step === 7) {
  const $main = document.getElementById("main");
  $main.innerHTML = renderWizardStep(7);
}

try {
  const data = await api("/api/generate_character", "POST", {
    era_id: wizard.era_id,
    gender: wizard.gender,
    location: wizard.location,
    location_description: getLocationDescription(wizard.location),
    identity_description: wizard.identity_description,
    life_expectation: wizard.life_expectation,
  });
  if (data.error) {
    const $el = document.getElementById("char-area");
    if ($el) $el.innerHTML = "<div class='error'>" + data.error + "</div>";
  } else {
    wizard.character = data.character;
    // 重新渲染 step 7 显示结果（不重新 attach，因为 character 已设置）
    if (wizard.step === 7) {
      const $main = document.getElementById("main");
      $main.innerHTML = renderWizardStep(7);
    }
  }
} finally {
  wizard._generating_character = false;
}
}

// 🐛 Bug #3 修复：位置 → identity 映射
// 6 个 SHENGZE_LOCATIONS 对应 era.json 6 个 identity
const LOCATION_TO_IDENTITY = {
"family_workshop": {"male": "weaving_male", "female": "weaving_female"},   // 自家织坊 → 织户
"yaxing_east":     {"male": "merchant_male", "female": "merchant_female"},// 镇东牙行 → 商人
"market_west":     {"male": "merchant_male", "female": "merchant_female"},// 镇西市集 → 商人
"sang_field":      {"male": "weaving_male", "female": "weaving_female"},   // 镇外桑田 → 织户
"rented_house":    {"male": "weaving_male", "female": "weaving_female"},   // 租住平房 → 织户（外来者）
"li_jia_house":    {"male": "scholar_male", "female": "scholar_female"},   // 里长老宅 → 读书人
};

async function startGame() {
// 🐛 Bug #3 修复：根据位置 + 性别 选择对应 identity
let identity = "default";
if (wizard.era_id === "wanli1587") {
  const map = LOCATION_TO_IDENTITY[wizard.location] || LOCATION_TO_IDENTITY["family_workshop"];
  identity = map[wizard.gender] || map["male"];
}
state.gender = wizard.gender;
state.identity = identity;
state.era_id = wizard.era_id;
state.location = wizard.location;
const data = await api("/api/start", "POST", {era_id: wizard.era_id, identity, gender: wizard.gender, character: wizard.character});
if (data.error) {
  alert(data.error);
  return;
}
state.session_id = data.session_id;
renderGame(data);
}

async function showArchives() {
let data;
try {
  data = await api("/api/archives?era_id=" + state.era_id);
} catch (e) {
  // 🆕 v1.7.13: 网络错误处理（ERR_EMPTY_RESPONSE 等）
  console.error("showArchives fetch error:", e);
  $main.innerHTML = `<div class='start-screen'><h2>存档列表</h2>
    <p style='color:#a33;text-align:center'>无法连接服务器，请稍后重试</p>
    <div style='text-align:center;margin-top:24px'>
      <button class='btn-secondary' onclick='renderStart()'>返回</button>
    </div></div>`;
  return;
}
let html = "<div class='start-screen'><h2>存档列表</h2><div style='max-width:500px;margin:0 auto;text-align:left'>";
if (data.error) {
  // 🆕 v1.7.13: 后端返回 500 等错误
  html += `<p style='color:#a33;text-align:center'>${data.error}</p>`;
} else if (!data.archives || data.archives.length === 0) {
  html += "<p style='color:#5a4a30;text-align:center'>暂无存档</p>";
} else {
  data.archives.forEach(a => {
    const sidEsc = escapeHtml(a.session_id);
    html += `<div class='archive-item'>
      <div class='ar-clickable' onclick='loadArchive("${sidEsc}")'>
        <div class='ar-session'>${sidEsc}</div>
        <div class='ar-meta'>${escapeHtml(a.current_date || '')} · 第${a.current_round}回合 · 进度摘要: ${escapeHtml(a.summary || '')}</div>
        <div class='ar-meta'>身份: ${escapeHtml(a.selected_identity || '?')} (${escapeHtml(a.player_gender || '?')})</div>
      </div>
      <button class='ar-delete-btn' onclick='deleteArchive("${sidEsc}", event)' title='删除此存档'>🗑️</button>
    </div>`;
  });
}
html += "<div style='text-align:center;margin-top:24px;display:flex;gap:12px;justify-content:center'>";
html += "<button class='btn-secondary' onclick='renderStart()'>返回</button>";
if (data.archives && data.archives.length > 0) {
  html += "<button class='btn-danger' onclick='clearAllArchives()'>🗑️ 清空全部</button>";
}
html += "</div></div>";
$main.innerHTML = html;
}

// 🆕 v1.7.14: 删除单个存档（带二次确认）
async function deleteArchive(sessionId, evt) {
if (evt) {
  evt.stopPropagation();  // 防止触发行点击
}
if (!confirm(`确定要删除存档吗？\n\n${sessionId}\n\n此操作不可撤销！`)) {
  return;
}
try {
  const data = await api("/api/archive/delete", "POST", {session_id: sessionId});
  if (data.error) {
    alert("删除失败：" + data.error);
    return;
  }
  if (data.deleted) {
    // 重新加载存档列表
    await showArchives();
  }
} catch (e) {
  console.error("deleteArchive error:", e);
  alert("删除失败：网络错误");
}
}

// 🆕 v1.7.14: 清空所有存档（带二次确认）
async function clearAllArchives() {
if (!confirm("⚠️ 确定要清空所有存档吗？\n\n此操作将永久删除此时代的所有游戏进度，不可恢复！")) {
  return;
}
if (!confirm("再确认一次：真的要清空全部存档吗？")) {
  return;
}
try {
  const data = await api("/api/archives/clear", "POST", {
    era_id: state.era_id,
    confirm: true,
  });
  if (data.error) {
    alert("清空失败：" + data.error);
    return;
  }
  alert(`已清空 ${data.deleted_count} 个存档${data.failed && data.failed.length > 0 ? `，${data.failed.length} 个失败` : ''}`);
  await showArchives();
} catch (e) {
  console.error("clearAllArchives error:", e);
  alert("清空失败：网络错误");
}
}

async function loadArchive(session_id) {
const data = await api("/api/load", "POST", {session_id});
if (data.error) {
  alert(data.error);
  return;
}
state.session_id = session_id;
state.gender = data.player_gender;
state.identity = data.selected_identity;
renderGame(data);
}

// 🆕 v1.6.2 移动端适配：iOS 键盘弹出时滚动到输入区
function setupMobileKeyboardFix() {
if (window.visualViewport) {
  const onResize = () => {
    // 当键盘弹出时，visualViewport.height < window.innerHeight
    const $inputArea = document.getElementById("input-area");
    if (!$inputArea) return;
    // 让 input-area 跟随键盘顶部位置
    const keyboardTop = window.visualViewport.height;
    const $layout = document.querySelector(".layout");
    if ($layout) {
      $layout.style.height = keyboardTop + "px";
    }
  };
  window.visualViewport.addEventListener("resize", onResize);
  window.visualViewport.addEventListener("scroll", onResize);
}
}
setupMobileKeyboardFix();

function renderGame(data) {
renderSidebar(data);
$main.innerHTML = "";
appendOpening(data);
appendInputArea();
// 🆕 v1.5.1 P0 Bug #2 修复：开局渲染 voice_options
// 如果是加载存档且有 last_voice_options，复用它；否则用预定义开局选项
if (data.last_voice_options && data.last_voice_options.length > 0) {
  appendVoiceOptions(data.last_voice_options);
} else {
  appendOpeningVoiceOptions(data);
}
// 🆕 v1.6.6 侧边栏内已集成剧情回顾按钮（不再用浮动按钮）
}

async function openRecap() {
const data = await api("/api/recap", "POST", {
  session_id: state.session_id,
  recent_count: 10,
  archive_count: 50,
});
if (data.error) {
  alert("回顾失败：" + data.error);
  return;
}
renderRecapModal(data);
}

function renderRecapModal(recap) {
// 移除旧弹层
const existing = document.getElementById("recap-modal");
if (existing) existing.remove();

const recent = recap.recent || [];
const archive = recap.archive || [];

const recentHtml = recent.length === 0 ? "<p class='recap-empty'>尚无最近叙事</p>" :
  recent.map(n => `<details class="recap-entry">
    <summary>第 ${n.round} 回合${n.summary ? ' · ' + escapeHtml(n.summary.slice(0, 30)) : ''}</summary>
    <div class="recap-body">${escapeHtml(n.narrative || '').replace(/\n/g, "<br>")}</div>
  </details>`).join("");

const archiveHtml = archive.length === 0 ? "<p class='recap-empty'>尚无早期记录</p>" :
  archive.slice().reverse().map(n => `<div class="recap-archive-item">
    <span class="recap-round">第 ${n.round} 回合</span>
    <span class="recap-summary">${escapeHtml(n.summary || n.narrative_preview || '')}</span>
  </div>`).join("");

const modal = document.createElement("div");
modal.id = "recap-modal";
modal.className = "recap-modal-overlay";
modal.onclick = (e) => {
  if (e.target === modal) closeRecap();
};
modal.innerHTML = `
  <div class="recap-modal" onclick="event.stopPropagation()">
    <div class="recap-header">
      <h2>📖 剧情回顾</h2>
      <span class="recap-meta">第 ${recap.round_number} 回合 · ${recap.current_date} · 共 ${recap.total_narratives} 条记录</span>
      <button class="recap-close" onclick="closeRecap()">×</button>
    </div>
    <div class="recap-body-content">
      <section>
        <h3>📜 最近 ${recent.length} 回合（详细）</h3>
        ${recentHtml}
      </section>
      <section>
        <h3>📚 早期记录（${archive.length} 条摘要）</h3>
        ${archiveHtml}
      </section>
    </div>
  </div>
`;
document.body.appendChild(modal);
}

function closeRecap() {
const existing = document.getElementById("recap-modal");
if (existing) existing.remove();
}

// ============================================================
// 🆕 v1.6.6 明朝名词表（侧边栏入口 + 全局 tooltip）
// ============================================================

async function openGlossary() {
// 打开名词表弹层（默认列出全部）
const data = await api("/api/glossary", "POST", {query: ""});
if (data.error) {
  alert("名词表加载失败：" + data.error);
  return;
}
renderGlossaryModal(data);
}

function renderGlossaryModal(data) {
const existing = document.getElementById("glossary-modal");
if (existing) existing.remove();

const items = (data.terms || []).map(t => `
  <div class="glossary-item" data-term="${escapeHtml(t.key)}" onclick="showTermDetail('${escapeHtml(t.key)}')">
    <span class="term-name">${escapeHtml(t.key)}</span>
    <span class="term-cat">[${escapeHtml(t.category)}]</span>
    <div class="term-def">${escapeHtml(t.definition)}</div>
  </div>
`).join("");

const modal = document.createElement("div");
modal.id = "glossary-modal";
modal.className = "recap-modal-overlay";
modal.onclick = (e) => { if (e.target === modal) closeGlossary(); };
modal.innerHTML = `
  <div class="recap-modal" onclick="event.stopPropagation()">
    <div class="recap-header">
      <h2>📚 明朝名词表</h2>
      <span class="recap-meta">共 ${data.total_in_dict} 个名词 · 显示 ${data.count} 个</span>
      <button class="recap-close" onclick="closeGlossary()">×</button>
    </div>
    <div class="recap-body-content">
      <input type="text" class="glossary-search" id="glossary-search-input"
        placeholder="🔍 搜索名词（如：牙行、湖丝、科举...）" oninput="filterGlossary(this.value)" />
      <div class="glossary-list" id="glossary-list">${items || '<p class="recap-empty">未找到匹配名词</p>'}</div>
    </div>
  </div>
`;
document.body.appendChild(modal);
// 自动 focus 搜索框
setTimeout(() => {
  const inp = document.getElementById("glossary-search-input");
  if (inp) inp.focus();
}, 100);
}

function closeGlossary() {
const existing = document.getElementById("glossary-modal");
if (existing) existing.remove();
}

// ============================================================
// 🆕 v1.6.8 玩家反馈入口（侧边栏 + 版本号点击触发）
// ============================================================
let _selectedCategory = "bug";  // 默认分类

// 🆕 v1.7.16: LLM 状态面板（Token 统计 + Fallback 历史）
async function showLLMStats() {
  let data;
  try {
    data = await api("/api/llm/stats?recent_limit=20");
  } catch (e) {
    alert("无法获取 LLM 统计：" + e.message);
    return;
  }
  // 渲染 HTML
  const totals = data.totals || {};
  const providers = data.providers || [];
  const recent = data.recent || [];
  let html = `<div class='start-screen'>
    <h2>📊 LLM 调用统计</h2>
    <div style='max-width:600px;margin:0 auto;text-align:left'>

      <div class='llm-stats-summary'>
        <div class='llm-stat-card'>
          <div class='llm-stat-label'>总调用次数</div>
          <div class='llm-stat-value'>${totals.calls || 0}</div>
        </div>
        <div class='llm-stat-card'>
          <div class='llm-stat-label'>总 Token</div>
          <div class='llm-stat-value'>${(totals.tokens || 0).toLocaleString()}</div>
        </div>
        <div class='llm-stat-card'>
          <div class='llm-stat-label'>输入 / 输出</div>
          <div class='llm-stat-value'>${(totals.input_tokens || 0).toLocaleString()} / ${(totals.output_tokens || 0).toLocaleString()}</div>
        </div>
        <div class='llm-stat-card ${totals.fallback_count > 0 ? "warn" : ""}'>
          <div class='llm-stat-label'>Fallback 次数</div>
          <div class='llm-stat-value'>${totals.fallback_count || 0}</div>
        </div>
      </div>

      <h3>按 Provider</h3>
      <table class='llm-stats-table'>
        <tr><th>Provider</th><th>调用</th><th>成功</th><th>失败</th><th>Token</th><th>平均延迟</th><th>最大延迟</th></tr>`;
  for (const p of providers) {
    const avg = p.total_calls > 0 ? Math.round(p.total_latency_ms / p.total_calls) : 0;
    html += `<tr>
      <td>${escapeHtml(p.provider)}</td>
      <td>${p.total_calls}</td>
      <td>${p.successful_calls}</td>
      <td>${p.failed_calls}</td>
      <td>${(p.total_tokens || 0).toLocaleString()}</td>
      <td>${avg}ms</td>
      <td>${p.max_latency_ms || 0}ms</td>
    </tr>`;
  }
  html += `</table>

      <h3>最近 20 次调用</h3>
      <table class='llm-stats-table llm-stats-recent'>
        <tr><th>时间</th><th>Provider</th><th>状态</th><th>Token</th><th>延迟</th></tr>`;
  for (const r of recent.slice().reverse()) {
    const ts = (r.ts || "").slice(11, 19);
    const status = r.success ? "✅" : (r.timeout ? "⏱️" : "❌");
    const fallbackTag = r.fallback ? " 🔁" : "";
    const errTip = r.error ? ` title='${escapeHtml(r.error)}'` : "";
    html += `<tr${errTip}>
      <td>${ts}</td>
      <td>${escapeHtml(r.provider || "?")}${fallbackTag}</td>
      <td>${status}</td>
      <td>${(r.total_tokens || 0).toLocaleString()}</td>
      <td>${r.latency_ms || 0}ms</td>
    </tr>`;
  }
  html += `</table>
    </div>
    <div style='text-align:center;margin-top:24px;display:flex;gap:12px;justify-content:center'>
      <button class='btn-secondary' onclick='resetLLMStats()'>重置统计</button>
      <button class='btn-secondary' onclick='renderStart()'>返回</button>
    </div>
  </div>`;
  document.getElementById("main").innerHTML = html;
}

async function resetLLMStats() {
  if (!confirm("确定要重置 LLM 统计吗？")) return;
  try {
    await api("/api/llm/reset_stats", "POST", {});
    await showLLMStats();  // 重新加载（空状态）
  } catch (e) {
    alert("重置失败：" + e.message);
  }
}

async function openFeedback() {
// 拉取分类列表
const data = await api("/api/feedback_categories", "POST", {});
if (data.error) {
  alert("反馈入口加载失败：" + data.error);
  return;
}
renderFeedbackModal(data.categories);
}

function renderFeedbackModal(categories) {
const existing = document.getElementById("feedback-modal");
if (existing) existing.remove();

const catButtons = categories.map(c => `
  <button class="feedback-cat-btn ${c.key === _selectedCategory ? 'selected' : ''}"
          data-key="${c.key}" onclick="selectFeedbackCategory('${c.key}')">
    ${c.label}
  </button>
`).join("");

const selectedCat = categories.find(c => c.key === _selectedCategory);
const placeholder = selectedCat ? selectedCat.placeholder : "描述你遇到的问题...";

const modal = document.createElement("div");
modal.id = "feedback-modal";
modal.className = "recap-modal-overlay";
modal.onclick = (e) => { if (e.target === modal) closeFeedback(); };
modal.innerHTML = `
  <div class="recap-modal" onclick="event.stopPropagation()" style="max-width:560px">
    <div class="recap-header">
      <h2>🐛 问题反馈</h2>
      <span class="recap-meta">${categories.length} 种分类 · 自动收集上下文</span>
      <button class="recap-close" onclick="closeFeedback()">×</button>
    </div>
    <div class="recap-body-content">
      <div class="feedback-form" id="feedback-form-body">
        <label style="font-size:13px;color:#5a3e1f;font-weight:bold">问题分类：</label>
        <div class="feedback-categories">${catButtons}</div>
        <label style="font-size:13px;color:#5a3e1f;font-weight:bold">详细描述：</label>
        <textarea class="feedback-textarea" id="feedback-description"
          placeholder="${escapeHtml(placeholder)}"></textarea>
        <div class="feedback-context-note" id="feedback-context-note">
          📋 自动收集：当前回合、日期、浏览器、屏幕尺寸、最近 3 个玩家操作。<br>
          你的反馈将包含一个会话 ID（不会包含个人身份信息）。
        </div>
        <div class="feedback-submit-row">
          <button class="sidebar-action-btn" style="background:transparent;color:#5a3e1f;width:auto;display:inline-block"
            onclick="closeFeedback()">取消</button>
          <button class="feedback-submit-btn" id="feedback-submit-btn" onclick="submitFeedback()">提交反馈</button>
        </div>
      </div>
    </div>
  </div>
`;
document.body.appendChild(modal);
}

function closeFeedback() {
const existing = document.getElementById("feedback-modal");
if (existing) existing.remove();
}

function selectFeedbackCategory(key) {
_selectedCategory = key;
// 更新 UI
document.querySelectorAll(".feedback-cat-btn").forEach(btn => {
  btn.classList.toggle("selected", btn.dataset.key === key);
});
// 更新 placeholder（异步从服务端拉取最新 placeholder）
api("/api/feedback_categories", "POST", {}).then(data => {
  if (data.categories) {
    const cat = data.categories.find(c => c.key === key);
    if (cat) {
      const textarea = document.getElementById("feedback-description");
      if (textarea) textarea.placeholder = cat.placeholder;
    }
  }
});
}

async function submitFeedback() {
const desc = document.getElementById("feedback-description").value.trim();
if (!desc) {
  alert("请填写描述");
  return;
}
if (desc.length < 5) {
  alert("描述过短（至少 5 字符）");
  return;
}

// 收集上下文
const context = {
  round: state.round || 0,
  date: state.current_date || "unknown",
  user_agent: navigator.userAgent,
  screen: `${window.screen.width}x${window.screen.height}`,
  viewport: `${window.innerWidth}x${window.innerHeight}`,
  timestamp: new Date().toISOString(),
  // 玩家最近 3 个输入（从 state 读）
  recent_inputs: (state.recent_inputs || []).slice(-3),
};

// 禁用按钮
const btn = document.getElementById("feedback-submit-btn");
btn.disabled = true;
btn.textContent = "提交中...";

try {
  const result = await api("/api/feedback", "POST", {
    session_id: state.session_id || "",
    category: _selectedCategory,
    description: desc,
    context: context,
  });

  if (result.error) {
    alert("提交失败：" + result.error);
    btn.disabled = false;
    btn.textContent = "提交反馈";
    return;
  }

  // 成功
  const formBody = document.getElementById("feedback-form-body");
  formBody.innerHTML = `
    <div class="feedback-success">
      ✅ 反馈已收到！<br>
      <small>ID: ${result.id}</small><br>
      <small style="color:#8b6f47">开发团队会查看并处理。</small>
    </div>
    <div class="feedback-submit-row">
      <button class="feedback-submit-btn" onclick="closeFeedback()">关闭</button>
    </div>
  `;
} catch (e) {
  alert("网络错误：" + e.message);
  btn.disabled = false;
  btn.textContent = "提交反馈";
}
}

// 🆕 v1.6.8 页面加载时拉取版本信息更新 badge
async function loadVersionBadge() {
try {
  const info = await api("/api/version", "POST", {});
  if (info && info.full_label) {
    const textEl = document.querySelector("#version-badge .version-text");
    if (textEl) textEl.textContent = info.full_label;
  }
} catch (e) {
  // 静默失败，使用 HTML 模板里的默认值
}
}
// 在页面加载完成后调用
if (document.readyState === "loading") {
document.addEventListener("DOMContentLoaded", loadVersionBadge);
} else {
loadVersionBadge();
}

async function filterGlossary(query) {
// 客户端过滤：避免每次都打 API
const data = await api("/api/glossary", "POST", {query: query});
const list = document.getElementById("glossary-list");
if (!list) return;
if (data.error || !data.terms) {
  list.innerHTML = '<p class="recap-empty">加载失败</p>';
  return;
}
list.innerHTML = data.terms.map(t => `
  <div class="glossary-item" data-term="${escapeHtml(t.key)}" onclick="showTermDetail('${escapeHtml(t.key)}')">
    <span class="term-name">${escapeHtml(t.key)}</span>
    <span class="term-cat">[${escapeHtml(t.category)}]</span>
    <div class="term-def">${escapeHtml(t.definition)}</div>
  </div>
`).join("") || '<p class="recap-empty">未找到匹配名词</p>';
}

async function showTermDetail(key) {
const data = await api("/api/glossary", "POST", {term: key});
if (data.error) {
  alert("未找到：" + key);
  return;
}
// 标记已读
if (state.session_id) {
  api("/api/mark_term_seen", "POST", {
    session_id: state.session_id,
    term: key,
  }).catch(() => {});
}
// 显示弹层
showTermTooltipInline(data);
}

function showTermTooltipInline(termData) {
const existing = document.getElementById("term-detail-modal");
if (existing) existing.remove();

const example = termData.example ? `<div class="term-example">例：${escapeHtml(termData.example)}</div>` : "";
const related = (termData.related && termData.related.length)
  ? `<div class="term-related">相关：${termData.related.map(r => `<span class="term-name" style="font-size:12px">${escapeHtml(r)}</span>`).join("、")}</div>`
  : "";

const modal = document.createElement("div");
modal.id = "term-detail-modal";
modal.className = "recap-modal-overlay";
modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
modal.innerHTML = `
  <div class="recap-modal" onclick="event.stopPropagation()" style="max-width:480px">
    <div class="recap-header">
      <h2><span class="term-name">${escapeHtml(termData.key)}</span> <span class="term-cat">[${escapeHtml(termData.category)}]</span></h2>
      <button class="recap-close" onclick="document.getElementById('term-detail-modal').remove()">×</button>
    </div>
    <div class="recap-body-content">
      <div class="term-def" style="font-size:14px;line-height:1.7;color:#2c2416">${escapeHtml(termData.definition)}</div>
      ${example}
      ${related}
      <div style="margin-top:16px;text-align:right">
        <button class="sidebar-action-btn" style="background:rgba(139,111,71,0.15);color:#5a3e1f;display:inline-block;width:auto"
          onclick="document.getElementById('term-detail-modal').remove()">知道了</button>
      </div>
    </div>
  </div>
`;
document.body.appendChild(modal);
}

// 给叙事中所有 .term-new 元素绑定 tooltip 事件
function attachTermTooltips() {
document.querySelectorAll(".term-new").forEach(el => {
  if (el.dataset.tooltipBound) return;
  el.dataset.tooltipBound = "1";
  el.addEventListener("mouseenter", async (e) => {
    const term = el.dataset.term;
    if (!term) return;
    const data = await api("/api/glossary", "POST", {term: term});
    if (data.error) return;
    // 标记已读
    if (state.session_id) {
      api("/api/mark_term_seen", "POST", {
        session_id: state.session_id,
        term: term,
      }).catch(() => {});
    }
    // 显示 tooltip
    let tooltip = document.getElementById("term-tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = "term-tooltip";
      tooltip.className = "term-tooltip";
      document.body.appendChild(tooltip);
    }
    const example = data.example ? `<div class="term-example">例：${escapeHtml(data.example)}</div>` : "";
    tooltip.innerHTML = `
      <div class="term-name">${escapeHtml(data.key)} <span class="term-cat">[${escapeHtml(data.category)}]</span></div>
      <div class="term-def">${escapeHtml(data.definition)}</div>
      ${example}
    `;
    // 定位
    const rect = el.getBoundingClientRect();
    tooltip.style.left = (rect.left + window.scrollX) + "px";
    tooltip.style.top = (rect.bottom + window.scrollY + 6) + "px";
    tooltip.style.display = "block";
  });
  el.addEventListener("mouseleave", () => {
    const tooltip = document.getElementById("term-tooltip");
    if (tooltip) tooltip.style.display = "none";
  });
});
}

function appendOpeningVoiceOptions(data) {
// 🐛 v1.5.1 P0 Bug #2 修复：开局的 DE 风格选项（基于开局处境）
// 这些是"你脑海中的声音"——基于玩家人设给 2-3 个开局方向
const cc = data.custom_character || {};
const openingOptions = [
  {
    voice_id: "voice_observe",
    voice_name: "先看看家里情况",
    intent_text: "我先扫一眼家里有什么，银钱还剩多少，灶房是什么光景",
  },
  {
    voice_id: "voice_action",
    voice_name: "出门找活路",
    intent_text: "我去牙行问问最近有没有活计可接",
  },
  {
    voice_id: "voice_moral",
    voice_name: "先顾眼前",
    intent_text: "我想想今天的米缸还够不够，今天必须先吃饱",
  },
];
appendVoiceOptions(openingOptions);
}

function appendOpening(data) {
const nh = data.recent_narratives || [];
nh.forEach(n => appendNarrative(n, null));
}

function appendNarrative(n, lastMeta) {
const div = document.createElement("div");
div.className = "narrative";
// 🆕 v1.7.9 兼容：n 可能是 string（last_narrative 纯文本）或 object（recent_narratives dict）
if (typeof n === "string") {
  n = { round: lastMeta?.round || "?", summary: lastMeta?.summary || "", narrative: n };
}
let tag = `<div class="round-tag">第${n.round}回合 · ${n.summary || ""}</div>`;
if (lastMeta && lastMeta.player_input) {
  tag = `<div class="player-echo">> ${escapeHtml(lastMeta.player_input)}</div>` + tag;
}
// 🆕 v1.5+：describe/intent_type 标签
if (lastMeta && lastMeta.intent_type === "describe") {
  tag += `<div class="describe-tag">🪞 描述（你在补充身份/处境，不消耗行动点）</div>`;
} else if (lastMeta && lastMeta.intent_type === "voice") {
  tag += `<div class="describe-tag">🎭 内在声音（${escapeHtml(state._selectedVoice?.voice_name || '?')}）</div>`;
} else if (lastMeta && lastMeta.is_action === false) {
  tag += `<div class="action-tag inquire">💬 问询（不消耗行动点）</div>`;
} else if (lastMeta && lastMeta.time_cost !== undefined) {
  const cost = lastMeta.time_cost;
  const costLabel = cost === 0 ? "瞬时" : cost === 1 ? "半日" : cost === 2 ? "一日" : cost === 3 ? "数日" : `${cost}点`;
  tag += `<div class="action-tag">⚡ 行动 · 消耗 ${cost} 点（${costLabel}）</div>`;
}
if (lastMeta && lastMeta.month_advanced) {
  tag = `<div class="month-marker">━━━ 行动点耗尽，进入 ${lastMeta.new_date} ━━━</div>` + tag;
}
// 🆕 v1.6.7 架构重构：前端不再本地清洗，统一调 /api/sanitize
// 服务端 narrative_sanitizer.py 是单一权威（前后端共用）
const rawNarrative = n.narrative || "";
api("/api/sanitize", "POST", {text: rawNarrative}).then(sanitizeData => {
  const cleanedNarrative = (sanitizeData && !sanitizeData.error)
    ? sanitizeData.cleaned
    : rawNarrative;
  // 🆕 v1.7.0：调用 /api/render_narrative 做结构化渲染
  api("/api/render_narrative", "POST", {
    structured_blocks: n.narrative_blocks || [],
    narrative_text: cleanedNarrative,
  }).then(renderData => {
    let bodyHtml;
    if (renderData && !renderData.error && renderData.html) {
      // 结构化 blocks → CSS 渲染
      bodyHtml = `<div class="narrative-body" data-round="${n.round}">${renderData.html}</div>`;
    } else {
      // fallback：纯文本
      bodyHtml = `<div class="narrative-body plain" data-round="${n.round}">${escapeHtml(cleanedNarrative)}</div>`;
    }
    div.innerHTML = tag + bodyHtml;
    $main.insertBefore(div, $main.lastElementChild);
    // 异步请求后端提取名词（标记未读词）
    if (state.session_id) {
      api("/api/extract_terms", "POST", {
        session_id: state.session_id,
        text: cleanedNarrative,
      }).then(data => {
        if (data.error || !data.new_terms || data.new_terms.length === 0) return;
        const $body = div.querySelector(".narrative-body");
        if ($body) {
          $body.innerHTML = data.marked_text;
          attachTermTooltips();
        }
      }).catch(() => {});
    }
  }).catch(() => {
    // render API 失败 → 纯文本 fallback
    const bodyHtml = `<div class="narrative-body plain" data-round="${n.round}">${escapeHtml(cleanedNarrative)}</div>`;
    div.innerHTML = tag + bodyHtml;
    $main.insertBefore(div, $main.lastElementChild);
  });
}).catch(() => {
  // 兜底：sanitize API 失败时直接显示原文
  const bodyHtml = `<div class="narrative-body plain" data-round="${n.round}">${escapeHtml(rawNarrative)}</div>`;
  div.innerHTML = tag + bodyHtml;
  $main.insertBefore(div, $main.lastElementChild);
});
}

function appendInputArea() {
// 🆕 v1.7.7 改：把 voice_options 容器嵌到 input-area 内部，统一为"行动区"
// 玩家视觉上"声音选项 + 输入框"是一个整体
// 🆕 v1.7.9 改：默认隐藏输入框（声音按钮优先），点"自由输入"才展开
const wrapper = document.createElement("div");
wrapper.className = "action-area";
wrapper.id = "action-area";
wrapper.innerHTML = `
  <div class="input-area input-area-collapsed" id="input-area">
    <div class="input-area-header">
      <span class="input-area-title">✍️ 自由发挥</span>
      <button class="input-area-toggle" onclick="cancelFreeInput()" title="返回声音选项">← 返回</button>
    </div>
    <textarea id="player_input" placeholder="想做什么 / 想说什么？  ⏎ 提交 · Shift+Enter 换行"></textarea>
    <div class="row">
      <span class="hint">/help 元指令 · /state 状态 · /save slot1 存档</span>
      <button id="btn_submit" onclick="submitInput()">行动</button>
    </div>
    <div id="submit_msg"></div>
  </div>
`;
$main.appendChild(wrapper);
document.getElementById("player_input").focus();
// 🆕 v1.6.5 快捷键：
// - Enter（裸键）       → 提交（移动端友好，没 Ctrl 键）
// - Shift+Enter / Alt+Enter → 换行（多行输入）
// - Ctrl+Enter / Cmd+Enter → 提交（兼容桌面用户习惯）
document.getElementById("player_input").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey && !e.altKey) {
    // 裸 Enter 提交
    e.preventDefault();
    submitInput();
  } else if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    // Ctrl/Cmd+Enter 提交（兼容）
    e.preventDefault();
    submitInput();
  }
  // Shift+Enter / Alt+Enter 默认行为：插入换行
});
}

// 🆕 v1.6.9 重置输入框 placeholder 为默认
// 🆕 v1.7.24 改：调用 /api/dilemma 动态生成困境引导 placeholder
function resetInputPlaceholder() {
const $ta = document.getElementById("player_input");
if ($ta) {
  $ta.placeholder = "或自由输入（你想做什么/想描述什么都可以）";
  $ta.value = "";
}
}

// 🆕 v1.7.24: 从 narrative 提取困境，动态更新 placeholder
async function updatePlaceholderFromNarrative(narrative) {
  if (!narrative || narrative.length < 50) return;
  try {
    const r = await api("/api/dilemma", "POST", {text: narrative});
    if (r && r.placeholder && r.placeholder.length > 0) {
      const $ta = document.getElementById("player_input");
      if ($ta) {
        $ta.placeholder = r.placeholder;
      }
    }
  } catch (e) {
    console.warn("[v1.7.24] dilemma placeholder update failed:", e);
  }
}

// 🆕 v1.7.1 Character Wiki 弹层（per-save 人物知识图谱）
async function openCharacterWiki() {
if (!state.session_id) {
  alert("请先开始游戏");
  return;
}
const data = await api("/api/character_wiki", "POST", {
  session_id: state.session_id,
});
if (data.error) {
  alert("Wiki 加载失败：" + data.error);
  return;
}
renderCharacterWikiModal(data.wiki);
}

function renderCharacterWikiModal(wiki) {
const existing = document.getElementById("character-wiki-modal");
if (existing) existing.remove();

const stats = wiki.stats || {};
const chars = Object.values(wiki.characters || {}).sort(
  (a, b) => (b.appear_count || 0) - (a.appear_count || 0)
);

const charItems = chars.map(c => {
  const promises = []
    .concat((c.promises_player || []).map(p => `<div class="promise-player">我方承诺：${escapeHtml(p)}</div>`))
    .concat((c.promises_npc || []).map(p => `<div class="promise-npc">对方承诺：${escapeHtml(p)}</div>`))
    .join("");
  const events = (c.key_events || []).slice(-5).map(e =>
    `<li>第 ${e.round} 回合：${escapeHtml(e.summary || "")}</li>`
  ).join("");
  return `
    <div class="wiki-character" data-name="${escapeHtml(c.id)}">
      <div class="wiki-char-header">
        <span class="wiki-char-name">${escapeHtml(c.id)}</span>
        <span class="wiki-char-rel">${escapeHtml(c.relationship)}</span>
        <span class="wiki-char-count">出现 ${c.appear_count || 0} 次</span>
      </div>
      <div class="wiki-char-summary">${escapeHtml(c.first_appear_summary || c.description || "")}</div>
      ${promises ? `<div class="wiki-char-promises">${promises}</div>` : ""}
      ${events ? `<ul class="wiki-char-events">${events}</ul>` : ""}
    </div>
  `;
}).join("") || '<p class="recap-empty">本存档还没有遇到任何人物</p>';

const decisionItems = (wiki.decisions || []).slice(-10).reverse().map(d => `
  <div class="wiki-decision">
    <span class="wiki-dec-round">R${d.round}</span>
    <span class="wiki-dec-text">${escapeHtml(d.summary)}</span>
    ${(d.alternatives || []).length > 0 ? `<div class="wiki-dec-alt">其他选项：${d.alternatives.map(escapeHtml).join("、")}</div>` : ""}
  </div>
`).join("") || '<p class="recap-empty">暂无决策记录</p>';

const modal = document.createElement("div");
modal.id = "character-wiki-modal";
modal.className = "recap-modal-overlay";
modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
modal.innerHTML = `
  <div class="recap-modal" onclick="event.stopPropagation()" style="max-width:720px">
    <div class="recap-header">
      <h2>🕸️ 人物 Wiki（仅本存档）</h2>
      <span class="recap-meta">${stats.character_count || 0} 人物 · ${stats.event_count || 0} 事件 · ${stats.decision_count || 0} 决策</span>
      <button class="recap-close" onclick="document.getElementById('character-wiki-modal').remove()">×</button>
    </div>
    <div class="recap-body-content">
      <h3 style="margin-top:0;color:#5a3e1f">👥 人物</h3>
      ${charItems}
      <h3 style="color:#5a3e1f">🎯 关键决策（最近 10）</h3>
      ${decisionItems}
    </div>
  </div>
`;
document.body.appendChild(modal);
}

function appendVoiceOptions(voiceOptions) {
// 🆕 v1.6+ Tab 式 UX：先显示 2-4 个选项 + 「其他」按钮
// 点「其他」后才展开自由输入框，避免玩家直接打字跳过选项
// 🆕 v1.7.7 改：插入到 action-area 内（input-area 之前），形成"行动区"
// 🆕 v1.7.9 改："其他" 按钮更突出（拆分样式 + 明确文案），强调"自由输入"是次要路径
// 🆕 v1.7.21 改：即使 voiceOptions 为空也必须显示"自由输入"按钮
// 🆕 v1.7.29 改：移动端默认折叠（节省屏高），点击/双击展开；用 localStorage 记住用户偏好
voiceOptions = voiceOptions || [];
const div = document.createElement("div");
div.className = "voice-options";
div.id = "voice-options";
// 🆕 v1.7.22 修复：如果后端已经注入了 voice_freetext 占位，前端不要再加 "自由输入" 按钮
const hasFreetext = voiceOptions.some(v => v.is_freetext);
// 🆕 v1.7.21: 如果 voiceOptions 为空，header 文案变化
const headerHint = voiceOptions.length > 0
  ? '<span class="voice-options-hint">或点下方"自由输入"</span>'
  : '<span class="voice-options-hint">DM 没生成选项——直接描述你想做什么</span>';

const gridItems = voiceOptions.map((opt, i) => {
  // 🆕 v1.7.21: is_freetext 标记的选项，点它直接展开自由输入框
  const onclick = opt.is_freetext
    ? 'showFreeInputTab()'
    : `submitVoiceOption(${i}, ${JSON.stringify(opt).replace(/"/g, '&quot;')})`;
  return `
    <button class="voice-option-btn ${opt.is_freetext ? 'other' : ''}" onclick="${onclick}">
      <span class="voice-name">${escapeHtml(opt.voice_name || '?')}</span>
      <span class="voice-intent">${escapeHtml(opt.intent_text || '都不对？自己描述要做什么')}</span>
    </button>
  `;
}).join("");
// 🆕 v1.7.22: 只在没 freetext 占位时才显示前端的"自由输入"按钮
const freetextButton = hasFreetext
  ? ""
  : `<button class="voice-option-btn other" onclick="showFreeInputTab()">
      <span class="voice-name">✍️ 自由输入</span>
      <span class="voice-intent">都不对？自己描述要做什么</span>
    </button>`;

// 🆕 v1.7.29 移动端折叠：默认隐藏 grid，只显示一条"🎭 N 个声音 ▾"小按钮
// 用户点 / 点 header 后展开（保存偏好到 localStorage）
// 🆕 v1.7.30 修复：折叠态也保留「自由输入」入口（grid 外），避免死局
const PREF_KEY = "hfe_voice_options_collapsed";
const isMobile = window.matchMedia("(max-width: 768px)").matches;
const storage = window.__VOICE_PREFS__ || JSON.parse(localStorage.getItem(PREF_KEY) || "null");
let userPref = storage;
// 没有偏好时：移动端默认折叠，桌面端默认展开
if (userPref === null || userPref === undefined) {
  userPref = isMobile;
}
window.__VOICE_PREFS__ = userPref;
const savePref = (collapsed) => {
  try { localStorage.setItem(PREF_KEY, JSON.stringify(collapsed)); } catch (_) {}
  window.__VOICE_PREFS__ = collapsed;
};
const initialCollapsed = userPref;
// 当前回合数（用于高亮）；从 state.round 取不到时用 -1
const currentRound = (typeof state !== "undefined" && state.round_number) || 0;
const voiceCount = voiceOptions.filter(v => !v.is_freetext).length || 1;
// 🆕 v1.7.30：折叠态常驻「自由输入」按钮（grid 外），保证玩家永远有 fallback
// 重要：voiceOptions 为空时强制不折叠（无可选项时隐藏 grid 等于死局）
const hasRealOptions = voiceOptions.filter(v => !v.is_freetext).length > 0;
const effectiveCollapsed = hasRealOptions ? initialCollapsed : false;
const fallbackText = voiceOptions.length > 0
  ? "或自由输入"
  : "DM 没生成选项——直接描述你想做什么";
// 🆕 v1.7.30：玩家主动求 LLM 补充选项（仅 < 2 真实选项时显示）
const suggestButton = hasRealOptions ? "" : `
  <button class="voice-options-suggest-btn" onclick="suggestVoiceOptions()" aria-label="帮我一下">
    <span class="suggest-icon">✨</span>
    <span class="suggest-text">帮我一下（DM 帮想 3~5 个方案）</span>
  </button>
`;
div.innerHTML = `
  <div class="voice-options-header">
    <button class="voice-options-toggle" aria-expanded="${!effectiveCollapsed}" aria-controls="voice-options-grid" ${hasRealOptions ? "" : "disabled"}>
      <span class="voice-options-toggle-icon">${effectiveCollapsed ? "▸" : "▾"}</span>
      <span class="voice-options-title">🎭 ${effectiveCollapsed ? voiceCount + " 个声音" : "你脑海中的声音"}</span>
      ${currentRound > 0 ? `<span class="voice-options-round-tag" title="当前回合">R${currentRound}</span>` : ""}
    </button>
    <span class="voice-options-hint">${effectiveCollapsed ? "点开选行动" : headerHint.replace(/<[^>]+>/g, "")}</span>
  </div>
  <div class="voice-options-grid ${effectiveCollapsed ? "collapsed" : ""}" id="voice-options-grid" role="region">
    ${gridItems}
    ${freetextButton}
  </div>
  ${suggestButton}
  <button class="voice-options-freetext-fallback" onclick="showFreeInputTab()" aria-label="自由输入">
    <span class="freetext-icon">✍️</span>
    <span class="freetext-text">${fallbackText}</span>
  </button>
`;
// 折叠状态：如果默认展开，反向给折叠按钮取消 collapsed class（已经有 expanded class）
if (!initialCollapsed) div.classList.add("voice-options-expanded");

// 🆕 绑定折叠按钮
const $toggle = div.querySelector(".voice-options-toggle");
if ($toggle) {
  $toggle.addEventListener("click", () => {
    const isCollapsed = div.classList.toggle("voice-options-collapsed");
    savePref(isCollapsed);
    const $grid = div.querySelector(".voice-options-grid");
    if ($grid) $grid.classList.toggle("collapsed", isCollapsed);
    const $icon = div.querySelector(".voice-options-toggle-icon");
    const $title = div.querySelector(".voice-options-toggle-title, .voice-options-title");
    const $hint = div.querySelector(".voice-options-hint");
    if ($icon) $icon.textContent = isCollapsed ? "▸" : "▾";
    if ($title) $title.textContent = isCollapsed
      ? `🎭 ${voiceCount} 个声音`
      : "你脑海中的声音";
    if ($hint) $hint.textContent = isCollapsed
      ? "点开选行动"
      : (voiceOptions.length > 0 ? '或点下方"自由输入"' : "DM 没生成选项——直接描述你想做什么");
    $toggle.setAttribute("aria-expanded", String(!isCollapsed));
  });
}

// 🆕 v1.7.7 改：插到 action-area 内部 input-area 之前
const $actionArea = document.getElementById("action-area");
const $inputArea = document.getElementById("input-area");
if ($actionArea && $inputArea && $actionArea.contains($inputArea)) {
  $actionArea.insertBefore(div, $inputArea);
} else if ($inputArea && $main.contains($inputArea)) {
  $main.insertBefore(div, $inputArea);
} else {
  $main.appendChild(div);
}

// 🆕 v1.7.29 新回合到达时，一次性脉冲（动画后移除 class）
requestAnimationFrame(() => {
  div.classList.add("voice-options-new-round");
  setTimeout(() => div.classList.remove("voice-options-new-round"), 1000);
});
}

// 🆕 v1.7.30：玩家点 "✨ 帮我一下" 调 /api/voice_options/suggest
// LLM 基于最近 narrative + state 补充 3~5 个可执行方案
async function suggestVoiceOptions() {
  const sid = (typeof state !== "undefined" && state.session_id) || "";
  if (!sid) {
    console.warn("[suggestVoiceOptions] no session_id");
    return;
  }
  const $btn = document.querySelector(".voice-options-suggest-btn");
  if (!$btn) return;
  // 锁定按钮 + 改文案
  $btn.disabled = true;
  $btn.classList.add("loading");
  const $text = $btn.querySelector(".suggest-text");
  const originalText = $text ? $text.textContent : "";
  if ($text) $text.textContent = "DM 在想...";
  try {
    const resp = await fetch("/api/voice_options/suggest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sid }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const errMsg = data.error || "请求失败";
      if ($text) $text.textContent = `${errMsg}，请直接输入`;
      console.error("[suggestVoiceOptions] HTTP", resp.status, errMsg);
      return;
    }
    if (Array.isArray(data.voice_options) && data.voice_options.length > 0) {
      // 重渲染：删除旧节点 + 重新调 appendVoiceOptions
      const old = document.getElementById("voice-options");
      if (old) old.remove();
      // 临时禁用 localStorage 折叠（确保新选项可见）
      const prev = window.__VOICE_PREFS__;
      window.__VOICE_PREFS__ = false;
      appendVoiceOptions(data.voice_options);
      window.__VOICE_PREFS__ = prev;
      // 滚动到新选项
      const newOpts = document.getElementById("voice-options");
      if (newOpts && newOpts.scrollIntoView) {
        newOpts.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else {
      if ($text) $text.textContent = "没想出方案，请直接输入";
    }
  } catch (e) {
    console.error("[suggestVoiceOptions] failed:", e);
    if ($text) $text.textContent = "网络出错，请直接输入";
  } finally {
    // 2s 后让按钮失效（玩家已用过了）
    setTimeout(() => {
      if ($btn) {
        $btn.classList.add("used");
        $btn.disabled = true;
        if ($text) $text.textContent = "已使用，请基于这些选项行动";
      }
    }, 500);
  }
}

function showFreeInputTab() {
// 🆕 v1.7.9 改：玩家点 "自由输入" 后展开输入框（不是新 tab，只是展开折叠区）
  // 1. 展开 input-area（移除 collapsed class）
const $inputArea = document.getElementById("input-area");
if ($inputArea) {
  $inputArea.classList.remove("input-area-collapsed");
  $inputArea.classList.add("input-area-expanded");
}

// 2. 高亮声音区为"已折叠"（变灰）
const $opts = document.getElementById("voice-options");
if ($opts) $opts.classList.add("voice-options-collapsed");

// 3. 聚焦输入框
const $ta = document.getElementById("player_input");
if ($ta) {
  $ta.focus();
  $ta.placeholder = "想做什么 / 想说什么？例：我要去乡试考场亲眼看看……";
}

// 4. 滚动到底部
$main.scrollTop = $main.scrollHeight;
}

function cancelFreeInput() {
// 🆕 v1.7.9 改：玩家点 "← 返回" 后折叠输入框，回到声音选项为主的状态
// 1. 折叠 input-area
const $inputArea = document.getElementById("input-area");
if ($inputArea) {
  $inputArea.classList.remove("input-area-expanded");
  $inputArea.classList.add("input-area-collapsed");
}

// 2. 取消声音区折叠
const $opts = document.getElementById("voice-options");
if ($opts) $opts.classList.remove("voice-options-collapsed");

// 3. 清空输入框内容
const $ta = document.getElementById("player_input");
if ($ta) {
  $ta.placeholder = "想做什么 / 想说什么？";
  $ta.value = "";
}
}

async function submitVoiceOption(index, opt) {
// 🆕 v1.5+：玩家点击内在声音选项 → 用 intent_text 作为输入
// 🐛 Issue #3 修复：双击防护
if (state._submitting) return;
const inputText = (opt.intent_text || (opt.voice_name + "的想法")).trim();
if (!inputText) {
  console.warn("Empty intent_text in voice option", opt);
  return;
}
state._submitting = true;
state._selectedVoice = opt;

// 🆕 v1.7.8 立即视觉反馈 + 禁用所有 voice 按钮（防止重复点击）
const voiceOptions = document.getElementById("voice-options");
let originalVoiceHTML = null;
if (voiceOptions) {
  originalVoiceHTML = voiceOptions.innerHTML;
  // 禁用所有 voice 按钮
  voiceOptions.querySelectorAll("button").forEach(b => {
    b.disabled = true;
    b.style.opacity = "0.6";
    b.style.cursor = "not-allowed";
  });
  // 高亮选中的
  const buttons = voiceOptions.querySelectorAll(".voice-option-btn");
  if (buttons[index]) {
    buttons[index].style.opacity = "1";
    buttons[index].style.background = "#f5e6c8";
    buttons[index].style.borderColor = "#c4a878";
    buttons[index].innerHTML = `<span class='voice-name'>⏳ ${escapeHtml(opt.voice_name || '?')}</span><span class='voice-intent'>${escapeHtml(inputText)}</span>`;
  }
}

try {
  await submitInputWithText(inputText);
} catch (e) {
  // 🆕 v1.7.8 失败时恢复 voice 按钮
  console.error("submitVoiceOption error:", e);
  if (voiceOptions && originalVoiceHTML !== null) {
    voiceOptions.innerHTML = originalVoiceHTML;
  }
  const $m = document.getElementById("submit_msg");
  if ($m) $m.innerHTML = "<div class='error'>提交失败，请重试</div>";
} finally {
  state._submitting = false;
}
}

// 🆕 v1.7.15 弹窗进度管理
const LoadingModal = {
  overlay: null,
  startTime: 0,
  timer: null,
  // 🆕 v1.7.30: facts 轮播状态
  factTimer: null,
  factPauseUntil: 0,
  currentFactIndex: 0,
  show(title = "🌀 DM 正在渲染下一回合...") {
    this.close();  // 关闭已存在的
    this.startTime = Date.now();
    const html = `
      <div id="loading-modal" class="loading-modal-overlay">
        <div class="loading-modal">
          <div class="loading-title">${escapeHtml(title)}</div>
          <div class="loading-phase">⏳ 准备中...</div>
          <div class="loading-progress">
            <div class="loading-progress-bar" style="width:0%"></div>
          </div>
          <div class="loading-time">⏱️ 已等待 0 秒</div>
          <div class="loading-facts" aria-live="polite">
            <div class="loading-facts-header">💡 等待时的小知识</div>
            <div class="loading-facts-body">
              <button class="loading-facts-prev" onclick="LoadingModal.cycleFact(-1)" aria-label="上一条">‹</button>
              <div class="loading-facts-content" id="loading-facts-content">…</div>
              <button class="loading-facts-next" onclick="LoadingModal.cycleFact(1)" aria-label="下一条">›</button>
            </div>
            <div class="loading-facts-counter"><span id="loading-facts-counter">--</span></div>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML("beforeend", html);
    this.overlay = document.getElementById("loading-modal");
    // 启动计时器
    this.timer = setInterval(() => {
      const $t = this.overlay?.querySelector(".loading-time");
      if ($t) {
        const sec = Math.floor((Date.now() - this.startTime) / 1000);
        $t.textContent = `⏱️ 已等待 ${sec} 秒`;
      }
    }, 200);
    // 🆕 v1.7.30: 启动 facts 轮播（5s 一次）
    this.refreshFacts();
    this.factTimer = setInterval(() => {
      if (Date.now() < this.factPauseUntil) return;
      this.cycleFact(1);
    }, 5000);
    // hover 暂停（桌面端）
    const $facts = this.overlay?.querySelector(".loading-facts");
    if ($facts) {
      $facts.addEventListener("mouseenter", () => { this.factPauseUntil = Date.now() + 8000; });
      $facts.addEventListener("mouseleave", () => { this.factPauseUntil = 0; });
    }
  },
  update(phase, message, progress) {
    if (!this.overlay) return;
    const $phase = this.overlay.querySelector(".loading-phase");
    const $bar = this.overlay.querySelector(".loading-progress-bar");
    if ($phase && message) $phase.textContent = message;
    if ($bar && typeof progress === "number") $bar.style.width = progress + "%";
  },
  // 🆕 v1.7.30: 收集等待时可展示的 facts（4 个来源）
  collectFacts() {
    const facts = [];
    // 来源 1: world_dwell（已有的世界画卷）
    if (wizard && wizard.world_dwell) {
      const dwell = wizard.world_dwell;
      if (dwell.geography) facts.push({ source: "地理", text: dwell.geography });
      if (dwell.economy) facts.push({ source: "生计", text: dwell.economy });
      if (dwell.culture) facts.push({ source: "风物", text: dwell.culture });
      if (dwell.politics) facts.push({ source: "官府", text: dwell.politics });
    }
    // 来源 2: era_data（时代包元数据）
    if (wizard && wizard.era_data) {
      const e = wizard.era_data;
      if (e.description) facts.push({ source: "时代", text: `${e.name || ""}：${e.description}` });
      if (e.year_range) facts.push({ source: "年代", text: `本时代年份：${e.year_range}` });
    }
    // 来源 3: 静态知识库（万历十五年硬知识）
    if (WANLI_FACTS && Array.isArray(WANLI_FACTS)) {
      for (const f of WANLI_FACTS) facts.push({ source: f.cat, text: f.text });
    }
    // 来源 4: state.narrative_history 摘要（最近 3 轮）
    if (typeof state !== "undefined" && state.narrative_history && state.narrative_history.length) {
      const recent = state.narrative_history.slice(-3);
      for (const n of recent) {
        const t = (n && n.narrative) || "";
        if (t) facts.push({ source: "回顾", text: t.replace(/\s+/g, " ").slice(0, 80) + "…" });
      }
    }
    // 去空 + 去重
    const seen = new Set();
    const uniq = [];
    for (const f of facts) {
      if (!f || !f.text) continue;
      const key = f.text.slice(0, 40);
      if (seen.has(key)) continue;
      seen.add(key);
      uniq.push(f);
    }
    return uniq.slice(0, 20);  // 最多 20 条
  },
  refreshFacts() {
    const facts = this.collectFacts();
    this.facts = facts;
    this.currentFactIndex = 0;
    this.renderFact();
  },
  cycleFact(direction) {
    if (!this.facts || this.facts.length === 0) {
      this.refreshFacts();
      return;
    }
    this.currentFactIndex = (this.currentFactIndex + direction + this.facts.length) % this.facts.length;
    this.renderFact();
  },
  renderFact() {
    if (!this.overlay) return;
    const $content = this.overlay.querySelector("#loading-facts-content");
    const $counter = this.overlay.querySelector("#loading-facts-counter");
    if (!this.facts || this.facts.length === 0) {
      if ($content) $content.textContent = "（无更多内容）";
      if ($counter) $counter.textContent = "0/0";
      return;
    }
    const f = this.facts[this.currentFactIndex];
    if ($content) {
      // 简单 fade 动画
      $content.classList.add("loading-facts-fadeout");
      setTimeout(() => {
        if (!$content) return;
        $content.innerHTML = `<span class="loading-facts-source">${escapeHtml(f.source)}</span>${escapeHtml(f.text)}`;
        $content.classList.remove("loading-facts-fadeout");
      }, 150);
    }
    if ($counter) $counter.textContent = `${this.currentFactIndex + 1}/${this.facts.length}`;
  },
  close() {
    if (this.timer) clearInterval(this.timer);
    if (this.factTimer) clearInterval(this.factTimer);
    this.timer = null;
    this.factTimer = null;
    this.facts = [];
    this.currentFactIndex = 0;
    if (this.overlay) {
      this.overlay.classList.add("loading-modal-fadeout");
      setTimeout(() => {
        if (this.overlay && this.overlay.parentNode) {
          this.overlay.parentNode.removeChild(this.overlay);
        }
        this.overlay = null;
      }, 200);
    } else {
      this.overlay = null;
    }
  },
};

// 🆕 v1.7.30: 静态知识库——万历十五年小知识
// 等待时展示，玩家可学些硬知识
const WANLI_FACTS = [
  { cat: "物价", text: "万历年间，米价每石 8 钱至 1 两不等（江南水乡偏高，荒年翻倍）" },
  { cat: "差役", text: "里甲制下，每 10 年轮差 1 次；正德后多雇人代役，1 个正役折银 1~3 两" },
  { cat: "科举", text: "秀才须通过院试，考题出自《四书》《五经》，每县录取率 1/300" },
  { cat: "物价", text: "上好湖绫 1 匹可卖 5~8 钱；盛泽镇绸行抽佣 3%~5%" },
  { cat: "律法", text: "《大明律》藏匿逃人杖 80；诱拐良家女子绞监候；私藏武器杖 100" },
  { cat: "农时", text: "五月收麦插秧，七月早稻登场；霜降后种油菜，冬至前完成" },
  { cat: "纺织", text: "盛泽镇出产湖绫、苏缎、水纬；机户十之七八，织工日赚 30~50 文" },
  { cat: "赋税", text: "田赋按亩征夏税秋粮；丁税（人头税）已于万历九年部分摊入田亩" },
  { cat: "商业", text: "徽商晋商多走盐茶丝；江南本地商人多走绸布；长途贩运风险高" },
  { cat: "官制", text: "县令正七品，月俸 7.5 石米；典史 9 品未入流；里长由粮长轮充" },
  { cat: "节令", text: "五月初五端午，挂艾虎、饮雄黄；七月初七乞巧，女子对月穿针" },
  { cat: "饮食", text: "江南主食米饭，菜以鱼虾豆腐为主；富户宴客八菜一汤" },
  { cat: "婚嫁", text: "聘礼一般为银 30~50 两（盛泽镇中等人家标准）；嫁妆 1~2 抬箱笼" },
  { cat: "宗族", text: "江南宗族势力大；建祠堂、修族谱、设族田；犯事可请族长出面具保" },
  { cat: "宗教", text: "江南佛道并存；城隍庙、土地祠最普遍；妇女入庙烧香为日常" },
  { cat: "物价", text: "上等猪肉 1 斤 20 文；鸡蛋 1 枚 1 文；好酒 1 斤 50~80 文" },
];

// 🆕 v1.7.30 城市显示名（city_id → 中文名）
const CITY_DISPLAY = {
  shengze: "盛泽镇",
  suzhou: "苏州府",
  hangzhou: "杭州府",
  songjiang: "松江府",
  nanjing: "南京应天府",
};

// 🆕 v1.7.30 亲属关系显示名
const RELATION_DISPLAY = {
  wife: "妻",
  husband: "夫",
  son: "子",
  daughter: "女",
  father: "父",
  mother: "母",
  brother: "兄",
  sister: "姐",
  patriarch: "祖父",
  grandparent: "祖父母",
  parent: "父母",
  uncle: "叔伯",
  aunt: "姑姨",
  cousin: "堂表亲",
  ancestor: "先祖",
  spouse: "配偶",
  child: "子女",
};

// 🆕 v1.7.30 折叠区切换
// 🆕 v1.7.30 把 discoveries 展开成顶层字段（前端用）
function flattenDiscoveries(data) {
  const d = data.discoveries || {};
  // facts 是 list
  data.facts = d.facts || [];
  // 其他是 dict[kind]={id: obj, ...}
  for (const k of ["place", "person", "item", "letter", "event"]) {
    const bucket = d[`${k}s`] || {};
    data[`${k}s`] = Object.values(bucket);
  }
  // 简写：letters / places / persons / items / events
  data.letters = data.letters || [];
  return data;
}

function toggleSbSection(name) {
  const $body = document.querySelector(`[data-body="${name}"]`);
  const $header = document.querySelector(`[data-section="${name}"] .sb-section-toggle`);
  if (!$body) return;
  const isCollapsed = $body.classList.toggle("collapsed");
  if ($header) $header.textContent = isCollapsed ? "▸" : "▾";
  // localStorage 记忆
  try { localStorage.setItem(`hfe_sb_${name}_collapsed`, isCollapsed ? "1" : "0"); } catch (_) {}
}

// 🆕 v1.7.30 我的档案弹层（5 tab）
function openMyProfile(tab = "cash") {
  // 简单实现：提示后续 commit 完善
  alert(`👤 我的档案\n\n即将上线：${tab} 标签页\n\n当前在 sidebar 已有 6 折叠区。\n弹层"全部"功能 v1.7.30 后续 commit 完善。`);
}

// 🆕 v1.7.30 账户登录/注册 UI
function showAccountLogin() {
  if (state.account_id) {
    showSavesList();
    return;
  }
  $main.innerHTML = `
    <div class="start-screen">
      <h2>👤 账户登录</h2>
      <p style="color:#8b6f47;font-size:14px;line-height:1.7">
        v1.7.30 引入邀请码注册。请输入您的邀请码和用户名。
      </p>
      <div style="background:#faf3e0;padding:16px;border:1px solid #c4a878;border-radius:6px;margin:16px 0;max-width:480px">
        <div style="margin-bottom:12px">
          <label style="display:block;font-size:13px;color:#5a3e1f;margin-bottom:4px">邀请码</label>
          <input id="invite-code-input" type="text" placeholder="INV-XXXX-XXXX"
                 style="width:100%;padding:8px;border:1px solid #c4a878;border-radius:4px;font-family:monospace;font-size:14px"/>
        </div>
        <div style="margin-bottom:12px">
          <label style="display:block;font-size:13px;color:#5a3e1f;margin-bottom:4px">用户名（2-20 字符）</label>
          <input id="username-input" type="text" placeholder="例如：施润泽"
                 style="width:100%;padding:8px;border:1px solid #c4a878;border-radius:4px;font-size:14px"/>
        </div>
        <div style="margin-bottom:12px">
          <label style="display:block;font-size:13px;color:#5a3e1f;margin-bottom:4px">邮箱（可选）</label>
          <input id="email-input" type="email" placeholder="example@email.com"
                 style="width:100%;padding:8px;border:1px solid #c4a878;border-radius:4px;font-size:14px"/>
        </div>
        <button onclick="registerAccount()" style="width:100%;padding:10px;background:#5a3e1f;color:#f5e6c8;border:none;border-radius:4px;cursor:pointer;font-size:14px">
          🎫 注册并登录
        </button>
        <div id="account-error" style="color:#c0392b;margin-top:8px;font-size:13px"></div>
      </div>
      <p style="font-size:12px;color:#a08858">
        💡 已有账户？
        <a href="javascript:showAccountSwitch()" style="color:#5a3e1f;text-decoration:underline">使用 account_id 登录</a>
      </p>
    </div>
  `;
}

async function registerAccount() {
  const inviteCode = document.getElementById("invite-code-input").value.trim();
  const username = document.getElementById("username-input").value.trim();
  const email = document.getElementById("email-input").value.trim();
  const $err = document.getElementById("account-error");
  if (!inviteCode || !username) {
    $err.textContent = "邀请码和用户名必填";
    return;
  }
  try {
    const data = await api("/api/account/register", "POST", {
      invite_code: inviteCode,
      username: username,
      email: email,
    });
    if (data.error) {
      $err.textContent = data.error;
      return;
    }
    state.account_id = data.account_id;
    state.account_username = data.username;
    state.account_role = data.role;
    localStorage.setItem("hfe_account_id", data.account_id);
    localStorage.setItem("hfe_account_username", data.username);
    localStorage.setItem("hfe_account_role", data.role);
    showSavesList();
  } catch (e) {
    $err.textContent = "网络错误：" + e.message;
  }
}

function showAccountSwitch() {
  $main.innerHTML = `
    <div class="start-screen">
      <h2>👤 使用 account_id 登录</h2>
      <div style="background:#faf3e0;padding:16px;border:1px solid #c4a878;border-radius:6px;margin:16px 0;max-width:480px">
        <div style="margin-bottom:12px">
          <label style="display:block;font-size:13px;color:#5a3e1f;margin-bottom:4px">account_id</label>
          <input id="account-id-input" type="text" placeholder="8 字符 ID"
                 style="width:100%;padding:8px;border:1px solid #c4a878;border-radius:4px;font-family:monospace;font-size:14px"/>
        </div>
        <button onclick="loginByAccountId()" style="width:100%;padding:10px;background:#5a3e1f;color:#f5e6c8;border:none;border-radius:4px;cursor:pointer;font-size:14px">
          🔑 登录
        </button>
        <div id="login-error" style="color:#c0392b;margin-top:8px;font-size:13px"></div>
      </div>
      <p style="font-size:12px;color:#a08858">
        <a href="javascript:showAccountLogin()" style="color:#5a3e1f;text-decoration:underline">← 返回注册</a>
      </p>
    </div>
  `;
}

async function loginByAccountId() {
  const accountId = document.getElementById("account-id-input").value.trim();
  const $err = document.getElementById("login-error");
  if (!accountId) {
    $err.textContent = "account_id 必填";
    return;
  }
  try {
    const data = await api("/api/account/login", "POST", {account_id: accountId});
    if (data.error) {
      $err.textContent = data.error;
      return;
    }
    state.account_id = data.account_id;
    state.account_username = data.username;
    state.account_role = data.role;
    localStorage.setItem("hfe_account_id", data.account_id);
    localStorage.setItem("hfe_account_username", data.username);
    localStorage.setItem("hfe_account_role", data.role);
    showSavesList();
  } catch (e) {
    $err.textContent = "网络错误：" + e.message;
  }
}

async function showSavesList() {
  try {
    const data = await api(`/api/account/saves?account_id=${state.account_id}`);
    if (data.error) {
      alert(data.error);
      return;
    }
    const saves = data.saves || [];
    $main.innerHTML = `
      <div class="start-screen">
        <h2>👤 ${escapeHtml(state.account_username)} 的存档</h2>
        <p style="color:#8b6f47;font-size:14px;line-height:1.7">
          共 ${saves.length} 个存档
        </p>
        <div id="saves-list" style="margin:16px 0;max-width:600px">
          ${saves.length > 0 ? saves.map(s => `
            <div class="archive-item" onclick="loadAccountSave('${s.save_id}')">
              <div class="ar-session">💾 ${escapeHtml(s.save_id)}</div>
              <div class="ar-meta">${escapeHtml(s.bound_at || '')}</div>
            </div>
          `).join("") : "<p style='color:#a08858;font-size:13px'>尚无存档</p>"}
        </div>
        <button onclick="createAccountSave()" style="padding:10px 20px;background:#5a3e1f;color:#f5e6c8;border:none;border-radius:4px;cursor:pointer;font-size:14px;margin-top:8px">
          ✨ 创建新存档
        </button>
        <button onclick="logoutAccount()" style="padding:10px 20px;background:transparent;color:#5a3e1f;border:1px solid #c4a878;border-radius:4px;cursor:pointer;font-size:14px;margin-top:8px;margin-left:8px">
          退出登录
        </button>
      </div>
    `;
  } catch (e) {
    alert("网络错误：" + e.message);
  }
}

async function createAccountSave() {
  try {
    const data = await api("/api/account/saves", "POST", {account_id: state.account_id});
    if (data.error) {
      alert(data.error);
      return;
    }
    // 创建完存档后用这个存档启动游戏
    state.session_id = data.save_path;
    alert(`✨ 存档创建成功：${data.save_id}\n请继续选择身份启动游戏`);
    showSavesList();
  } catch (e) {
    alert("网络错误：" + e.message);
  }
}

function loadAccountSave(saveId) {
  alert(`加载存档 ${saveId}（v1.7.31 实施具体逻辑）`);
}

function logoutAccount() {
  state.account_id = null;
  state.account_username = null;
  localStorage.removeItem("hfe_account_id");
  localStorage.removeItem("hfe_account_username");
  showAccountLogin();
}

// 页面加载时自动恢复
function restoreAccountFromStorage() {
  const accountId = localStorage.getItem("hfe_account_id");
  const username = localStorage.getItem("hfe_account_username");
  const role = localStorage.getItem("hfe_account_role") || "user";
  if (accountId && username) {
    state.account_id = accountId;
    state.account_username = username;
    state.account_role = role;
    return true;
  }
  return false;
}

// 🆕 v1.7.30 管理员面板（4 tab）
async function showAdminPanel() {
  if (!state.account_id) {
    showAccountLogin();
    return;
  }
  // 先验证权限
  const info = await api(`/api/account/info?account_id=${state.account_id}`);
  if (info.error || info.role !== "admin") {
    alert("需要 admin 权限");
    return;
  }
  $main.innerHTML = `
    <div class="start-screen">
      <h2>🛠 管理员面板</h2>
      <p style="color:#8b6f47;font-size:13px">
        ${escapeHtml(state.account_username)} (${state.account_id}) · <span style="color:#5a3e1f">admin</span>
      </p>
      <div style="display:flex;gap:8px;margin:16px 0;flex-wrap:wrap">
        <button onclick="adminShowTab('users')" class="admin-tab-btn" data-tab="users" style="padding:8px 16px;background:#5a3e1f;color:#f5e6c8;border:none;border-radius:4px;cursor:pointer">
          👥 用户
        </button>
        <button onclick="adminShowTab('saves')" class="admin-tab-btn" data-tab="saves" style="padding:8px 16px;background:transparent;color:#5a3e1f;border:1px solid #c4a878;border-radius:4px;cursor:pointer">
          💾 存档
        </button>
        <button onclick="adminShowTab('tokens')" class="admin-tab-btn" data-tab="tokens" style="padding:8px 16px;background:transparent;color:#5a3e1f;border:1px solid #c4a878;border-radius:4px;cursor:pointer">
          🎫 Token
        </button>
        <button onclick="adminShowTab('config')" class="admin-tab-btn" data-tab="config" style="padding:8px 16px;background:transparent;color:#5a3e1f;border:1px solid #c4a878;border-radius:4px;cursor:pointer">
          ⚙️ 配置
        </button>
        <button onclick="logoutAccount()" style="padding:8px 16px;background:transparent;color:#5a3e1f;border:1px solid #c4a878;border-radius:4px;cursor:pointer;margin-left:auto">
          退出
        </button>
      </div>
      <div id="admin-tab-content" style="margin-top:16px"></div>
    </div>
  `;
  adminShowTab("users");
}

async function adminShowTab(tab) {
  // 切换按钮样式
  document.querySelectorAll(".admin-tab-btn").forEach(btn => {
    const isActive = btn.dataset.tab === tab;
    btn.style.background = isActive ? "#5a3e1f" : "transparent";
    btn.style.color = isActive ? "#f5e6c8" : "#5a3e1f";
  });
  const $content = document.getElementById("admin-tab-content");
  $content.innerHTML = "<p style='color:#a08858;font-size:13px'>加载中…</p>";
  try {
    if (tab === "users") {
      const data = await api(`/api/admin/users?account_id=${state.account_id}`);
      $content.innerHTML = `
        <h3>👥 用户列表 (${data.total})</h3>
        <p style="font-size:13px;color:#5a3e1f">管理员 ${data.admins} 个 · 普通用户 ${data.users_count} 个</p>
        <div style="max-width:900px">
        ${data.users.map(u => `
          <div class="archive-item" style="display:flex;align-items:center;gap:12px">
            <div style="flex:1">
              <div class="ar-session">${escapeHtml(u.username)} ${u.role === "admin" ? "🛠" : ""}</div>
              <div class="ar-meta">id=${escapeHtml(u.account_id)} · ${u.saves_count} 个存档 · ${escapeHtml(u.email || "")}</div>
            </div>
            <select onchange="adminChangeRole('${u.account_id}', this.value)" style="padding:4px 8px;border:1px solid #c4a878;border-radius:4px">
              <option value="user" ${u.role === "user" ? "selected" : ""}>user</option>
              <option value="admin" ${u.role === "admin" ? "selected" : ""}>admin</option>
              <option value="guest" ${u.role === "guest" ? "selected" : ""}>guest</option>
            </select>
            <button onclick="adminDeleteUser('${u.account_id}')" style="padding:4px 8px;background:#c0392b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">删除</button>
          </div>
        `).join("")}
        </div>
      `;
    } else if (tab === "saves") {
      const data = await api(`/api/admin/saves?account_id=${state.account_id}`);
      $content.innerHTML = `
        <h3>💾 全部存档 (${data.total})</h3>
        <div style="max-width:900px">
        ${data.saves.length === 0 ? "<p style='color:#a08858'>尚无存档</p>" :
          data.saves.map(s => `
            <div class="archive-item" style="display:flex;align-items:center;gap:12px">
              <div style="flex:1">
                <div class="ar-session">💾 ${escapeHtml(s.save_id)} <span style="color:#8b6f47;font-size:12px">@ ${escapeHtml(s.username || "")}</span></div>
                <div class="ar-meta">account=${escapeHtml(s.account_id)} · ${escapeHtml(s.bound_at || "")}</div>
              </div>
              <button onclick="adminDeleteSave('${s.account_id}', '${s.save_id}')" style="padding:4px 8px;background:#c0392b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">删除</button>
            </div>
          `).join("")
        }
        </div>
      `;
    } else if (tab === "tokens") {
      const data = await api(`/api/admin/tokens?account_id=${state.account_id}&recent_limit=10`);
      const s = data.stats || {};
      $content.innerHTML = `
        <h3>🎫 Token 消耗统计</h3>
        <div style="background:#faf3e0;padding:16px;border:1px solid #c4a878;border-radius:6px;margin-bottom:16px">
          <div class="stat-line"><span class="label">总调用次数</span><span class="val">${s.total_calls || 0}</span></div>
          <div class="stat-line"><span class="label">总 token</span><span class="val">${s.total_tokens || 0}</span></div>
          <div class="stat-line"><span class="label">输入 token</span><span class="val">${s.total_prompt_tokens || 0}</span></div>
          <div class="stat-line"><span class="label">输出 token</span><span class="val">${s.total_completion_tokens || 0}</span></div>
          <div class="stat-line"><span class="label">错误数</span><span class="val">${s.error_count || 0}</span></div>
        </div>
        <h4>近期调用 (${(data.recent || []).length})</h4>
        <div style="max-width:900px">
        ${(data.recent || []).map(r => `
          <div class="archive-item" style="font-size:12px">
            <div class="ar-meta">${escapeHtml(r.model || "")} · ${r.prompt_tokens || 0} → ${r.completion_tokens || 0} · ${escapeHtml(r.timestamp || "")}</div>
          </div>
        `).join("")}
        </div>
      `;
    } else if (tab === "config") {
      const data = await api(`/api/admin/config?account_id=${state.account_id}`);
      $content.innerHTML = `
        <h3>⚙️ 配置概览</h3>
        <div style="background:#faf3e0;padding:16px;border:1px solid #c4a878;border-radius:6px;margin-bottom:16px">
          <div class="stat-line"><span class="label">era_id</span><span class="val">${escapeHtml(data.era_id)}</span></div>
          <div class="stat-line"><span class="label">era_name</span><span class="val">${escapeHtml(data.era_name)}</span></div>
          <div class="stat-line"><span class="label">current_year</span><span class="val">${data.current_year}</span></div>
          <div class="stat-line"><span class="label">current_date</span><span class="val">${escapeHtml(data.current_date)}</span></div>
          <div class="stat-line"><span class="label">player_identities</span><span class="val">${data.player_identities_count}</span></div>
          <div class="stat-line"><span class="label">cities</span><span class="val">${data.cities_count}</span></div>
          <div class="stat-line"><span class="label">major_events</span><span class="val">${data.major_events_count}</span></div>
          <div class="stat-line"><span class="label">triggers</span><span class="val">${data.triggers_count}</span></div>
        </div>
        <p style="color:#8b6f47;font-size:12px">💡 热更新请用 POST /api/admin/config（白名单字段：era_name / current_date / silver_inflow 等）</p>
      `;
    }
  } catch (e) {
    $content.innerHTML = `<p style='color:#c0392b'>加载失败：${e.message}</p>`;
  }
}

async function adminChangeRole(accountId, newRole) {
  if (!confirm(`确认将 ${accountId} 改为 ${newRole}?`)) return;
  const data = await api("/api/admin/users/role", "POST", {
    admin_id: state.account_id,
    target_account_id: accountId,
    new_role: newRole,
  });
  if (data.error) {
    alert("错误：" + data.error);
  } else {
    alert("✅ 角色已更新");
    adminShowTab("users");
  }
}

async function adminDeleteUser(accountId) {
  if (!confirm(`确认删除账户 ${accountId}?（存档保留）`)) return;
  const data = await api("/api/admin/users/delete", "POST", {
    admin_id: state.account_id,
    target_account_id: accountId,
  });
  if (data.error) {
    alert("错误：" + data.error);
  } else {
    alert("✅ 账户已删除");
    adminShowTab("users");
  }
}

async function adminDeleteSave(accountId, saveId) {
  if (!confirm(`确认删除存档 ${saveId}?`)) return;
  const data = await api("/api/admin/saves/delete", "POST", {
    admin_id: state.account_id,
    target_account_id: accountId,
    save_id: saveId,
  });
  if (data.error) {
    alert("错误：" + data.error);
  } else {
    alert("✅ 存档已删除");
    adminShowTab("saves");
  }
}

// 在存档选择页加 admin 入口
const _origShowSavesList = showSavesList;
showSavesList = async function() {
  await _origShowSavesList();
  if (state.account_role === "admin") {
    // 在 saves 列表下加一个 admin 入口按钮
    const adminBtn = document.createElement("div");
    adminBtn.style.cssText = "margin-top:16px;padding-top:16px;border-top:1px dashed #c4a878";
    adminBtn.innerHTML = `
      <button onclick="showAdminPanel()" style="padding:8px 16px;background:#5a3e1f;color:#f5e6c8;border:none;border-radius:4px;cursor:pointer;font-size:14px">
        🛠 进入管理员面板
      </button>
    `;
    document.querySelector(".start-screen").appendChild(adminBtn);
  }
};


async function submitInputWithText(inputText) {
const $btn = document.getElementById("btn_submit");
if ($btn) {
  $btn.disabled = true;
  $btn.innerHTML = "<span class='loading'>⏳ DM 正在叙述...</span>";
}

// 🆕 v1.7.15 显示弹窗
LoadingModal.show("🌀 DM 正在渲染下一回合...");

let data;
try {
  // 🆕 v1.7.15 改用 SSE 流式接口（带阶段进度）
  data = await submitInputStream(inputText);
} catch (e) {
  LoadingModal.close();
  // 🆕 v1.7.8 网络错误：恢复 UI
  if ($btn) {
    $btn.disabled = false;
    $btn.innerHTML = "行动";
  }
  const $m = document.getElementById("submit_msg");
  if ($m) $m.innerHTML = "<div class='error'>网络错误：无法连接到服务器</div>";
  throw e;
}

// 成功，关闭弹窗
LoadingModal.close();
if ($btn) {
  $btn.disabled = false;
  $btn.innerHTML = "行动";
}
if (data.error) {
  const $m = document.getElementById("submit_msg");
  if ($m) $m.innerHTML = "<div class='error'>" + data.error + "</div>";
  return;
}
renderSidebar(data);
if (data.last_narrative) {
  const lastMeta = {
    player_input: inputText,
    is_action: data.last_is_action,
    time_cost: data.last_time_cost,
    intent_type: data.last_intent_type,
    month_advanced: data.last_month_advanced,
    new_date: data.last_new_date,
  };
  appendNarrative(data.last_narrative, lastMeta);
  // 🆕 v1.7.24: 动态更新 placeholder（困境引导）
  const _narrText = typeof data.last_narrative === "string"
    ? data.last_narrative
    : (data.last_narrative.narrative || "");
  updatePlaceholderFromNarrative(_narrText);
}
// 🆕 v1.5+：渲染新一轮的内在声音选项
// 🐛 v1.6+ 修复：先清理旧选项区 + 旧 banner，避免重复
const oldVoice = document.getElementById("voice-options");
if (oldVoice) oldVoice.remove();
const oldBanner = $main.querySelector(".free-input-banner");
if (oldBanner) oldBanner.remove();

if (data.last_voice_options && data.last_voice_options.length > 0) {
  appendVoiceOptions(data.last_voice_options);
} else {
  if (data.last_narrative) {
    extractInlineOptionsFromText(data.last_narrative).then(opts => {
      if (opts && opts.length > 0) {
        appendVoiceOptions(opts);
        return;
      }
      resetInputPlaceholder();
    });
  } else {
    resetInputPlaceholder();
  }
}
$main.scrollTop = $main.scrollHeight;
}

// 🆕 v1.7.15 SSE 流式提交（带阶段进度 + 弹窗更新）
async function submitInputStream(inputText) {
const resp = await fetch("/api/input_stream", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({session_id: state.session_id, input: inputText}),
});
if (!resp.ok) {
  throw new Error(`HTTP ${resp.status}`);
}
const reader = resp.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
let finalData = null;
while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, {stream: true});
  // SSE 格式：event: <type>\ndata: <data>\n\n
  const events = buffer.split("\n\n");
  buffer = events.pop() || "";  // 最后一段可能不完整
  for (const ev of events) {
    if (!ev.trim()) continue;
    let eventType = "message";
    let dataLine = "";
    for (const line of ev.split("\n")) {
      if (line.startsWith("event:")) eventType = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLine += line.slice(5).trim();
    }
    if (!dataLine) continue;
    let data;
    try { data = JSON.parse(dataLine); } catch { data = dataLine; }
    if (eventType === "phase" && typeof data === "object") {
      LoadingModal.update(data.phase, data.message, data.progress);
    } else if (eventType === "chunk") {
      // 模拟 streaming chunk（已生成的叙事片段）
      // 这里不强求实时显示，但弹窗仍显示进度
    } else if (eventType === "done") {
      finalData = data;
    } else if (eventType === "error") {
      throw new Error(typeof data === "string" ? data : JSON.stringify(data));
    }
  }
}
if (!finalData) {
  throw new Error("SSE 结束但未收到 done 事件");
}
// 🆕 v1.7.18: done 事件已包含全量数据（不再额外 fetch /api/state）
// 背景：之前的 /api/state 在 SSE 还没彻底关闭时并发 fetch，
//       会触发 ERR_ABORTED（Connection: keep-alive 让 socket 复用）
// 修复：done 事件直接带全量数据 + 服务端 SSE Connection: close
return {
  ...finalData,
  last_voice_options: finalData.voice_options || [],
  voice_options: finalData.voice_options || [],
};
}

async function submitInput() {
// 🐛 Issue #3 修复：双击防护
if (state._submitting) return;
const $ta = document.getElementById("player_input");
const input = $ta.value.trim();
if (!input) return;
$ta.value = "";
state._submitting = true;
const $btn = document.getElementById("btn_submit");
$btn.disabled = true;
$btn.innerHTML = "<span class='loading'>⏳ DM 正在叙述...</span>";
let data;
try {
  data = await api("/api/input", "POST", {session_id: state.session_id, input});
} catch (e) {
  // 🆕 v1.7.8 网络错误：恢复输入框 + UI
  $ta.value = input;  // 恢复输入（玩家不用重打）
  $btn.disabled = false;
  $btn.innerHTML = "行动";
  document.getElementById("submit_msg").innerHTML = "<div class='error'>网络错误：无法连接到服务器，请重试</div>";
  state._submitting = false;
  return;
}
$btn.disabled = false;
$btn.innerHTML = "行动";
if (data.error) {
  // 🆕 v1.7.8 服务端错误：恢复输入（玩家可修改后重发）
  $ta.value = input;
  document.getElementById("submit_msg").innerHTML = "<div class='error'>" + data.error + "</div>";
  state._submitting = false;
  return;
}
renderSidebar(data);
if (data.last_narrative) {
  const lastMeta = {
    player_input: input,
    is_action: data.last_is_action,
    time_cost: data.last_time_cost,
    intent_type: data.last_intent_type,
    month_advanced: data.last_month_advanced,
    new_date: data.last_new_date,
  };
  appendNarrative(data.last_narrative, lastMeta);
}
// 🆕 v1.5+：渲染新一轮的内在声音选项
// 🐛 v1.6+ 修复：清理旧选项区 + banner（Tab 式 UX 一致）
const oldVoice = document.getElementById("voice-options");
if (oldVoice) oldVoice.remove();
const oldBanner = $main.querySelector(".free-input-banner");
if (oldBanner) oldBanner.remove();

if (data.last_voice_options && data.last_voice_options.length > 0) {
  appendVoiceOptions(data.last_voice_options);
} else {
  // 没有新选项 → 重置 placeholder
  $ta.placeholder = "或自由输入（你想做什么/想描述什么都可以）";
  $ta.value = "";
}
document.getElementById("submit_msg").innerHTML = "";
$main.scrollTop = $main.scrollHeight;
// 🐛 Issue #3 修复：解锁
state._submitting = false;
}

function renderSidebar(data) {
// 🆕 v1.7.30 展开 discoveries → 顶层字段
flattenDiscoveries(data);
const v = data.variables || {};
const apCur = data.action_points_current ?? 3;
const apMax = data.action_points_max ?? 3;
let apDots = "";
for (let i = 0; i < apMax; i++) {
  apDots += `<div class="ap-dot${i < apCur ? " filled" : ""}"></div>`;
}
// 🆕 v1.7.26 侧边栏固化数据
const sb = data.sidebar_data || {};
const tasks = sb.active_tasks || [];
const deadlines = sb.upcoming_deadlines || [];
const fin = sb.financial_status || {};

// 渲染任务列表
const tasksHtml = tasks.length > 0
  ? tasks.map(t => {
      const icon = t.urgency === "high" ? "🔴" : "🟡";
      // 🆕 v1.7.28：每个任务加 ✓ 完成按钮 + 紧急度 badge
      const safeTitle = escapeHtml(t.title || "");
      const tid = `task-${escapeHtml((t.title || "").replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, "-"))}`;
      return `
        <div class="sidebar-task" id="${tid}">
          <span class="task-icon">${icon}</span>
          <span class="task-title">${safeTitle}</span>
          <button class="task-done-btn" data-title="${escapeHtml(t.title || "")}" title="标记完成">✓</button>
        </div>`;
    }).join("")
  : "<div style='color:#5a4a30;font-size:12px'>暂无待办</div>";

// 渲染还债日
const deadlinesHtml = deadlines.length > 0
  ? deadlines.map(d => {
      const days = d.days_estimate ? `约${d.days_estimate}天后` : "近期";
      const amount = d.amount ? ` · ${escapeHtml(d.amount)}` : "";
      return `<div class="sidebar-deadline">
        <div class="deadline-name">${escapeHtml(d.name || "")}</div>
        <div class="deadline-meta">${days}${amount}</div>
      </div>`;
    }).join("")
  : "<div style='color:#5a4a30;font-size:12px'>近期无还债</div>";

// 渲染财务
const finHtml = `
  ${fin.cash !== undefined ? `<div class="stat-line"><span class="label">💰 现金</span><span class="val">${fin.cash} 两</span></div>` : ""}
  ${fin.rice_days !== undefined ? `<div class="stat-line"><span class="label">🍚 米粮</span><span class="val">${fin.rice_days} 日</span></div>` : ""}
  ${fin.monthly_burn !== undefined ? `<div class="stat-line"><span class="label">📉 月耗</span><span class="val">约 ${fin.monthly_burn} 两</span></div>` : ""}
  ${fin.family ? `<div class="sidebar-fin-extra">👨‍👩‍👧 ${escapeHtml(fin.family)}</div>` : ""}
  ${fin.external ? `<div class="sidebar-fin-extra">📢 ${escapeHtml(fin.external)}</div>` : ""}
  ${Object.keys(fin).length === 0 ? "<div style='color:#5a4a30;font-size:12px'>财务数据待更新</div>" : ""}
`;

$side.innerHTML = `
  <h2>${data.era_name || "万历十五年"}</h2>
  <div class="stat-line"><span class="label">回合</span><span class="val">${data.round_number}</span></div>
  <div class="stat-line"><span class="label">日期</span><span class="val">${data.current_date}</span></div>
  <div class="stat-line"><span class="label">身份</span><span class="val">${data.selected_identity || "?"} (${data.player_gender || "?"})</span></div>
  <div class="stat-line"><span class="label">Session</span><span class="val" style="font-size:11px">${(data.session_id || "").slice(-8)}</span></div>

  <h3>本月行动点</h3>
  <div class="action-point-bar">${apDots}<span class="ap-label">${apCur}/${apMax}</span></div>
  <div style="color:#a08858;font-size:11px;line-height:1.5;margin-top:4px">
    ⚡ 行动点耗尽时自动跳到下月。<br>
    💬 问询/观察不消耗行动点，可继续追问。
  </div>

  <!-- 🆕 v1.7.30 我的档案折叠区（6 区：财务/家人/谱系/财产/库存/位置） -->
  <button class="sidebar-my-profile-btn" onclick="openMyProfile()" title="查看完整档案">👤 我的档案</button>
  <div class="sb-section sb-section-cash" data-section="cash">
    <div class="sb-section-header" onclick="toggleSbSection('cash')">
      💰 财务 <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="cash">
      <div class="stat-line"><span class="label">💵 现金</span><span class="val">${(data.cash ?? 0).toFixed(2)} 两</span></div>
      <div class="stat-line"><span class="label">🍚 存粮</span><span class="val">${(data.rice ?? 0).toFixed(1)} 石</span></div>
      <div class="stat-line"><span class="label">💳 欠债</span><span class="val">${(data.debt ?? 0).toFixed(2)} 两</span></div>
      <div class="stat-line"><span class="label">📉 月耗</span><span class="val">${(data.monthly_burn ?? 0).toFixed(2)} 两</span></div>
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('cash')">📊 全部</button>
      </div>
    </div>
  </div>
  <div class="sb-section sb-section-location" data-section="location">
    <div class="sb-section-header" onclick="toggleSbSection('location')">
      📍 当前位置 <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="location">
      <div class="stat-line"><span class="label">城市</span><span class="val">${escapeHtml(CITY_DISPLAY[data.current_city] || data.current_city || "盛泽镇")}</span></div>
    </div>
  </div>
  <div class="sb-section sb-section-family" data-section="family">
    <div class="sb-section-header" onclick="toggleSbSection('family')">
      👨‍👩‍👧 家人 (${(data.family_members || []).length}) <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="family">
      ${(data.family_members || []).slice(0, 4).map(m => `
        <div class="sb-item">
          <span class="sb-item-name">${escapeHtml(m.name || "?")}</span>
          <span class="sb-item-meta">${escapeHtml(RELATION_DISPLAY[m.relation] || m.relation || "")} · ${escapeHtml(CITY_DISPLAY[m.location] || m.location || "盛泽")}</span>
        </div>
      `).join("") || "<div style='color:#5a4a30;font-size:12px'>暂无家人</div>"}
      ${(data.family_members || []).length > 4 ? `<div class="sb-item-meta">… 还有 ${data.family_members.length - 4} 位</div>` : ""}
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('family')">📊 全部</button>
      </div>
    </div>
  </div>
  <div class="sb-section sb-section-genealogy" data-section="genealogy">
    <div class="sb-section-header" onclick="toggleSbSection('genealogy')">
      🌳 谱系 (${(data.genealogy || []).length}) <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="genealogy">
      ${(data.genealogy || []).filter(e => e.is_known_to_player).slice(0, 3).map(e => `
        <div class="sb-item">
          <span class="sb-item-name">${escapeHtml(e.name || "?")}</span>
          <span class="sb-item-meta">${escapeHtml(RELATION_DISPLAY[e.relation] || e.relation || "")}${e.alive ? "" : "（已逝）"}</span>
        </div>
      `).join("") || "<div style='color:#5a4a30;font-size:12px'>尚无记录</div>"}
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('genealogy')">📊 全部</button>
      </div>
    </div>
  </div>
  <div class="sb-section sb-section-property" data-section="property">
    <div class="sb-section-header" onclick="toggleSbSection('property')">
      🏘️ 城市财产 <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="property">
      ${Object.keys(data.city_properties || {}).length > 0
        ? Object.entries(data.city_properties).map(([city, props]) => `
          <div class="sb-item">
            <span class="sb-item-name">${escapeHtml(CITY_DISPLAY[city] || city)}</span>
            <span class="sb-item-meta">${props.length} 处 · ${props.reduce((s, p) => s + (p.value || 0), 0).toFixed(0)} 两</span>
          </div>
        `).join("")
        : "<div style='color:#5a4a30;font-size:12px'>尚无</div>"
      }
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('property')">📊 全部</button>
      </div>
    </div>
  </div>
  <div class="sb-section sb-section-inventory" data-section="inventory">
    <div class="sb-section-header" onclick="toggleSbSection('inventory')">
      📦 库存 <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="inventory">
      ${Object.keys(data.inventory || {}).length > 0
        ? Object.entries(data.inventory).map(([city, items]) => `
          <div class="sb-item">
            <span class="sb-item-name">${escapeHtml(CITY_DISPLAY[city] || city)}</span>
            <span class="sb-item-meta">${items.length} 项 · ${items.reduce((s, it) => s + (it.qty || 0), 0)} 件</span>
          </div>
        `).join("")
        : "<div style='color:#5a4a30;font-size:12px'>尚无</div>"
      }
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('inventory')">📊 全部</button>
      </div>
    </div>
  </div>
  <div class="sb-section sb-section-letters" data-section="letters">
    <div class="sb-section-header" onclick="toggleSbSection('letters')">
      📜 信件 (${(data.letters || []).length}) <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="letters">
      ${(data.letters || []).slice(0, 3).map(l => `
        <div class="sb-item">
          <span class="sb-item-name">${escapeHtml(l.from || "?")} → ${escapeHtml(l.to || "我")}</span>
          <span class="sb-item-meta">${escapeHtml(l.date || "")} · ${l.status === "unread" ? "🔴 未读" : "✓"}</span>
        </div>
      `).join("") || "<div style='color:#5a4a30;font-size:12px'>尚无信件</div>"}
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('letters')">📊 全部</button>
      </div>
    </div>
  </div>
  <div class="sb-section sb-section-facts" data-section="facts">
    <div class="sb-section-header" onclick="toggleSbSection('facts')">
      💡 知识 (${(data.facts || []).length}) <span class="sb-section-toggle">▸</span>
    </div>
    <div class="sb-section-body" data-body="facts">
      ${(data.facts || []).slice(0, 3).map(f => `
        <div class="sb-item">
          <span class="sb-item-name">${escapeHtml((f.text || "").slice(0, 18))}${f.text && f.text.length > 18 ? "…" : ""}</span>
          <span class="sb-item-meta">${f.heard_from ? "👤 " + escapeHtml(f.heard_from) : ""}</span>
        </div>
      `).join("") || "<div style='color:#5a4a30;font-size:12px'>尚无</div>"}
      <div class="sb-section-actions">
        <button class="sb-section-more" onclick="openMyProfile('facts')">📊 全部</button>
      </div>
    </div>
  </div>

  <!-- 🆕 v1.7.26 固化面板：任务 / 还债 / 财务 -->
  <h3>📋 待办 (${tasks.length})</h3>
  <div class="sidebar-tasks">${tasksHtml}</div>

  <!-- 🆕 v1.7.28：手动添加任务（剧情未提及的） -->
  <div class="sidebar-task-add">
    <input id="new-task-input" type="text" placeholder="+ 添加待办…" maxlength="40" />
    <button id="new-task-btn">＋</button>
  </div>
  <div class="sidebar-task-history" onclick="toggleCompleted()" title="点击查看已完成">
    已完成 ${data.completed_tasks_count || 0}
  </div>

  <h3>⏰ 还债日 (${deadlines.length})</h3>
  <div class="sidebar-deadlines">${deadlinesHtml}</div>

  <h3>💰 财务</h3>
  <div class="sidebar-fin">${finHtml}</div>

  <div class="sidebar-secondary">
    <h3>已解锁认知 (${(data.unlocked_insights || []).length}/14)</h3>
    <div>${(data.unlocked_insights || []).map(i => `<span class="insight-tag">${i}</span>`).join("") || "<span style='color:#5a4a30;font-size:12px'>尚无</span>"}</div>

    <h3>已触发事件 (${(data.triggered_events || []).length})</h3>
    <div>${(data.triggered_events || []).map(e => `<span class="event-tag">${e}</span>`).join("") || "<span style='color:#5a4a30;font-size:12px'>尚无</span>"}</div>

    <h3>关键变量</h3>
    ${Object.entries(v).map(([k, val]) =>
      `<div class="stat-line"><span class="label">${k}</span><span class="val">${val}</span></div>`
    ).join("")}
  </div>

  <!-- 🆕 v1.6.6 侧边栏底部快捷按钮（剧情回顾 + 名词表） -->
  <div class="sidebar-actions">
    <button class="sidebar-action-btn" onclick="openRecap()" title="查看最近剧情回顾">
      📖 剧情回顾
    </button>
    <button class="sidebar-action-btn" onclick="openGlossary()" title="查看明朝名词解释">
      📚 名词表
    </button>
    <button class="sidebar-action-btn" onclick="openCharacterWiki()" title="查看本存档出现的人物 + 支线一致性">
      🕸️ 人物关系
    </button>
  </div>
`;

  // 🆕 v1.7.28：挂接任务完成按钮 + 添加按钮（render 后绑定，避免 XSS 内嵌 on*）
  document.querySelectorAll(".task-done-btn").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const title = btn.dataset.title;
      if (title) completeTask(title);
    });
  });
  const addBtn = document.getElementById("new-task-btn");
  const addInput = document.getElementById("new-task-input");
  if (addBtn && addInput) {
    addBtn.addEventListener("click", () => addTaskFromInput(addInput));
    addInput.addEventListener("keypress", e => {
      if (e.key === "Enter") addTaskFromInput(addInput);
    });
  }

  // 🆕 v1.7.30 折叠区初始化：默认折叠 + localStorage 恢复
  document.querySelectorAll(".sb-section").forEach($section => {
    const name = $section.dataset.section;
    let collapsed = true;  // 默认折叠
    try {
      const saved = localStorage.getItem(`hfe_sb_${name}_collapsed`);
      if (saved === "0") collapsed = false;
    } catch (_) {}
    const $body = $section.querySelector(".sb-section-body");
    const $toggle = $section.querySelector(".sb-section-toggle");
    if ($body) {
      $body.classList.toggle("collapsed", collapsed);
    }
    if ($toggle) {
      $toggle.textContent = collapsed ? "▸" : "▾";
    }
  });
}

// 🆕 v1.7.28：任务完成 API 调用
async function completeTask(title) {
  if (!currentSessionId) return;
  try {
    const data = await api("/api/task/complete", "POST", {
      session_id: currentSessionId,
      title,
    });
    if (data.status === "completed") {
      // 重新拉取 state
      await refreshSidebar();
    } else if (data.status === "not_found") {
      console.warn("任务未找到:", title);
    }
  } catch (e) {
    console.error("completeTask failed:", e);
  }
}

// 🆕 v1.7.28：手动添加任务 API 调用
async function addTaskFromInput(inputEl) {
  const title = (inputEl.value || "").trim();
  if (!title || !currentSessionId) return;
  try {
    const data = await api("/api/task/add", "POST", {
      session_id: currentSessionId,
      title,
      urgency: "normal",
    });
    if (data.status === "added" || data.status === "duplicate") {
      inputEl.value = "";
      await refreshSidebar();
    }
  } catch (e) {
    console.error("addTask failed:", e);
  }
}

async function refreshSidebar() {
  // 调用 /api/state 拉新侧边栏（替代完整刷新）
  if (!currentSessionId) return;
  try {
    const data = await api("/api/state?session_id=" + encodeURIComponent(currentSessionId), "GET");
    // 仅重渲染侧边栏，不再触发叙事重放
    if (typeof renderSidebar === "function") renderSidebar(data);
  } catch (e) {
    console.error("refreshSidebar failed:", e);
  }
}

// 🆕 v1.7.28：查看已完成任务（简单弹层）
function toggleCompleted() {
  // 复用最近一次 /api/state 拉到的 completed_tasks_count；如需详细列表，弹层再发 /api/state
  alert("已完成任务历史请查看存档（完成项已存档，不删除）");
}

function escapeHtml(s) {
if (!s) return "";
return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// 🆕 v1.6.7 架构重构：删除 JS 端 stripSkillMetadata（重复实现）
// 改用 /api/sanitize 端点调用服务端 narrative_sanitizer.py
// 服务端是单一权威实现，避免前后端正则漂移

// 🆕 v1.6.9 前端兜底：调用服务端 merge_voice_options（避免 JS 重复实现）
async function extractInlineOptionsFromText(text) {
if (!text) return [];
try {
  const data = await api("/api/merge_voice_options", "POST", {
    structured_options: [],
    narrative_text: text,
  });
  return data.options || [];
} catch (e) {
  return [];
}
}

renderStart();

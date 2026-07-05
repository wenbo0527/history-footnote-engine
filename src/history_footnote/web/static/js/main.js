// 🆕 v1.7.3 历史注脚体验引擎 - 主脚本
// 拆分自 web_server.py（原 INDEX_HTML 内嵌 JS）
// v1.6+ 起累积：开场 + 游戏循环 + 弹层 + 移动端

let state = {
session_id: null,
identity: null,
gender: null,
era_id: "wanli1587",
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
wizard.step = 1;
renderWizard();
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
function resetInputPlaceholder() {
const $ta = document.getElementById("player_input");
if ($ta) {
  $ta.placeholder = "或自由输入（你想做什么/想描述什么都可以）";
  $ta.value = "";
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
if (!voiceOptions || voiceOptions.length === 0) return;
const div = document.createElement("div");
div.className = "voice-options";
div.id = "voice-options";
div.innerHTML = `
  <div class="voice-options-header">
    🎭 你脑海中的声音——选择按哪个行动
    <span class="voice-options-hint">或点下方"自由输入"</span>
  </div>
  <div class="voice-options-grid">
    ${voiceOptions.map((opt, i) => `
      <button class="voice-option-btn" onclick="submitVoiceOption(${i}, ${JSON.stringify(opt).replace(/"/g, '&quot;')})">
        <span class="voice-name">${escapeHtml(opt.voice_name || '?')}</span>
        <span class="voice-intent">${escapeHtml(opt.intent_text || '?')}</span>
      </button>
    `).join("")}
    <button class="voice-option-btn other" onclick="showFreeInputTab()">
      <span class="voice-name">✍️ 自由输入</span>
      <span class="voice-intent">都不对？自己描述要做什么</span>
    </button>
  </div>
`;
// 🆕 v1.7.7 改：插到 action-area 内部 input-area 之前
// 视觉上"声音 + 输入"是一个整体
const $actionArea = document.getElementById("action-area");
const $inputArea = document.getElementById("input-area");
if ($actionArea && $inputArea && $actionArea.contains($inputArea)) {
  $actionArea.insertBefore(div, $inputArea);
} else if ($inputArea && $main.contains($inputArea)) {
  $main.insertBefore(div, $inputArea);
} else {
  $main.appendChild(div);
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
  },
  update(phase, message, progress) {
    if (!this.overlay) return;
    const $phase = this.overlay.querySelector(".loading-phase");
    const $bar = this.overlay.querySelector(".loading-progress-bar");
    if ($phase && message) $phase.textContent = message;
    if ($bar && typeof progress === "number") $bar.style.width = progress + "%";
  },
  close() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
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
// done 事件已包含 voice_options / intent_type / time_cost
// 但还需要 last_narrative + last_is_action + last_time_cost + last_intent_type
// 这些是后端 _format_state 输出的，从 state.narrative_history[-1] 读取
// 简单做法：再发个 GET /api/state 拿全量
let stateData = {};
try {
  stateData = await api("/api/state?session_id=" + state.session_id);
} catch (e) {
  console.warn("Failed to load /api/state after stream", e);
}
return {
  ...finalData,
  last_narrative: stateData.last_narrative || null,
  last_is_action: stateData.last_is_action,
  last_time_cost: stateData.last_time_cost,
  last_intent_type: stateData.last_intent_type,
  last_month_advanced: stateData.last_month_advanced,
  last_new_date: stateData.last_new_date,
  current_date: stateData.current_date,
  round_number: stateData.round_number,
  action_points_current: stateData.action_points_current,
  action_points_max: stateData.action_points_max,
  variables: stateData.variables,
  // voice_options 已经在 finalData 里
  last_voice_options: finalData.voice_options || [],
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
const v = data.variables || {};
const apCur = data.action_points_current ?? 3;
const apMax = data.action_points_max ?? 3;
let apDots = "";
for (let i = 0; i < apMax; i++) {
  apDots += `<div class="ap-dot${i < apCur ? " filled" : ""}"></div>`;
}
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

  <div class="sidebar-secondary"> <!-- 🆕 v1.6.2 移动端隐藏次要信息 -->
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

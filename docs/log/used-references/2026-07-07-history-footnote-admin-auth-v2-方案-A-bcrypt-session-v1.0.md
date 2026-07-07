# 历史注脚 admin 鉴权升级 v2 · 方案 A · bcrypt + session cookie

| 字段 | 值 |
|:---|:---|
| **文档版本** | v1.0（初稿 · 待 review）|
| **创建时间** | 2026-07-07 08:55 CST |
| **作者** | 钟离 🏛️ |
| **状态** | 📋 计划中（文博 8:52 同意方案 A）|
| **目标版本** | v1.8.0（不阻塞主线 v1.7.x）|
| **前置版本** | v1.7.46（bcdea42 + 3b7cb64 已部署）|
| **估计工时** | ~2.5h（含缓冲）|
| **关联 commit** | `bcdea42`（admin.py 鉴权）· `3b7cb64`（main.js token 前端）|

---

## 🎯 TL;DR

**明文 ADMIN_TOKEN (`hf-xUl...guBd`) → bcrypt 密码 + 24h HttpOnly session cookie + audit log**

> 一句话：写死的"密码 = 一把万能钥匙"模式 → "用户名+密码登录 → 服务端签发临时通行证 → 每操作自动留痕"。

---

## 1. 背景 & 风险（v1.7.46 现状）

| 风险 | 现状证据 | 实际影响 |
|:---|:---|:---|
| **Token 明文流转** | `.env` + `main.js` 浏览器 prompt + `sessionStorage` 都有 | 任何 leak 点 = 永久 admin |
| **不可撤销** | 改 token = 必重启服务，所有登录态全断 | 紧急事件响应慢 |
| **不可追溯** | admin 操作无 audit log | 出事不知道谁干的 |
| **不可轮换** | 无 expiry，泄露 = 永久有效 | 单 secret 控全局 |
| **不可撤销多端** | 1 个 token 控所有客户端 | 1 台电脑被偷 = 全网裸奔 |

→ 当前是 **"单 secret 控全局"** 模型，单人项目暂时够用；多用户/公网部署必爆。

---

## 2. 目标 & 非目标

### ✅ 目标（必须做）
1. admin 鉴权从明文 token → **bcrypt 密码 + 短期 session**
2. 每 session 操作自动落 **audit log**（who/what/when/where）
3. 浏览器侧提供完整 **登录/登出** UI（替代 `window.prompt()`）
4. 单点登录失败 → **5 次锁定 15 min**（防 brute force）

### ❌ 非目标（明确不做）
- 不引入第三方 OAuth/JWT（overkill）
- 不重写 `account_system.py` 整体（增量 patch）
- 不动 player-facing 侧的鉴权（user account 体系独立管理）
- 不动 `ensure_default_admin()` 的 token 兜底逻辑（保留为脚本/CLI fallback）

---

## 3. 架构

### 3.1 时序图（login → admin 操作 → logout）

```
┌────────┐         ┌──────────────┐         ┌──────────────┐
│ Browser│         │ Frontend (SPA)│         │ Backend      │
└───┬────┘         └──────┬───────┘         └──────┬───────┘
    │                     │                       │
    │  1. 点 admin 按钮    │                       │
    ├─────────────────────►│                       │
    │                     │  2. POST /admin/login  │
    │                     │  {username, password}  │
    │                     ├──────────────────────►│
    │                     │                       │ 3. bcrypt 验密
    │                     │                       │ 4. 创建 session
    │                     │                       │ 5. 写 audit (login ok)
    │                     │  ◄───────────────────┤  Set-Cookie session_id=...
    │                     │  200 {account}        │ HttpOnly; SameSite=Lax
    │                     │                       │ 6. 写 audit (login fail if err)
    │  ◄──────────────────┤                       │
    │  显示 admin 面板      │                       │
    │                     │                       │
    │                     │  7. GET /admin/users   │
    │                     ├──────────────────────►│
    │                     │  Cookie: session_id   │
    │                     │                       │ 8. 查 session 表
    │                     │                       │ 9. sliding 续期
    │                     │  ◄───────────────────┤ 10. 写 audit (action)
    │                     │  200 {users:[...]}    │
    │                     │                       │
    │  点 logout           │                       │
    ├─────────────────────►│                       │
    │                     │ 11. POST /admin/logout │
    │                     ├──────────────────────►│
    │                     │                       │ 12. 删 session
    │                     │                       │ 13. 写 audit (logout)
    │                     │  ◄───────────────────┤
    │  ◄──────────────────┤ 200                    │
    │  回登录表单          │                       │
```

### 3.2 数据流分层

| 层 | 组件 | 关键动作 |
|:---|:---|:---|
| **存** | `accounts.json` + **新增 `sessions.json`** | 增 password_hash / session 表 |
| **运** | `account_system.py` + **新增 `session_manager.py`** | bcrypt + sliding session |
| **路** | `web_server/routers/admin.py` + **新增 `audit.py`** | login/logout + audit hook |
| **前端** | `main.js` | 表单 + logout 按钮 |
| **配** | `.env` | 移除 `ADMIN_TOKEN`，加 `SESSION_HMAC_SECRET`（server 签 cookie）+ `AUDIT_LOG_PATH` |

---

## 4. 数据 schema 变化

### 4.1 `accounts.json`（增量字段）

```jsonc
// 增加 2 个字段（不破坏老数据，老账户 password_hash="" = 无密码，回退到 ADMIN_TOKEN）
{
  "accounts": [
    {
      "account_id": "00000000",
      "username": "admin",
      // ... 老字段全保留 ...
      "password_hash": "scrypt:32768:8:1$<salt-b64>$<hash-b64>",
      "password_set_at": "2026-07-07T10:00:00+08:00"
    }
  ]
}
```

**关键决策**：用 `hashlib.scrypt`（Python stdlib，3.6+）而非 `bcrypt` —— **零新增依赖**。

### 4.2 `sessions.json`（全新文件）

```jsonc
{
  "sessions": [
    {
      "session_id": "8f3c2e1a4b5d6e7f9a0b1c2d3e4f5a6b",  // 32 hex
      "account_id": "00000000",
      "created_at": "2026-07-07T08:55:00+08:00",
      "last_active_at": "2026-07-07T08:55:00+08:00",
      "expires_at": "2026-07-08T08:55:00+08:00",        // 24h sliding
      "ip": "118.196.79.130",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) ..."
    }
  ]
}
```

### 4.3 `audit.log`（全新 JSONL，每行 1 条 admin 操作）

```jsonc
// 每行 1 个 JSON 对象，append-only
{"ts":"2026-07-07T08:55:00.123+08:00","event":"login_ok","session_id":"8f3c...","account_id":"00000000","ip":"...","user_agent":"..."}
{"ts":"2026-07-07T08:55:15.456+08:00","event":"action","session_id":"8f3c...","account_id":"00000000","route":"/api/admin/users","method":"GET","status":200,"latency_ms":12}
{"ts":"2026-07-07T09:00:00.789+08:00","event":"login_fail","ip":"...","reason":"bad_password","attempt":1,"account_id":"00000000"}
{"ts":"2026-07-07T09:00:01.234+08:00","event":"account_locked","account_id":"00000000","until":"2026-07-07T09:15:00+08:00"}
```

事件类型：`login_ok` / `login_fail` / `account_locked` / `action` / `logout` / `session_expired`

---

## 5. API 变化

### 5.1 新增

| Method | Path | Body | 返回 | 说明 |
|:---|:---|:---|:---|:---|
| `POST` | `/api/admin/login` | `{account_id, password}` | `200 {account}` + Set-Cookie / `401 {error}` | bcrypt 验密；5 次错锁 15min |
| `POST` | `/api/admin/logout` | (Cookie 必带) | `200` / `401` | 删 session + 清 cookie |
| `GET` | `/api/admin/whoami` | (Cookie) | `200 {account}` / `401` | 当前 session 信息（前端定时校验）|

### 5.2 修改

| Method | Path | 变化 |
|:---|:---|:---|
| 10 个 `/api/admin/*` 路由 | `_check_admin_token(headers)` → `_check_session(cookie)` |
| `_require_admin()` | 先 session，后回退 token（兼容老脚本）|

### 5.3 移除（可选，建议保留作 fallback）

- `.env` 的 `ADMIN_TOKEN`（保留 1 个版本作为 script 调用 fallback，下下版本移除）

### 5.4 失败锁定策略

```
连续失败 N=5 次 → 锁定 15 min
- 锁定状态存 account_system（不存 session）
- 锁定期间 admin/login 一律返回 429 Too Many Requests
- TTL 到期自动解除
```

---

## 6. 前端变化（`main.js`）

### 6.1 `adminAuthPrompt()` → `adminLoginForm()`（重写）

```javascript
// 之前：window.prompt("🛡️ 输入 ADMIN_TOKEN")
// 之后：模态框表单
async function adminLoginForm() {
  if (await hasValidSession()) return true; // 已登录直接过
  // 渲染模态框（username + password input）
  // submit 后调 /api/admin/login
  // 成功后 Set-Cookie 自动生效 → return true
  // 失败：alert + 显示错误计数
}
```

UI 草图：

```
┌─────────────────────────────────────┐
│  🛡️  管理员登录                       │
│                                     │
│  账户 ID: [_________________]        │
│  密   码: [_________________]        │
│                                     │
│         [ 登录 ]  [ 取消 ]            │
│                                     │
│  ⚠️ 5 次错将锁定 15 分钟             │
└─────────────────────────────────────┘
```

### 6.2 logout 按钮（admin 面板 header 新增）

```html
<button onclick="adminLogout()">🚪 登出</button>
```

```javascript
async function adminLogout() {
  await api('/api/admin/logout', 'POST');
  location.reload();  // 回到登录表单
}
```

### 6.3 失败计数显示

```
❌ 密码错误（剩余 3 次机会）  ← alert
❌ 账户已锁定 14 分 35 秒     ← alert
```

---

## 7. 关键设计要点（必读）

| 点 | 设计 |
|:---|:---|
| **Cookie 属性** | `HttpOnly; Secure; SameSite=Lax; Path=/`（防 XSS 偷 cookie，防 CSRF）|
| **Session 续期** | 每次 admin 操作刷新 `last_active_at` 和 `expires_at`（sliding window）|
| **过期清理** | 服务启动时 + 每小时 cron 删过期 session |
| **密码强度** | min 12 字符，含大小写 + 数字 + 符号（前 + 后端双校验）|
| **失败锁定** | 5 次错密码锁定 15min（防 brute force）|
| **Audit 字段** | ts + event + session_id + account_id + route + method + status + latency_ms + ip + user_agent |
| **Audit 存储** | JSONL append-only；每天 rotation（logrotate 或脚本）|
| **HMAC 签 cookie** | `session_id=<id>.<HMAC-SHA256>` 防 cookie 伪造 |
| **回退兼容** | `.env` 的 `ADMIN_TOKEN` 保留 v1.8 + v1.9，v2.0 移除 |
| **会话清理** | 启动时删 expired；后台 thread 每小时跑一次 |

---

## 8. 实施 WBS（8 步 · 总 ~2.5h）

| # | 任务 | 文件 | 时间 | 验证 |
|:--|:---|:---|:---:|:---|
| **1** | Account: 加 `set_password` / `verify_password` (scrypt) | `account_system.py` | 20m | `scripts/test_password.py` |
| **2** | Account: 加锁定逻辑（lock_until / increment_fail） | `account_system.py` | 15m | 单测 |
| **3** | `session_manager.py`（CRUD + 过期清理 + HMAC 签 cookie）| **新文件** | 25m | `scripts/test_session_manager.py` |
| **4** | 路由 `/api/admin/login` + `/api/admin/logout` + `/api/admin/whoami` | `web_server/routers/admin.py` | 30m | curl 6 项 e2e |
| **5** | `_check_admin_token` → `_check_session`（10 handlers + _require_admin）| `admin.py` | 15m | 6 项 e2e (老测试保留) |
| **6** | `audit.py` 中间件 + 写 `audit.log` | **新文件** + `admin.py` | 20m | JSONL 校验 + 字段完整 |
| **7** | `main.js`: prompt → form + logout + failure lock UI | `main.js` | 30m | 浏览器 e2e (4 场景) |
| **8** | admin bootstrap 整合：`ensure_default_password()` 一次设密 CLI | `scripts/set_admin_password.py` | 15m | CLI + 自动生成 |

---

## 9. 测试计划

### 9.1 单元测试（scripts/*.py，新写 2 个）

| 脚本 | 用例 |
|:---|:---|
| `test_password.py` | set → verify roundtrip / 错密验 / salt 随机 / 时长合规 |
| `test_session_manager.py` | create / lookup / extend / expire / delete / cookie 签验 |

### 9.2 e2e（curl，6 项老测试 + 5 项新测试）

| # | 场景 | 期望 |
|:--|:---|:---|
| 老 1 | 无 token + 无 cookie | 401 |
| 老 2 | 正 ADMIN_TOKEN（兼容） | 200 |
| 老 3 | 正 cookie | 200 |
| 老 4 | 错 token | 401 |
| 老 5 | header 方式 token | 200 |
| 老 6 | 非 admin 账户 | 403 |
| **新 1** | 错密码 5 次 | 第 6 次返回 429 + 锁定提示 |
| **新 2** | 锁定期间再登录 | 429 + `retry_after` |
| **新 3** | 正确登录 | 200 + Set-Cookie 会话生效 |
| **新 4** | 过期 session（手动改 expires_at）| 401 + 自动清理 |
| **新 5** | logout 后 cookie 失效 | 401 |

### 9.3 浏览器 e2e（4 场景）

| # | 场景 | 验证 |
|:--|:---|:---|
| B1 | admin 面板按钮 → 登录表单渲染 | URL 不变，form 出来 |
| B2 | 错密码提示 | alert 文案 + 失败计数 |
| B3 | 正确登录 → 进 admin 面板 | 4 tab 内容加载 |
| B4 | logout → 回登录页 | cookie 清空 |

---

## 10. Rollout 计划

### 10.1 兼容性策略（**关键**）

- 老 `ADMIN_TOKEN` 仍存在于 `.env` —— v1.8 / v1.9 期间 **双轨制**：
  - 优先 `_check_session` (cookie)
  - cookie 缺失时回退 `_check_admin_token` (header / query)
  - 这样老脚本（cron / feishu bot）继续可用
- v2.0 完全移除 ADMIN_TOKEN 回退

### 10.2 灰度

| 阶段 | 范围 | 时间 |
|:---|:---|:---|
| Phase 0 | dev 机器本地测试完毕 | 0d |
| Phase 1 | 远程 staging（如果有）/ 直接主站 25% 用户 | 1d |
| Phase 2 | 全量 | 1d 后 |

> 当前架构无 staging 域名 → 直接上主站，但 audit log 立即开，1 天内看 log 确认无异常

### 10.3 回滚

| 触发 | 行动 |
|:---|:---|
| 5xx > 5% | `git revert <commit>` + 服务重启 |
| Login 401 风暴 | 临时切回 ADMIN_TOKEN 单鉴权（保留回退逻辑）|
| 数据损坏 | v1.7.46 commit `bcdea42` 仍可签出 |

---

## 11. 未来演进（v1.9+ · 不在本工单）

| 需求 | 演进 |
|:---|:---|
| 多人 admin | RBAC：moderator 角色（只读）+ superadmin（写）|
| 公网部署 | OAuth (GitHub/Google) per-user |
| 高度敏感操作 | MFA：TOTP (RFC 6238) |
| 第三方审计 | audit.log → ELK / Loki / CloudWatch |
| 邀请系统 | admin 创建 invite_code → 邀请非 owner 享受只读权限 |

---

## 12. 安全 Checklist（实施时逐条勾）

- [ ] 不存明文密码，只存 scrypt hash
- [ ] Cookie `HttpOnly; Secure; SameSite=Lax; Path=/`
- [ ] Session ID 32 hex（128 bit entropy）
- [ ] HMAC 签 cookie 防篡改（用 `SESSION_HMAC_SECRET` env）
- [ ] 密码 min 12 char + 字符类型校验
- [ ] 失败 5 次锁 15min（account-level，不是 session-level）
- [ ] Session 24h expiry + sliding 续期
- [ ] 服务启动 + 每小时 cron 删过期 session
- [ ] Audit log append-only + 每天 rotation
- [ ] 所有 admin 路由**强制**走 `_check_session`（无任何豁免）
- [ ] `IP` 字段从 `X-Forwarded-For` 头取（nginx 已配）
- [ ] Logout 真删 session（不只清 cookie）
- [ ] 测试覆盖 11 项 e2e + 4 项浏览器

---

## 13. 参考资料

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Python `hashlib.scrypt` 文档](https://docs.python.org/3/library/hashlib.html#hashlib.scrypt)
- [RFC 6265 - HTTP State Management Mechanism (Cookies)](https://www.rfc-editor.org/rfc/rfc6265)
- [RFC 6238 - TOTP（未来 MFA 用）](https://www.rfc-editor.org/rfc/rfc6238)
- 公司内部：`memory/sop/security-and-hardening.md`（如有）

---

## 14. 决策点（已拍）

| 选项 | 拍 | 备注 |
|:---|:---|:---|
| **A**（bcrypt + session cookie）| ✅ 文博 8:52 同意 | 本文 |
| B (JWT) | ❌ | overkill |
| C (维持现状) | ❌ | 高风险 |
| D (现状 + 月度 rotate) | ❌ | 治标不治本 |

---

## 15. 下一步

| 选项 | 含义 |
|:---|:---|
| **A**（推荐）| 立即开始实施 WBS（按 8 步跑完 + commit + push + e2e）|
| **B** | 先实施 1-3（后端核心 1h），下 session 做 4-8（路由+前端+审计）|
| **C** | 等 review 后再说（可能调整方案）|
| **D** | 暂缓，先做其他事 |

---

*文档结束 · v1.0 · 2026-07-07 08:55 CST · 钟离 🏛️*

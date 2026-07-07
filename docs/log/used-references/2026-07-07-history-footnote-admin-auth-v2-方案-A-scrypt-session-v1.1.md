# 历史注脚 admin 鉴权升级 v2 · 方案 A · scrypt + session cookie

| 字段 | 值 |
|:---|:---|
| **文档版本** | v1.1（v1.0 + 简化修订）|
| **创建时间** | 2026-07-07 08:55 CST（v1.0）· 09:30 v1.1 |
| **作者** | 钟离 🏛️ |
| **状态** | 🚀 实施中（文博 9:30 同意按 v1.1 实施）|
| **目标版本** | v1.8.0 |
| **前置版本** | v1.7.47（1b47647 已部署）|
| **估计工时** | ~2h（无老账户，简化版）|
| **关联 commit** | `1b47647`（通用菜单+admin 修复）· 8b78237（smoke）|

---

## 🎯 TL;DR

**明文 ADMIN_TOKEN (`hf-xUl...guBd`) → scrypt 密码 + 24h HttpOnly session cookie + audit log**

> 一句话：写死的"密码 = 一把万能钥匙"模式 → "用户名+密码登录 → 服务端签发临时通行证 → 每操作自动留痕"。

---

## 1. 背景 & 风险（v1.7.47 现状）

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
1. admin 鉴权从明文 token → **scrypt 密码 + 短期 session**
2. 每 session 操作自动落 **audit log**（who/what/when/where）
3. 浏览器侧提供完整 **登录/登出** UI（替代 `window.prompt()`）
4. 单点登录失败 → **5 次锁定 15 min**（防 brute force）
5. 紧急 kill_sessions 端点（防 token/cookie leak）

### ❌ 非目标（明确不做）
- 不引入第三方 OAuth/JWT（overkill）
- 不重写 `account_system.py` 整体（增量 patch）
- 不动 player-facing 侧的鉴权（user account 体系独立管理）
- 不动 `ensure_default_admin()` 的 token 兜底逻辑（保留为脚本/CLI fallback）
- **不保留老账户**（重新初始化，无迁移）

---

## 3. v1.1 修订（vs v1.0）

| 修订点 | v1.0 | v1.1 | 原因 |
|:---|:---|:---|:---|
| **密码算法** | bcrypt（命名）| scrypt（实际）| 统一命名 |
| **密码长度** | min 12 字符 + 4 类字符 | min 8 字符 + 不强制类型 | 内测阶段 NIST 推荐 |
| **双轨制** | v1.8+1.9（1+ 年）| v1.8.0 单轨（仅 1 季度）| 无老账户 |
| **kill_sessions 端点** | 缺 | 必加 | 紧急安全 |
| **CSRF e2e** | 缺 | 必加 | 跨域防护 |
| **audit rotation** | 简述 | 详细 spec | 防止丢日志 |
| **WBS 8（CLI）** | 必加 | **删除** | 重新初始化直接写 |
| **总工时** | 2.5h | **2h** | 简化 |

---

## 4. 架构

### 4.1 时序图（login → admin 操作 → logout）

```
┌────────┐         ┌──────────────┐         ┌──────────────┐
│ Browser│         │ Frontend (SPA)│         │ Backend      │
└───┬────┘         └──────┬───────┘         └──────┬───────┘
    │                     │                       │
    │  1. 点 admin 按钮    │                       │
    ├─────────────────────►│                       │
    │                     │  2. POST /admin/login  │
    │                     │  {account_id, password}│
    │                     ├──────────────────────►│
    │                     │                       │ 3. scrypt 验密
    │                     │                       │ 4. 查锁定状态
    │                     │                       │ 5. 创建 session
    │                     │                       │ 6. 写 audit
    │                     │  ◄───────────────────┤  Set-Cookie session_id=...
    │                     │  200 {account}        │ HttpOnly; SameSite=Lax
    │                     │                       │
    │  ◄──────────────────┤                       │
    │  显示 admin 面板      │                       │
    │                     │                       │
    │                     │  7. GET /admin/users  │
    │                     ├──────────────────────►│
    │                     │  Cookie: session_id   │
    │                     │                       │ 8. _check_session
    │                     │                       │ 9. sliding 续期
    │                     │  ◄───────────────────┤ 10. 写 audit
    │                     │  200 {users:[...]}    │
    │                     │                       │
    │  点 logout           │                       │
    ├─────────────────────►│                       │
    │                     │ 11. POST /admin/logout│
    │                     ├──────────────────────►│
    │                     │                       │ 12. 删 session
    │                     │  ◄───────────────────┤
    │  ◄──────────────────┤ 200                    │
    │  回登录表单          │                       │
```

### 4.2 数据流分层

| 层 | 组件 | 关键动作 |
|:---|:---|:---|
| **存** | `accounts.json` + **新增 `sessions.json`** + **新增 `audit.log`** | password_hash / session 表 / JSONL 日志 |
| **运** | `account_system.py` + **新增 `session_manager.py`** + **新增 `audit.py`** | scrypt + sliding session + audit append |
| **路** | `web_server/routers/admin.py` | login/logout + 10 handler 改 session |
| **前端** | `main.js` | 表单 + logout 按钮 + 失败计数 |
| **配** | `.env` | 移除 `ADMIN_TOKEN`，加 `SESSION_HMAC_SECRET` + `AUDIT_LOG_PATH` |

---

## 5. 数据 schema 变化

### 5.1 `accounts.json`（重新初始化）

```jsonc
{
  "accounts": [
    {
      "account_id": "00000000",
      "username": "admin",
      "role": "admin",
      "password_hash": "scrypt:32768:8:1$<salt-b64>$<hash-b64>",
      "password_set_at": "2026-07-07T10:00:00+08:00",
      "fail_count": 0,
      "lock_until": "",
      "invite_code_used": "INV-E3F0-W01K",
      "created_at": "2026-07-07T10:00:00+08:00",
      "bound_at": "2026-07-07T10:00:00+08:00",
      "last_login_at": ""
    }
  ]
}
```

### 5.2 `sessions.json`（全新文件）

```jsonc
{
  "sessions": [
    {
      "session_id": "8f3c2e1a4b5d6e7f9a0b1c2d3e4f5a6b",  // 32 hex (128-bit)
      "account_id": "00000000",
      "created_at": "2026-07-07T10:00:00+08:00",
      "last_active_at": "2026-07-07T10:00:00+08:00",
      "expires_at": "2026-07-08T10:00:00+08:00",        // 24h sliding
      "ip": "118.196.79.130",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) ..."
    }
  ]
}
```

### 5.3 `audit.log`（全新 JSONL，每行 1 条）

```jsonc
{"ts":"2026-07-07T10:00:00.123+08:00","event":"login_ok","session_id":"8f3c...","account_id":"00000000","ip":"...","user_agent":"..."}
{"ts":"2026-07-07T10:00:15.456+08:00","event":"action","session_id":"8f3c...","account_id":"00000000","route":"/api/admin/users","method":"GET","status":200,"latency_ms":12}
{"ts":"2026-07-07T10:05:00.789+08:00","event":"login_fail","ip":"...","reason":"bad_password","attempt":1,"account_id":"00000000"}
{"ts":"2026-07-07T10:05:01.234+08:00","event":"account_locked","account_id":"00000000","until":"2026-07-07T10:20:00+08:00"}
{"ts":"2026-07-07T11:00:00.000+08:00","event":"logout","session_id":"8f3c...","account_id":"00000000"}
```

事件类型：`login_ok` / `login_fail` / `account_locked` / `action` / `logout` / `session_expired` / `kill_sessions`

---

## 6. API 变化

### 6.1 新增（4 个端点）

| Method | Path | Body | 返回 | 说明 |
|:---|:---|:---|:---|:---|
| `POST` | `/api/admin/login` | `{account_id, password}` | `200 {account}` + Set-Cookie / `401/429` | scrypt 验密；5 次错锁 15min |
| `POST` | `/api/admin/logout` | (Cookie 必带) | `200` / `401` | 删 session + 清 cookie |
| `GET` | `/api/admin/whoami` | (Cookie) | `200 {account}` / `401` | 当前 session 信息 |
| `POST` | `/api/admin/kill_sessions` | `{admin_id, target_account_id?}` | `200 {killed: int}` | 紧急 kill（admin 自身或某用户）|

### 6.2 修改（10 个 handler）

| Method | Path | 变化 |
|:---|:---|:---|
| 10 个 `/api/admin/*` GET/POST | `_check_admin_token(headers)` → `_check_session(cookie)` |

**双轨制**：v1.8.0 期间 cookie 优先 + ADMIN_TOKEN header 回退（保 v1.7.47 脚本兼容）。**v1.8.1 移除 ADMIN_TOKEN 回退**。

### 6.3 失败锁定策略

```
连续失败 N=5 次 → 锁定 15 min
- 锁定状态存 account_system（不存 session）
- 锁定期间 admin/login 一律返回 429 Too Many Requests
- TTL 到期自动解除
```

---

## 7. 前端变化（`main.js`）

### 7.1 `adminAuthPrompt()` → `adminLoginForm()`（重写）

```javascript
async function adminLoginForm() {
  if (await hasValidSession()) return true;
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

### 7.2 logout 按钮（admin 面板 header 新增）

```html
<button onclick="adminLogout()">🚪 登出</button>
```

```javascript
async function adminLogout() {
  await api('/api/admin/logout', 'POST');
  location.reload();
}
```

### 7.3 失败计数显示

```
❌ 密码错误（剩余 3 次机会）  ← alert
❌ 账户已锁定 14 分 35 秒     ← alert
```

---

## 8. 关键设计要点

| 点 | 设计 |
|:---|:---|
| **密码算法** | `hashlib.scrypt`（Python 3.6+ stdlib，**零依赖**）|
| **密码长度** | min 8 字符（不强制字符类型）|
| **Cookie 属性** | `HttpOnly; SameSite=Lax; Path=/`（内测 HTTP 暂不强制 Secure）|
| **Session ID** | 32 hex（128 bit entropy）|
| **HMAC 签 cookie** | `session_id=<id>.<HMAC-SHA256>` 防 cookie 伪造 |
| **Session 续期** | 每次 admin 操作刷新 `last_active_at` + `expires_at`（sliding window）|
| **过期清理** | 服务启动时 + 每小时 cron 删过期 session |
| **失败锁定** | 5 次错密码锁定 15min（account-level，不是 session-level）|
| **Audit 字段** | ts + event + session_id + account_id + route + method + status + latency_ms + ip + user_agent |
| **Audit 存储** | JSONL append-only + `WatchedFileHandler` 自动 flush |
| **Audit rotation** | 每天 0:00 重命名 `audit.log` → `audit-YYYY-MM-DD.log.gz`，保留 30 天 |
| **回退兼容** | v1.8.0 双轨（cookie 优先 + ADMIN_TOKEN header 回退）|
| **会话清理** | 启动时删 expired；后台 thread 每小时跑一次 |
| **CSRF 防护** | `SameSite=Lax` 自动防；跨域 POST 拒绝（403）|

---

## 9. 实施 WBS（7 步 · 总 ~2h）

| # | 任务 | 文件 | 时间 | 验证 |
|:--|:---|:---|:---:|:---|
| **1** | Account: 加 `set_password` / `verify_password` (scrypt) + `lock_until` / `increment_fail` | `account_system.py` | 30m | `scripts/test_password.py` |
| **2** | `session_manager.py`（CRUD + 过期清理 + HMAC 签 cookie）| **新文件** | 25m | `scripts/test_session_manager.py` |
| **3** | `audit.py` 中间件 + 写 `audit.log` | **新文件** + `admin.py` | 20m | JSONL 校验 + 字段完整 |
| **4** | 路由 `/api/admin/login` + `/logout` + `/whoami` + `/kill_sessions` | `web_server/routers/admin.py` | 30m | curl 11 项 e2e |
| **5** | `_check_admin_token` → `_check_session`（10 handlers）| `admin.py` | 15m | 11 项 e2e（保 6 项老）|
| **6** | `main.js`: prompt → form + logout + failure lock UI | `main.js` | 20m | 浏览器 e2e (4 场景) |
| **7** | 重新初始化 + 11 项 e2e + 推送 | 5 文件 | 10m | git push + 浏览器 |

**注**：v1.0 WBS 8（CLI set_admin_password）删除。

---

## 10. 测试计划

### 10.1 单元测试（2 个新脚本）

| 脚本 | 用例 |
|:---|:---|
| `test_password.py` | set → verify roundtrip / 错密验 / salt 随机 / 时长合规 |
| `test_session_manager.py` | create / lookup / extend / expire / delete / cookie 签验 |

### 10.2 e2e（13 项：6 老 + 5 新登录 + 2 新 CSRF）

| # | 场景 | 期望 |
|:--|:---|:---|
| 老 1 | 无 token + 无 cookie | 401 |
| 老 2 | 正 ADMIN_TOKEN header（兼容） | 200 |
| 老 3 | 正 cookie | 200 |
| 老 4 | 错 token | 401 |
| 老 5 | 非 admin 账户 | 403 |
| 老 6 | 锁定期间 ADMIN_TOKEN | 200（header 不锁）|
| **新 1** | 错密码 5 次 | 第 6 次 429 + 锁定 |
| **新 2** | 锁定期间再 login | 429 + `retry_after` |
| **新 3** | 正确 login | 200 + Set-Cookie |
| **新 4** | 过期 session | 401 + 自动清理 |
| **新 5** | logout 后 cookie 失效 | 401 |
| **新 6** | kill_sessions 自身 | 200 {killed: 1} |
| **新 7** | 跨域 POST（Origin=evil.com）| 403 |

### 10.3 浏览器 e2e（4 场景）

| # | 场景 | 验证 |
|:--|:---|:---|
| B1 | admin 按钮 → 登录表单 | URL 不变，form 出现 |
| B2 | 错密码提示 | alert 文案 + 失败计数 |
| B3 | 正确登录 → 4 tab 加载 | token 自动失效 |
| B4 | logout → 回登录页 | cookie 清空 |

---

## 11. Rollout 计划

### 11.1 兼容性策略

- v1.8.0 **双轨制**（cookie 优先 + ADMIN_TOKEN header 回退）
- **v1.8.1 完全移除 ADMIN_TOKEN**（3 个月内）
- 老脚本（cron/feishu bot）：3 个月内迁到 cookie，否则需要永久 token fallback（**不推荐**）

### 11.2 灰度

| 阶段 | 范围 | 时间 |
|:---|:---|:---|
| Phase 0 | dev 机器本地测试完毕 | 0d |
| Phase 1 | 直接主站（admin 自己用） | 1d |
| Phase 2 | 全量 | 1d 后 |

### 11.3 回滚

| 触发 | 行动 |
|:---|:---|
| 5xx > 5% | `git revert <commit>` + 服务重启 |
| Login 401 风暴 | 临时切回 ADMIN_TOKEN 单鉴权（保留回退）|
| 数据损坏 | v1.7.47 commit `1b47647` 仍可签出 |

---

## 12. 安全 Checklist

- [ ] 不存明文密码，只存 scrypt hash
- [ ] Cookie `HttpOnly; SameSite=Lax; Path=/`
- [ ] Session ID 32 hex（128 bit entropy）
- [ ] HMAC 签 cookie 防篡改
- [ ] 密码 min 8 char（不强制字符类型）
- [ ] 失败 5 次锁 15min（account-level）
- [ ] Session 24h expiry + sliding 续期
- [ ] 服务启动 + 每小时 cron 删过期 session
- [ ] Audit log append-only + 每天 rotation + 保留 30 天
- [ ] 所有 admin 路由强制走 `_check_session`
- [ ] `IP` 字段从 `X-Forwarded-For` 头取
- [ ] Logout 真删 session（不只清 cookie）
- [ ] kill_sessions 端点可手动紧急 kill
- [ ] CSRF 跨域 POST 拒绝（403）
- [ ] 测试覆盖 13 项 e2e + 4 项浏览器

---

## 13. 未来演进（v1.9+ · 不在本工单）

| 需求 | 演进 |
|:---|:---|
| 多人 admin | RBAC：moderator + superadmin |
| 公网部署 | OAuth (GitHub/Google) + 强制 HTTPS |
| 高度敏感操作 | MFA：TOTP (RFC 6238) |
| 第三方审计 | audit.log → ELK / Loki |
| 邀请系统 | admin 创建 invite_code |

---

## 14. 下一步

| 选项 | 状态 |
|:---|:---|
| **A**（已同意）| 按 v1.1 实施 WBS 1-7（~2h）|

---

*文档结束 · v1.1 · 2026-07-07 09:30 CST · 钟离 🏛️*

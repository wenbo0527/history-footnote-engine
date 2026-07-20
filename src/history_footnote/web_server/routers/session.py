"""Session 管理路由：

POST /api/start               — 启动新游戏
GET  /api/archives            — 列出存档
POST /api/archive/delete      — 删除单个存档
POST /api/archives/clear      — 清空某 era 所有存档
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

from history_footnote.resource_cache import get_save_manager as get_save_manager_cached
from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.format_state import format_state
from history_footnote.web_server.views.session import new_session, session_pop


def handle_POST_start(handler, body) -> bool:
    era_id = body.get("era_id", "wanli1587")
    identity = body.get("identity", "weaving_male")
    gender = body.get("gender", "male")
    custom_character = body.get("character")
    # 🆕 v2.10.1 W75: 补全 LLM 需要的字段（personality / opening_paragraph / tics / starting_situation）
    # 之前前端只传 4 字段，LLM 收到的 custom_character 大量为空 → narrative 缺色彩
    if custom_character and isinstance(custom_character, dict):
        # 默认 personality 模板（按身份不同）
        DEFAULT_PERSONALITY_BY_IDENTITY = {
            "weaving_male":   "谨慎持家，顾念家人；手艺娴熟但不事张扬，习惯用沉默表达态度。",
            "weaving_female": "勤快持家，善待邻里；性子绵里带刚，遇大事能咬牙撑住。",
            "merchant_male":  "精于算计，嘴上活络；与人为善但账目分毫必争。",
            "merchant_female":"精明干练，能言善辩；邻里关系好但买卖场上不让步。",
        }
        default_p = DEFAULT_PERSONALITY_BY_IDENTITY.get(identity, "勤勉本分；与人为善，遇事三思而后行。")

        # 🆕 v2.10.6: 身份专属的"来历 + 剧情带入"模板
        # 解决：开局面板只有【开局处境】事实陈述，缺少氛围渲染
        # 方案：每个身份准备一段"【来历】"（角色背景）+ 一段"opening_paragraph"（剧情带入）
        # 用 f-string 拼 {name} / {hometown} / {occupation} / {family} 变量
        DEFAULT_BACKGROUND_BY_IDENTITY = {
            "weaving_male":   "盛泽镇织户人家出身，祖上三代靠织绸为生。家有两台旧织机，母亲早逝，父亲沈老三仍在；弟妹尚幼，束脩全靠你一双手。",
            "weaving_female": "盛泽镇织户人家出身，织机声里长大。公婆已逝，丈夫常年在外跑货，一双儿女靠你撑着作坊。",
            "merchant_male":  "盛泽镇行商出身，跟随父辈走南闯北，练就一副好嘴皮。账目记得清，行情摸得准，但近年生意难做，欠下几笔陈年旧账。",
            "merchant_female":"盛泽镇布行出身，自小在柜台后长大。买卖场上不让步，但邻里口碑好——镇上谁家织了好料子，第一个想到的就是你。",
        }
        DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY = {
            "weaving_male":   "万历十五年的正月，江南还是料峭春寒。盛泽镇河面上浮着一层薄冰，桑叶还没发芽，织工们已经陆续点亮了织机前的油灯。你推开作坊的门，冷气扑了满脸。两台旧织机蹲在昏暗的屋子里，像两头沉睡的牲口，等着你今天的第一梭。\n\n今早镇上的传言不少：苏州的织造局又下了新派银子的公文，王牙人在牙行门口骂骂咧咧，说今年的丝价要涨；隔壁张寡妇家昨夜哭了一宿——她男人去年欠下的赌债，债主终于找上了门。\n\n你握紧手里的梭子。新的一年就这么开始了。",
            "weaving_female": "万历十五年的正月，江南料峭春寒。盛泽镇的河水还凝着一层薄冰，桑田里光秃秃的，织机声却已经在屋里响起来——那是生活的节拍，比任何钟都准。\n\n你送走最后一担去年剩的绸，揣着换来的几百文铜钱往回走。街角王牙人正跟人嘀咕什么，见到你便笑着打了个招呼，眼里却有些说不清的意味。\n\n推开家门时，女儿在灶前烧火，儿子还在念书。日子苦，但还算安稳。新的一年，就这么来了。",
            "merchant_male":  "万历十五年正月，盛泽镇。你坐在自家布行的后堂，面前摊着一本账册，数字密密麻麻，看得人眼晕。\n\n去年苏州织造局的几笔尾款还没结清，丝价又涨了一成，开春的生意还没着落。伙计阿福端来一碗热茶，低声说外头有人找——是收旧账的。\n\n你放下茶碗，叹了口气。商人的年，从来不好过。",
            "merchant_female":"万历十五年正月，盛泽镇。你一边拨算盘一边听伙计报账，眉头微皱。\n\n去年赊出去的几笔账还没回，开春的丝价又涨了几分。苏州织造局的公文明明写着减税，可到下面又生出各种名目。邻座的钱老板拍拍你的肩——'老规矩，年关难过，开春更难。'\n\n你笑了笑，把账册合上。新的一年，就这么来了。",
        }

        # 🆕 v2.10.6: opening_paragraph 用格式化方式拼
        # 这样玩家名字/家乡/职业变化时 narrative 自动跟着变
        default_opening_tpl = DEFAULT_OPENING_PARAGRAPH_BY_IDENTITY.get(identity, "")
        default_background = DEFAULT_BACKGROUND_BY_IDENTITY.get(identity, "")

        # 拼 opening_paragraph（用 {name} {hometown} {occupation} 占位符）
        # 模板里 % 不会被解释（safe），用 str.format 安全
        try:
            if default_opening_tpl:
                custom_character.setdefault(
                    "opening_paragraph",
                    default_opening_tpl.format(
                        name=custom_character.get("name", "你"),
                        hometown=custom_character.get("hometown", "盛泽镇"),
                        occupation=custom_character.get("occupation", "织工"),
                    )
                )
            else:
                custom_character.setdefault("opening_paragraph", "")
        except (KeyError, IndexError):
            # 模板里出现未识别的占位符，兜底用模板原文
            custom_character.setdefault("opening_paragraph", default_opening_tpl)

        custom_character.setdefault("personality", default_p)
        custom_character.setdefault("tics", "说话时常用'嗯''这个'起头；笑时眼睛眯成一条缝。")
        custom_character.setdefault("starting_situation", f"今早推开家门，{custom_character.get('occupation', '做工')}的活计照旧，但心里总有些不安。")
        custom_character.setdefault("background", default_background)
        custom_character.setdefault("voices", [])
        custom_character.setdefault("skills", [])
        custom_character.setdefault("family", {})
    # 🆕 v1.7.30: 接 account_id（账户隔离）
    # 🆕 v2.7+: 优先从 cookie 拿（持久化），body 兜底
    account_id = body.get("account_id", "") or ""
    if not account_id:
        try:
            account_id = handler._get_guest_id_from_cookie_or_query() or ""
        except Exception:
            pass
    game = new_session(era_id, identity, gender, custom_character=custom_character)
    # 把 account_id 绑定到 game.state（供 save 时持久化）
    if account_id and hasattr(game, 'state'):
        try:
            game.state.account_id = account_id
        except Exception:
            pass

    # 🆕 v2.5: 全局随机种子（replay 机制）
    # 玩家可传 seed 用同一 seed 重玩（分享 / debug / 重玩）
    # 不传则系统生成随机 seed
    from history_footnote.random_utils import (
        set_session_seed, generate_random_seed, make_seed_from_string,
    )
    sid = getattr(game, "session_id", None)
    requested_seed = body.get("seed")
    seed_str = body.get("seed_str")  # 例: "wanli-love-story"
    if requested_seed is not None and isinstance(requested_seed, int):
        actual_seed = requested_seed & 0xFFFFFFFF
    elif seed_str and isinstance(seed_str, str):
        actual_seed = make_seed_from_string(seed_str)
    else:
        actual_seed = generate_random_seed()
    if sid:
        set_session_seed(sid, actual_seed)
        if hasattr(game.state, 'seed'):
            game.state.seed = actual_seed
        logger.info(f"[v2.5] session {sid[:8]} seed={actual_seed}")

    # 🆕 v2.5: 命运卡抽 5 张 + 立即应用开局效果
    from history_footnote.fate_cards import draw_fate_cards, apply_fate_card
    try:
        fate_cards = draw_fate_cards(sid, n=5)
        # 把卡转为 dict 存到 state
        game.state.fate_hand = [
            {
                "id": c.id, "name": c.name, "icon": c.icon, "color": c.color,
                "description": c.description, "effect_type": c.effect_type,
                "effect_params": c.effect_params, "used": False,
                # 🆕 v2.6 主动使用字段
                "use_type": c.use_type,
                "use_constraints": c.use_constraints,
                "use_hint": c.use_hint,
            }
            for c in fate_cards
        ]
        logger.info(f"[v2.5] 抽命运卡 5 张: {[c.id for c in fate_cards]}")
    except Exception as e:
        logger.exception(f"[v2.5] 命运卡抽取失败: {e}")
        game.state.fate_hand = []
    # 捕获开场白到 narrative_history
    buf = io.StringIO()
    with redirect_stdout(buf):
        game._print_opening()
    opening_text = buf.getvalue().strip()
    if opening_text:
        # 🆕 v2.10.4-patch3: 明确标记 round 0 是 opening（之前 type 字段为 null，靠前端 fallback）
        game.state.append_narrative(0, opening_text, "开场", narrative_type="opening")
        # 🆕 v2.7.2：开场也提取 fact，让第 1 回合能接上文
        try:
            from history_footnote.narrative_facts_extractor import extract_facts_from_narrative
            llm_wrapper = getattr(game, "dm", None)
            if llm_wrapper and hasattr(llm_wrapper, "llm"):
                llm_wrapper = llm_wrapper.llm
            opening_facts = extract_facts_from_narrative(
                narrative=opening_text,
                round_num=0,
                llm_wrapper=llm_wrapper,
                timeout=8.0,
            )
            if opening_facts:
                game.state.append_facts([f.to_dict() for f in opening_facts])
                logger.info(
                    f"[v2.7.2] 开场提取 {len(opening_facts)} 条 fact"
                )
        except Exception as e:
            logger.warning(f"[v2.7.2] 开场 fact 提取失败: {e}")
    # 🆕 v1.7.22: start 时不注入 freetext 占位
    state = format_state(game)
    state.pop("last_voice_options", None)
    # 🆕 v2.10.5: 开局 voice_options 异步生成
    # 之前：_context_aware_voices 同步阻塞 2-6s（LLM 调用）
    # 改造：立即返回空 list + 标记 "voice_options_pending=True"
    #      后台线程生成后注入 game.state.last_voice_options
    #      前端通过 SSE /api/voice/stream 或 GET /api/state 轮询获取
    # 总用户感知延迟：5-15s → 1-2s
    state["last_voice_options"] = []
    state["voice_options_pending"] = True  # 新增字段，前端可读
    game.state.last_voice_options = []

    if opening_text:
        # 🆕 v2.10.5: 用线程池异步生成 voice_options
        # 不阻塞 POST /start 响应
        import threading
        def _async_generate_voices():
            try:
                from history_footnote.web_server.routers.input import _context_aware_voices
                logger.info(f"[start] async voice_options 线程启动 (sid={game.session.session_id[:8]}...)")
                voices = _context_aware_voices(opening_text, game=game)
                if voices:
                    game.state.last_voice_options = list(voices)
                    logger.info(
                        f"[start] async voice_options 完成 ({len(voices)} 个)"
                    )
                # 标记 pending=False
                game.state.voice_options_pending = False
            except Exception as e:
                logger.exception(f"[start] async voice_options 失败: {e}")
                game.state.voice_options_pending = False

        threading.Thread(
            target=_async_generate_voices,
            daemon=True,
            name=f"voices-{game.session.session_id[:8]}",
        ).start()

        # 🆕 v2.10.5: 第 1 章蓝图预生成（让玩家首次输入不阻塞）
        # 之前：chapter_state.active=False, current_chapter=0（开局阶段）
        #      玩家首次输入 → _run_round → pre_step → advance_to_chapter(1)
        #      → 章节蓝图生成（LLM 3-10s）→ 玩家等待
        # 改造：start 阶段后台预生成 chapter 1，玩家首次输入直接进入 chapter
        # 总用户感知延迟：3-10s 减少
        def _async_prepare_chapter():
            try:
                logger.info(f"[start] async chapter 1 蓝图预生成启动 (sid={game.session.session_id[:8]}...)")
                coord = getattr(game, "_chapter_coordinator", None)
                if coord is not None:
                    # 🆕 v2.10.11+：实际 ChapterCoordinator 方法是 _init_first_chapter / pre_step
                    if hasattr(coord, "_init_first_chapter"):
                        coord._init_first_chapter()
                    else:
                        coord.pre_step()
                    logger.info(
                        f"[start] async chapter 1 预生成完成 "
                        f"(current_chapter={game.state.chapter_state.current_chapter})"
                    )
                else:
                    # v2.10.5 兜底：老 game_loop 没 _chapter_coordinator 时静默
                    logger.debug(f"[start] game 无 _chapter_coordinator，跳过 chapter 预生成")
            except Exception as e:
                # 不致命：玩家首次输入会再次尝试 advance
                logger.warning(f"[start] async chapter 1 预生成失败（fallback 到 lazy 初始化）: {e}")

        threading.Thread(
            target=_async_prepare_chapter,
            daemon=True,
            name=f"chapter-{game.session.session_id[:8]}",
        ).start()

    # 🆕 v2.7: session 创建后立即存档（保证命运卡等持久化）
    # 之前：玩家调 /api/start → 抽卡 + 叙事，但 state 没保存到磁盘
    # 后果：服务器重启后，state.fate_hand 等丢失（meta.json 只存元数据）
    try:
        from history_footnote.resource_cache import get_save_manager as get_save_manager_cached
        sm = get_save_manager_cached()
        state_data = game.state.to_dict()
        # 🆕 把 v2.5 字段显式写进 state_data（不依赖 to_dict 自动）
        state_data["fate_hand"] = list(getattr(game.state, "fate_hand", []) or [])
        state_data["fate_used"] = list(getattr(game.state, "fate_used", []) or [])
        state_data["fate_event_flags"] = list(getattr(game.state, "fate_event_flags", []) or [])
        state_data["npc_relations"] = dict(getattr(game.state, "npc_relations", {}) or {})
        state_data["active_buffs"] = list(getattr(game.state, "active_buffs", []) or [])
        state_data["seed"] = int(getattr(game.state, "seed", 0) or 0)
        sm.save_state(game.session, "auto", state_data, summary="新游戏")
        logger.info(f"[v2.7] session 创建后立即存档: {game.session.session_id[:8]}")
    except Exception as e:
        logger.exception(f"[v2.7] session 创建后存档失败: {e}")

    handler._json(200, {
        "session_id": game.session.session_id,
        "seed": getattr(game.state, "seed", 0),  # 🆕 v2.5: 返回 seed（玩家可重玩）
        "fate_hand": getattr(game.state, "fate_hand", []),  # 🆕 v2.5: 命运卡手牌
        **state,
    })
    return True


def handle_GET_archives(handler, query) -> bool:
    from urllib.parse import parse_qs
    qs = parse_qs(query)
    era_id = qs.get("era_id", [None])[0]
    # 🆕 v1.7.30: 接 account 过滤
    account = qs.get("account", [None])[0]
    # 🆕 v2.7+: include_archived=1 显示冷存档（管理员面板用）
    include_archived = qs.get("include_archived", ["0"])[0] in ("1", "true", "yes")
    try:
        save_manager = get_save_manager_cached()
        sessions = save_manager.list_sessions(
            era_id=era_id,
            account_id=account,
            include_archived=include_archived,
        )
        out = []
        for s in sessions[:20]:  # 增加 limit 到 20
            out.append({
                "session_id": s.session_id,
                "era_id": s.era_id,
                "current_round": getattr(s, "current_round", 0),
                "current_date": getattr(s, "current_date", ""),
                "summary": getattr(s, "summary", ""),
                "created_at": getattr(s, "created_at", ""),
                "last_saved_at": getattr(s, "last_saved_at", ""),
                "selected_identity": getattr(s, "selected_identity", ""),
                "player_gender": getattr(s, "player_gender", ""),
                "account_id": getattr(s, "account_id", ""),
                # 🆕 v2.7+ 冷存档标记
                "archived": getattr(s, "archived", False),
                "archived_at": getattr(s, "archived_at", ""),
            })
        # 🆕 v2.10.7: 返 sessions 字段（之前 archives 字段）
        # 前端 StartMenu.svelte:64 archives = response.sessions
        # 之前后端返 archives，前端拿 sessions → undefined.length 报错
        handler._json(200, {"sessions": out, "archives": out, "count": len(out)})
    except Exception as e:
        logger.exception("[/api/archives] 失败: %s", e)
        handler._json(500, {"error": f"列出存档失败: {e}", "sessions": [], "archives": []})
    return True


def handle_POST_archive_delete(handler, body) -> bool:
    sid = body.get("session_id", "").strip()
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True
    try:
        save_manager = get_save_manager_cached()
        if "/" in sid or "\\" in sid or ".." in sid:
            handler._json(400, {"error": "invalid session_id"})
            return True
        if not save_manager.find_session(sid):
            handler._json(404, {"error": "session not found", "session_id": sid})
            return True
        ok = save_manager.delete_session(sid)
        if ok:
            session_pop(sid)
            logger.info(f"[/api/archive/delete] Deleted archive: {sid}")
            handler._json(200, {"ok": True, "session_id": sid, "deleted": True})
        else:
            handler._json(500, {"error": "delete failed", "session_id": sid})
    except Exception as e:
        logger.exception(f"[/api/archive/delete] 失败: {e}")
        handler._json(500, {"error": f"delete failed: {e}"})
    return True


def handle_POST_archives_clear(handler, body) -> bool:
    era_id = body.get("era_id", "").strip()
    confirm = body.get("confirm", False)
    if not era_id:
        handler._json(400, {"error": "missing era_id"})
        return True
    if not confirm:
        handler._json(400, {"error": "需要 confirm=true 二次确认"})
        return True
    try:
        save_manager = get_save_manager_cached()
        sessions = save_manager.list_sessions(era_id=era_id)
        if not sessions:
            handler._json(200, {"ok": True, "deleted_count": 0, "deleted_ids": []})
            return True
        deleted_ids, failed = [], []
        for s in sessions:
            sid = s.session_id
            if "/" in sid or "\\" in sid or ".." in sid:
                failed.append(sid)
                continue
            if save_manager.delete_session(sid):
                deleted_ids.append(sid)
                session_pop(sid)
            else:
                failed.append(sid)
        logger.info(f"[/api/archives/clear] Cleared {len(deleted_ids)} archives for era {era_id}")
        handler._json(200, {
            "ok": True,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "failed": failed,
        })
    except Exception as e:
        logger.exception(f"[/api/archives/clear] 失败: {e}")
        handler._json(500, {"error": f"clear failed: {e}"})
    return True

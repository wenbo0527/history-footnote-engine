"""🆕 v2.10.13+: Anachronism（时代错位）检测器

目的：检测 LLM 在 narrative 中是否输出现代经商思路（明万历 + 江南丝绸业场景不合史实）。

设计原则：
- 两层分类：HARD（绝对违规） vs SOFT（需要 narrative 上下文澄清）
- warning + log — 不阻塞叙事，让玩家玩，但 dev/QA 能看到
- 概念级（concept-level）匹配 — 不只看单字，看"语义组合"

历史背景（明万历 / 1587-1601 / 江南丝绸业）：
- **流通**：现银 + 牙行（broker）+ 期票（飞钱）+ 会票；**没有**：
  - 银行（钱庄在清中后期才普及）
  - 纸币/银票（明代主流是真金白银）
  - 期货/对冲（19 世纪末）
- **组织**：家庭作坊 + 牙行（broker）+ 行会（最早形态）；**没有**：
  - 公司/股份公司（1557 年才有"合本"形态，但 1587 江南丝绸未普及）
  - 商标/品牌（"字号"有，但"品牌营销"是 20 世纪概念）
  - 股票/IPO（19 世纪）
- **会计**：流水账 + 牙行记账 + 私人账房；**没有**：
  - 复式记账（1494 年传入，1587 江南小作坊未用）
  - 现金流分析 / KPI
  - 现代审计
- **金融**：高利贷（按月 3%+）+ 私人拆借；**没有**：
  - 信用卡
  - 现代银行借贷（贷款用途用抵押，利率用基准利率）
  - 金融衍生品
- **生产**：手工缫丝 + 木织机 + 脚踏提花机；**没有**：
  - 飞梭（1733 年）/ 珍妮纺纱机（1764 年）
  - 工厂流水线
- **市场营销**：口碑 + 牙行引荐 + 集市；**没有**：
  - 广告投放 / "品牌定位" / 营销 4P
  - 数字化营销

注意：本器**只报告**，不阻断，目的是让 dev 在叙事中清理掉不合史实的概念，
避免对历史爱好者玩家产生违和感。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AnachronismLevel(str, Enum):
    """时代错位严重程度"""
    HARD = "hard"           # 绝对违规 — 明万历 + 江南丝绸不可能有
    SOFT = "soft"           # 概念存在但 narrative 没明确史实基础
    UNCLEAR = "unclear"     # narrative 没澄清（玩家输入可能合理）


@dataclass
class AnachronismHit:
    """单个时代错位命中点"""
    level: str           # hard | soft | unclear
    concept: str         # 概念名 (e.g., "期货")
    matched_term: str    # 匹配到的具体词
    snippet: str         # 上下文（前 50 字 + 命中 + 后 50 字）
    explanation: str     # 为什么这不合史实


@dataclass
class AnachronismReport:
    """完整 anachronism 检测报告"""
    hits: list[AnachronismHit] = field(default_factory=list)
    hard_count: int = 0
    soft_count: int = 0
    unclear_count: int = 0

    @property
    def has_issues(self) -> bool:
        return len(self.hits) > 0

    @property
    def worst_level(self) -> str:
        if self.hard_count > 0:
            return AnachronismLevel.HARD.value
        if self.soft_count > 0:
            return AnachronismLevel.SOFT.value
        if self.unclear_count > 0:
            return AnachronismLevel.UNCLEAR.value
        return "clean"

    def summary(self) -> str:
        if not self.has_issues:
            return "✅ narrative 通过时代错位检测（明万历 / 江南丝绸）"
        parts = []
        if self.hard_count:
            parts.append(f"{self.hard_count} 处 HARD")
        if self.soft_count:
            parts.append(f"{self.soft_count} 处 SOFT")
        if self.unclear_count:
            parts.append(f"{self.unclear_count} 处 UNCLEAR")
        return f"⚠️ narrative 含 {' + '.join(parts)} 时代错位概念"


# ============================================================
# 概念库（concept-level — 比 keyword 匹配更可靠）
# ============================================================

# HARD 概念：1587 + 江南丝绸业绝对不存在
HARD_CONCEPTS: dict[str, dict[str, Any]] = {
    "期货 / 合约交易": {
        "pattern": r"(期货|合约交易|对冲|做空|做多|保证金交易|杠杆交易|期指|期权)",
        "reason": (
            "明万历仅有零星'射利'约定（口头/契约），无标准期货合约。"
            "期货市场在 19 世纪美国/日本兴起，1949 年中国现代期货才起步。"
        ),
        "first_introduced": "1848 (CBOT)",
    },
    "股份公司 / 上市公司": {
        "pattern": r"(股份公司|上市公司|股东会|ipo|首次公开募股|股票发行|股权融资|股份融资)",
        "reason": (
            "明万历有'合本'形态（如盐商），但'股份公司'是 1552-1602 荷兰东印度公司"
            "初步形成的西方概念，江南丝绸业 1587 仍以家庭作坊 + 合伙（不超过 2-3 户）为主。"
        ),
        "first_introduced": "1552 (VOC)",
    },
    "银行 / 现代金融": {
        "pattern": r"(银行存贷|现代银行|抵押贷款|质押贷款|基准利率|央行|中央银行|准备金率)",
        "reason": (
            "钱庄在清中后期（约 19 世纪）才普及。明万历仅有'银号/钱铺'做换汇 +"
            "小额贷款，高利贷为主，无'基准利率'概念。"
        ),
        "first_introduced": "1694 (BoE)",
    },
    "信用卡 / 电子支付": {
        "pattern": r"(信用卡|借记卡|电子支付|移动支付|扫码支付|支付宝|微信支付)",
        "reason": "20 世纪后期概念，明万历绝对不存在",
        "first_introduced": "1950 (Diners Club)",
    },
    "品牌营销 / 4P": {
        "pattern": r"(品牌定位|品牌营销|市场营销策略|4p营销|4c营销|市场调研|marketing)",
        "reason": (
            "'字号'在明代有（同仁堂 1669 年创立可上溯），但'品牌战略/营销 4P'"
            "是 1960 年 Jerome McCarthy 提出。"
        ),
        "first_introduced": "1960",
    },
    "工业机械化纺织": {
        "pattern": r"(飞梭|珍妮纺纱机|水力纺纱|蒸汽机纺织|机器织机)",
        "reason": (
            "明万历江南丝绸全靠手工缫丝 + 木织机 + 脚踏提花机。"
            "飞梭 1733 年才有；珍妮纺纱机 1764 年；水力纺纱 1769 年。"
        ),
        "first_introduced": "1733 (Flying Shuttle)",
    },
    "现代审计 / 复式记账": {
        "pattern": r"(复式记账|借贷记账|资产负债表|现金流量表|审计报告|kpi|okr)",
        "reason": (
            "复式记账 1494 年（Pacioli）总结，但 1587 江南小作坊用流水账。"
            "现代审计/财务报表/数字化 KPI 是 19-20 世纪西方概念。"
        ),
        "first_introduced": "1494 (Theory but not practiced)",
    },
    "现代数理统计 / 商业建模": {
        "pattern": r"(大数据分析|商业模式画布|商业模型|crm系统|erp系统|sap|oracle)",
        "reason": "20 世纪后期 IT 概念，明万历无任何此类工具",
        "first_introduced": "1980s",
    },
}

# SOFT 概念：概念存在但 narrative 该澄清史实基础
SOFT_CONCEPTS: dict[str, dict[str, Any]] = {
    "会计学概念": {
        "pattern": r"(复利|单利|利率|年利率|月息|本金|利息|账期)",
        "reason": (
            "明万历贷款常用'月息几分'（如 月息 3 分 = 月利率 3%）。"
            "若 narrative 说'年利率 8%'等需澄清换算。"
        ),
    },
    "现代借贷术语": {
        "pattern": r"(信用贷款|无抵押贷款|小额贷款|消费金融)",
        "reason": "明万历民间借贷以'质押/抵押/私人拆借'为主，无'无抵押贷款'概念",
    },
    "税务术语现代": {
        "pattern": r"(个人所得税|增值税|税务筹划|避税)",
        "reason": (
            "明万历有'丁银 / 丝绢税 / 桑园税'。'税务筹划/避税'是现代概念。"
            "narrative 若提到这些需转换成明万历的税务结构。"
        ),
    },
    "保险/期货早期": {
        "pattern": r"(保险|海运保险|共同海损)",
        "reason": (
            "'镖局'有（保险前形态），但现代'海运保险/共同海损'是 14 世纪地中海"
            "起源，到 17 世纪 Lloyd's (1688) 才成型。明万历江南丝绸走京杭运河，"
            "镖局护送，不会有'海运保险'。"
        ),
    },
}

# UNCLEAR：narrative 没澄清（玩家输入可能合理）
UNCLEAR_CONCEPTS: dict[str, dict[str, Any]] = {
    "期货型约定": {
        "pattern": r"(预定|预订|定金|订金)",
        "reason": (
            "明万历有'先给定银'（定金）的习俗，但 narrative 没澄清是否现代"
            "意义的'预定合约'。建议：narrative 显式说'今日给定银 X 两，"
            "约定 Y 月织 X 匹'。"
        ),
    },
    "股份/合伙": {
        "pattern": r"(合股|合伙|按股|分账)",
        "reason": (
            "明万历有'合本'和'合伙'形态（盐商常见），但 narrative 没澄清是"
            "现代'股份公司'还是'明合伙'。"
        ),
    },
    "现代官府/税务机构": {
        "pattern": r"(税务局|工商局|市场监督)",
        "reason": "明万历对应的是'府衙/县衙/里甲/织造局'，'现代工商局'是错的",
    },
    "工业技术 / 通信": {
        "pattern": r"(电报|电话|铁路|工厂流水线)",
        "reason": "明万历无电报（1837）/ 电话（1876）/ 铁路（19 世纪）",
    },
    "现代人物身份": {
        "pattern": r"(资本家|企业家|上市公司老板)",
        "reason": (
            "明万历用'机户/坐贾/行商/盐商/徽商'等术语。'资本家/企业家'"
            "是 19-20 世纪西方概念。"
        ),
    },
}


# ============================================================
# Detector
# ============================================================

def _make_snippet(text: str, match: re.Match, before: int = 30, after: int = 30) -> str:
    """截取含命中的上下文片段"""
    start = max(0, match.start() - before)
    end = min(len(text), match.end() + after)
    return text[start:end].replace("\n", " ").strip()


def _scan_concepts(text: str, concepts: dict[str, dict[str, Any]]) -> list[AnachronismHit]:
    """对一组概念做 regex scan"""
    hits: list[AnachronismHit] = []
    for concept_name, c in concepts.items():
        pattern = c.get("pattern")
        reason = c.get("reason", "")
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append(AnachronismHit(
                level="",
                concept=concept_name,
                matched_term=m.group(),
                snippet=_make_snippet(text, m),
                explanation=reason,
            ))
    return hits


def detect_anachronisms(text: str) -> AnachronismReport:
    """检测 narrative 中的时代错位概念

    Args:
        text: 整篇 narrative 文本
    Returns:
        AnachronismReport 含所有命中点 + 数量统计
    """
    if not text:
        return AnachronismReport()

    report = AnachronismReport()

    # HARD
    hard_hits = _scan_concepts(text, HARD_CONCEPTS)
    for h in hard_hits:
        h.level = AnachronismLevel.HARD.value
    report.hits.extend(hard_hits)
    report.hard_count = len(hard_hits)

    # SOFT
    soft_hits = _scan_concepts(text, SOFT_CONCEPTS)
    for h in soft_hits:
        h.level = AnachronismLevel.SOFT.value
    report.hits.extend(soft_hits)
    report.soft_count = len(soft_hits)

    # UNCLEAR
    unclear_hits = _scan_concepts(text, UNCLEAR_CONCEPTS)
    for h in unclear_hits:
        h.level = AnachronismLevel.UNCLEAR.value
    report.hits.extend(unclear_hits)
    report.unclear_count = len(unclear_hits)

    return report


def log_report(report: AnachronismReport, session_id: str = "", round_number: int | None = None) -> None:
    """把检测报告写进 log（WARNING 级别，但不阻断）

    Args:
        report: AnachronismReport
        session_id: 用于 log 上下文
        round_number: 用于 log 上下文
    """
    if not report.has_issues:
        return
    ctx = f"session={session_id} R{round_number}" if round_number is not None else f"session={session_id}"
    logger.warning(
        f"[anachronism:{ctx}] {report.summary()}\n"
        + "\n".join(
            f"  [{h.level.upper():7}] {h.concept} | '{h.matched_term}' "
            f"in: {h.snippet[:80]!r}"
            for h in report.hits
        )
    )


# ============================================================
# Module exports
# ============================================================

__all__ = [
    "AnachronismLevel",
    "AnachronismHit",
    "AnachronismReport",
    "detect_anachronisms",
    "log_report",
    "HARD_CONCEPTS",
    "SOFT_CONCEPTS",
    "UNCLEAR_CONCEPTS",
]

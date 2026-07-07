"""🆕 v1.8.3 generateCharacter 加重试/超时/分类错误 静态测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src/history_footnote/web/static/js/main.js"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_retry_mechanism():
    print("[1/6] 重试机制")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  MAX_ATTEMPTS = 3", "MAX_ATTEMPTS = 3" in src) and ok
    ok = _step("  while 循环重试", "while (attempt < MAX_ATTEMPTS)" in src) and ok
    ok = _step("  退避数组 BACKOFF_MS", "BACKOFF_MS" in src) and ok
    ok = _step("  4xx 不重试（break）", "resp.status >= 400 && resp.status < 500" in src and "break;" in src) and ok
    return ok


def test_timeout():
    print("\n[2/6] 超时控制")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  TIMEOUT_MS = 30000", "TIMEOUT_MS = 30000" in src) and ok
    ok = _step("  AbortController 使用", "new AbortController()" in src) and ok
    ok = _step("  signal: controller.signal", "signal: controller.signal" in src) and ok
    ok = _step("  AbortError 分类为 timeout", "e.name === \"AbortError\"" in src and "type: \"timeout\"" in src) and ok
    return ok


def test_error_classification():
    print("\n[3/6] 错误类型分类")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function classifyError 存在", "function classifyError" in src) and ok
    ok = _step("  429 → rate_limit", "status === 429" in src and "rate_limit" in src) and ok
    ok = _step("  503 → service_unavailable", "status === 503" in src and "service_unavailable" in src) and ok
    ok = _step("  5xx → server_error", "status >= 500" in src and "server_error" in src) and ok
    ok = _step("  其他 → client_error", "client_error" in src) and ok
    return ok


def test_error_ui():
    print("\n[4/6] 错误 UI")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  function renderCharacterError 存在", "function renderCharacterError" in src) and ok
    ok = _step("  显示已重试次数", "已重试 ${attempts} 次" in src) and ok
    ok = _step("  6 种类型 label", all(t in src for t in ["timeout:", "network:", "rate_limit:", "service_unavailable:", "server_error:", "client_error:"])) and ok
    ok = _step("  重新生成按钮", "onclick=\"generateCharacter()\"" in src and "重新生成" in src) and ok
    ok = _step("  修改身份按钮", "修改身份" in src) and ok
    ok = _step("  返回菜单按钮", "renderMenu" in src) and ok
    return ok


def test_user_friendly():
    print("\n[5/6] 用户友好")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  重试提示 toast", "第 ${attempt}/${MAX_ATTEMPTS} 次重试" in src) and ok
    ok = _step("  成功 toast", "✅ 第 ${attempt} 次重试成功" in src) and ok
    ok = _step("  失败 toast", "❌ 人设生成失败" in src) and ok
    ok = _step("  触觉成功反馈", "HAPTIC.success()" in src) and ok
    ok = _step("  触觉错误反馈", "HAPTIC.error()" in src) and ok
    return ok


def test_backward_compat():
    print("\n[6/6] 向后兼容")
    src = MAIN.read_text(encoding="utf-8")
    ok = True
    ok = _step("  generateCharacter 仍 async function", "async function generateCharacter" in src) and ok
    ok = _step("  防重入 _generating_character 仍在", "wizard._generating_character" in src) and ok
    ok = _step("  renderWizardStep 仍调 generateCharacter", "renderWizardStep(7)" in src or "generateCharacter" in src) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.8.3 generateCharacter 加重试/超时 静态测试 ===\n")
    ok1 = test_retry_mechanism()
    ok2 = test_timeout()
    ok3 = test_error_classification()
    ok4 = test_error_ui()
    ok5 = test_user_friendly()
    ok6 = test_backward_compat()
    if all([ok1, ok2, ok3, ok4, ok5, ok6]):
        print("\n🎉 6 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=}")
        sys.exit(1)

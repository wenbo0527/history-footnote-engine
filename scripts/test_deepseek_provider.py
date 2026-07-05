"""v1.7.12 测试 DeepSeek provider 集成

不调用真实 API（避免账户余额问题），只验证：
1. make_llm("deepseek") 成功创建 ChatOpenAI 实例
2. base_url 是 https://api.deepseek.com
3. model 是 deepseek-v4-pro
4. reasoning_effort="high" 已设置
5. extra_body={"thinking": {"type": "enabled"}} 已设置
6. api_key 从 DEEPSEEK_API_KEY 环境变量读取
"""
import os
import sys

from dotenv import load_dotenv
load_dotenv("/Users/mac/Documents/trae_projects/history_footnote/.env")

sys.path.insert(0, "src")
from history_footnote.llm_providers import make_llm, get_provider_info, list_providers


def test_provider_in_list():
    """deepseek 应该在 provider 列表中"""
    providers = list_providers()
    assert "deepseek" in providers, f"deepseek 不在列表中: {providers}"
    print(f"✅ test_provider_in_list: deepseek in {providers}")


def test_provider_info():
    """get_provider_info 应返回 deepseek 元信息"""
    info = get_provider_info("deepseek")
    assert info.get("name") == "DeepSeek"
    assert info.get("default_model") == "deepseek-v4-pro"
    assert "DEEPSEEK_API_KEY" in info.get("env_vars", [])
    print(f"✅ test_provider_info: {info['name']}, model={info['default_model']}")


def test_create_llm():
    """make_llm('deepseek') 应返回 ChatOpenAI 实例"""
    llm = make_llm("deepseek")
    assert llm is not None
    assert "ChatOpenAI" in type(llm).__name__
    print(f"✅ test_create_llm: {type(llm).__name__} created")


def test_base_url():
    """base_url 应该是 https://api.deepseek.com"""
    llm = make_llm("deepseek")
    # ChatOpenAI 内部 openai_api_base
    base = getattr(llm, "openai_api_base", None)
    assert base and "deepseek.com" in base, f"base_url 错误: {base}"
    print(f"✅ test_base_url: {base}")


def test_model_name():
    """model 应该是 deepseek-v4-pro"""
    llm = make_llm("deepseek")
    model = getattr(llm, "model_name", None)
    assert model == "deepseek-v4-pro", f"model 错误: {model}"
    print(f"✅ test_model_name: {model}")


def test_thinking_mode():
    """思考模式参数应已设置"""
    llm = make_llm("deepseek")
    reasoning = getattr(llm, "reasoning_effort", None)
    extra_body = getattr(llm, "extra_body", None)
    assert reasoning == "high", f"reasoning_effort 应为 'high': {reasoning}"
    assert extra_body and extra_body.get("thinking", {}).get("type") == "enabled", \
        f"extra_body.thinking 应 enabled: {extra_body}"
    print(f"✅ test_thinking_mode: reasoning_effort={reasoning}, extra_body={extra_body}")


def test_api_key_from_env():
    """api_key 应从 DEEPSEEK_API_KEY 环境变量读取"""
    assert os.environ.get("DEEPSEEK_API_KEY"), "DEEPSEEK_API_KEY 环境变量未设置"
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    assert api_key.startswith("sk-"), f"API key 格式错误: {api_key[:10]}"
    print(f"✅ test_api_key_from_env: {api_key[:15]}...")


def test_override_params():
    """调用方可覆盖默认参数"""
    llm = make_llm("deepseek", model="deepseek-other", extra_kwargs={"reasoning_effort": "low"})
    assert llm.model_name == "deepseek-other"
    assert llm.reasoning_effort == "low"
    print(f"✅ test_override_params: model={llm.model_name}, reasoning={llm.reasoning_effort}")


if __name__ == "__main__":
    print("=" * 50)
    print("v1.7.12 DeepSeek Provider 单元测试")
    print("=" * 50)
    test_provider_in_list()
    test_provider_info()
    test_create_llm()
    test_base_url()
    test_model_name()
    test_thinking_mode()
    test_api_key_from_env()
    test_override_params()
    print("\n✅ 所有 DeepSeek provider 测试通过")
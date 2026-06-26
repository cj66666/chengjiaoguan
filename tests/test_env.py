"""
/* ========================================================================== */
/* GEB L3: 本地环境加载测试                                                   */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 pathlib/tmp_path、pytest monkeypatch 与 app.env
 * [OUTPUT]: 验证 .env.local/.env 加载、已有环境保护与 CLOSER_SKIP_DOTENV 开关
 * [POS]: tests 的启动配置证明文件，防止本地 provider 接线回退成手动临时环境变量
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

import os

from app.env import load_local_env


def test_load_local_env_reads_env_local_without_overriding_existing_values(tmp_path, monkeypatch):
    monkeypatch.delenv("CLOSER_SKIP_DOTENV", raising=False)
    monkeypatch.setenv("EXISTING_KEY", "from-env")
    (tmp_path / ".env.local").write_text(
        "\n".join(
            [
                "CLOSER_AGENT_MODEL=openai-chat:MiniMax-M3",
                "QUOTED_VALUE=\"hello world\"",
                "EXISTING_KEY=from-file",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_local_env(tmp_path)

    assert loaded == [str(tmp_path / ".env.local")]
    assert os.environ["CLOSER_AGENT_MODEL"] == "openai-chat:MiniMax-M3"
    assert os.environ["QUOTED_VALUE"] == "hello world"
    assert os.environ["EXISTING_KEY"] == "from-env"


def test_load_local_env_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOSER_SKIP_DOTENV", "1")
    (tmp_path / ".env.local").write_text("SHOULD_NOT_LOAD=1", encoding="utf-8")

    assert load_local_env(tmp_path) == []
    assert "SHOULD_NOT_LOAD" not in os.environ

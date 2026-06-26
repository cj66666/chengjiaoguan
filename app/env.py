"""
/* ========================================================================== */
/* GEB L3: 本地环境变量加载                                                   */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 os、pathlib 与可选 .env.local/.env 文件
 * [OUTPUT]: 对外提供 load_local_env，从项目根读取 key=value 环境变量
 * [POS]: app 的本地启动适配层，让开发机可持久接线外部 provider，同时不提交真实密钥
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ENV_FILES = (".env.local", ".env")


def load_local_env(root: Path | None = None, *, override: bool = False) -> list[str]:
    if os.getenv("CLOSER_SKIP_DOTENV") == "1":
        return []
    root = root or Path(__file__).resolve().parents[1]
    loaded: list[str] = []
    for name in DEFAULT_ENV_FILES:
        path = root / name
        if path.exists():
            _load_env_file(path, override=override)
            loaded.append(str(path))
    return loaded


def _load_env_file(path: Path, *, override: bool) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or (not override and key in os.environ):
            continue
        os.environ[key] = _clean_value(value.strip())


def _clean_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

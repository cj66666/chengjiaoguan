"""
/* ========================================================================== */
/* GEB L3: Demo 场景路由                                                      */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 FastAPI APIRouter/Depends、租户依赖、SQLAlchemy Session 与 demo seed 服务
 * [OUTPUT]: 对外提供 router，暴露 /api/v1/demo/seed 与 /api/v1/demo/wave3 演示提交入口
 * [POS]: routers 的演示辅助边界，让 Demo 主链路能一键生成可审阅数据，生产业务规则仍在 services 中执行
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.dependencies import get_seller_id
from app.services.demo import seed_demo_scenario, wave3_submission_manifest


router = APIRouter(prefix="/api/v1")


@router.post("/demo/seed")
def seed_demo(
    seller_id: int = Depends(get_seller_id),
    session: Session = Depends(get_session),
) -> dict:
    result = seed_demo_scenario(session, seller_id)
    session.commit()
    return result


@router.get("/demo/wave3")
def wave3_demo_manifest() -> dict:
    return wave3_submission_manifest()

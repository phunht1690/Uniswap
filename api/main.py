"""Serve the supplied dashboard and the versioned research API together."""
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes.v1 import router
from api.routes.workbench import router as workbench_router
from api.routes.live import router as live_router
from api.routes.news import router as news_router
from src.models.service import SimulationService
from src.utils.config import ROOT, state_directory


def create_app(state_dir: Path | None = None, *, live_enabled: bool | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = SimulationService(state_dir or state_directory())
        from src.data.live import LiveMarket
        app.state.live_enabled=(state_dir is None and os.getenv('UNISWAP_LIVE_ENABLED','1').lower() not in {'0','false','no'}) if live_enabled is None else live_enabled
        live_market=LiveMarket(app.state.service)
        app.state.live_market=live_market
        from src.data.news import NewsFeed
        news_enabled = state_dir is None and os.getenv('UNISWAP_NEWS_ENABLED', os.getenv('UNISWAP_LIVE_ENABLED', '1')).lower() not in {'0','false','no'}
        news_feed = NewsFeed(app.state.service, enabled=news_enabled)
        app.state.news_feed = news_feed
        if app.state.live_enabled:await live_market.start()
        await news_feed.start()
        try:yield
        finally:
            await news_feed.stop()
            await live_market.stop()

    app = FastAPI(title="Uniswap LP Research API", version="0.6.0", lifespan=lifespan,
                  description="Bước 5 — mô phỏng và historical replay có giả định phí/thanh khoản; dữ liệu quan sát không đồng nghĩa phí LP đã tái dựng. Công cụ nghiên cứu, không phải lời khuyên đầu tư.")
    app.add_middleware(CORSMiddleware,
                       allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo the request body: it may contain an accidentally pasted key.
        issues = [{"field": ".".join(str(part) for part in error["loc"]), "type": error["type"],
                   "constraint": error.get("ctx", {}).get("ge", error.get("ctx", {}).get("le"))} for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "Tham số không hợp lệ. Kiểm tra kiểu dữ liệu và giới hạn trong /docs; path_index phải nhỏ hơn n_paths, n_paths × horizon_days ≤ 1.000.000.", "errors": issues})

    app.include_router(router)
    app.include_router(workbench_router)
    app.include_router(live_router)
    app.include_router(news_router)

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(ROOT / "dashboard/rangelab/overview.html", media_type="text/html")

    for page in ['overview','lp-optimizer','optimization-results','strategy-backtesting','risk-and-research','data-and-methodology']:
        def page_response(page=page):
            name='risk-and-research' if page=='data-and-methodology' else page
            return FileResponse(ROOT/'dashboard/rangelab'/(name+'.html'),media_type='text/html')
        app.add_api_route('/'+page,page_response,methods=['GET'],include_in_schema=False)

    @app.get('/legacy',include_in_schema=False)
    def legacy_dashboard():return FileResponse(ROOT/'dashboard/index.html',media_type='text/html')

    app.mount("/dashboard", StaticFiles(directory=ROOT / "dashboard", html=True), name="dashboard")
    return app


app = create_app()

"""Observed-input simulation, data diagnostics and saved research runs."""
from datetime import date
import csv
import io
import json
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import Response

from api.schemas import BacktestQuery, BacktestRequest, BacktestRecord, PoolList, RunRecord, SimulationRequest, SimulationResponse
from src.data.backtest import BacktestUnavailable
from src.evaluation.backtest_service import BacktestService
from src.evaluation.artifacts import artifact, latest_manifest
from src.evaluation.reconciliation import research_reconciliation
from src.models.service import SimulationInputError, StageNotImplemented, UnknownPool
from src.data.market import MarketUnavailable

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health(request: Request):
    try:
        catalog = request.app.state.service.pool_list()
        kind, status, message = catalog.data_kind, "ok", "Dashboard gọi engine Python; xem data_asof và assumptions của từng run."
    except MarketUnavailable as exc:
        kind, status, message = "unavailable", "degraded", str(exc)
    return {"status": status, "stage": 5, "ui_version": "rangelab-v1", "data_kind": kind, "engine_status": "numpy_simulation",
            "ingestion_available": (request.app.state.service.state_dir / "data/coverage.json").exists(),
            "message": message}


@router.get("/data/status")
def data_status(request: Request):
    root = request.app.state.service.state_dir
    path = root / "data/coverage.json"
    if not path.exists():
        return {"mode": "not_downloaded", "datasets": [], "quality": None}
    coverage = json.loads(path.read_text(encoding="utf-8"))
    quality_path = root / "data/quality_report.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else None
    return {**coverage, "quality": quality}


@router.get("/pools", response_model=PoolList)
def pools(request: Request):
    try:
        return request.app.state.service.pool_list()
    except MarketUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@router.post("/simulate", response_model=SimulationResponse)
def simulate(body: SimulationRequest, request: Request):
    try:
        return request.app.state.service.simulate(body)
    except UnknownPool as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except SimulationInputError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except MarketUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except StageNotImplemented as exc:
        raise HTTPException(501, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, detail="Không ghi/đọc được cache kết quả. Kiểm tra quyền của thư mục outputs/runs trong UNISWAP_STATE_DIR rồi khởi động lại máy chủ.") from exc


@router.get("/runs/{run_id}", response_model=RunRecord | BacktestRecord)
def run_record(run_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")], request: Request):
    try:
        return request.app.state.service.get_run(run_id)
    except FileNotFoundError as exc:
        try:
            return BacktestService(request.app.state.service.state_dir).get(run_id)
        except FileNotFoundError:
            raise HTTPException(404, detail="Không tìm thấy run_id trong outputs/runs hoặc outputs/backtests của máy chủ này.") from exc


@router.get("/backtest/{pool}")
def backtest(pool: str, request: Request, query: Annotated[BacktestQuery, Query()]):
    if query.start >= query.end:
        raise HTTPException(400, detail="Ngày bắt đầu phải trước ngày kết thúc.")
    try:
        return BacktestService(request.app.state.service.state_dir).run(BacktestRequest(pool=pool, **query.model_dump()))
    except BacktestUnavailable as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except MarketUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, detail="Không đọc/ghi được dữ liệu hoặc outputs/backtests; kiểm tra quyền thư mục.") from exc


@router.get('/backtests/{run_id}/curve.csv')
def backtest_csv(run_id: Annotated[str, Path(pattern=r'^[0-9a-f]{64}$')], request: Request):
    try:
        result = BacktestService(request.app.state.service.state_dir).get(run_id).result
    except FileNotFoundError as exc:
        raise HTTPException(404, detail='Không tìm thấy backtest run_id.') from exc
    stream = io.StringIO(newline='')
    rows = result['equity_curve']
    if rows:
        rows = [{**row, 'data_kind': result['meta']['data_kind'], 'run_id': run_id} for row in rows]
        leading = ['timestamp','lp','hodl']
        writer = csv.DictWriter(stream, fieldnames=leading + [key for key in rows[0] if key not in leading])
        writer.writeheader()
        writer.writerows(rows)
    return Response(stream.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="backtest-{run_id[:12]}.csv"'})


@router.get('/research/status')
def research_status(request: Request):
    try:
        manifest=latest_manifest(request.app.state.service.state_dir)
        return {key:manifest[key] for key in ['research_id','version','data_kind','status','files']}
    except FileNotFoundError as exc:
        raise HTTPException(404,detail=str(exc)) from exc
    except (ValueError,OSError) as exc:
        raise HTTPException(503,detail='Không đọc được research manifest hợp lệ.') from exc


@router.get('/research/files/{name}')
def research_file(name: str, request: Request):
    try:
        data=artifact(request.app.state.service.state_dir,name)
    except FileNotFoundError as exc:
        raise HTTPException(404,detail=str(exc)) from exc
    except (ValueError,OSError) as exc:
        raise HTTPException(503,detail='Không đọc được file nghiên cứu có hash hợp lệ.') from exc
    suffix=name.rsplit('.',1)[-1]
    media={'csv':'text/csv','png':'image/png','json':'application/json','md':'text/markdown'}.get(suffix,'application/octet-stream')
    return Response(data,media_type=media,headers={'Content-Disposition':f'attachment; filename="{name}"'})


@router.get('/research/reconciliation')
def research_evidence_reconciliation(request: Request):
    try:
        return research_reconciliation(request.app.state.service.state_dir)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail='Chưa có đủ tệp nghiên cứu đã xuất để đối chiếu.') from exc
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        raise HTTPException(503, detail='Không đối chiếu được các tệp nghiên cứu cùng phiên bản và hash hợp lệ.') from exc

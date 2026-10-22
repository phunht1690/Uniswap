"""Public live market status and explicit immutable simulation input capture."""
from fastapi import APIRouter,HTTPException,Request,Response
from api.app_schemas import LiveSnapshotRequest
from src.data.live_snapshot import capture
from api.routes.workbench import guarded

router=APIRouter(prefix='/api/v1')


@router.get('/market/live')
def market(request:Request,response:Response):
    response.headers['Cache-Control']='no-store'
    result=request.app.state.live_market.snapshot()
    result['enabled']=request.app.state.live_enabled
    return result


@router.post('/market/snapshot')
def snapshot(body:LiveSnapshotRequest,request:Request):
    if not request.app.state.live_enabled:raise HTTPException(503,detail='Tự cập nhật thị trường đang tắt trên máy chủ này.')
    return guarded(lambda:capture(request.app.state.service,request.app.state.live_market,body.pool))

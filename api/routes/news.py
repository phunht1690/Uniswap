"""Read the shared news cache; a visitor never triggers an upstream request."""
from fastapi import APIRouter, HTTPException, Query, Request, Response

router = APIRouter(prefix='/api/v1')


@router.get('/news')
def news(request: Request, response: Response,
         pool: str = Query(default='weth-usdc-500', min_length=1, max_length=100, pattern=r'^[a-z0-9-]+$')):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return request.app.state.news_feed.snapshot(pool)
    except ValueError:
        raise HTTPException(404, detail='Không tìm thấy pool trong danh sách được xác minh.') from None

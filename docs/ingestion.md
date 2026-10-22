# Ingestion dữ liệu công khai — bước 3

Chạy `python manage.py data` hoặc `make data` để lấy dữ liệu công khai. Không cần key. Mỗi nguồn tải tới bản ghi mới nhất nó trả về; không ép tất cả nguồn có cùng khoảng thời gian. Xem `data/coverage.json`, bản CSV tương ứng và `GET /api/v1/data/status` để kiểm tra kết quả thực tế. Nguồn lỗi không được thay bằng dữ liệu giả. Các dataset tải thành công vẫn được giữ khi một nguồn khác lỗi.

```powershell
cd C:\Users\ADMIN\Downloads\uniswap
.\.venv\Scripts\python.exe manage.py data
# Chỉ cập nhật một số nguồn:
.\.venv\Scripts\python.exe -m src.data.ingest --sources binance,defillama
```

| Nguồn | Dữ liệu và giới hạn |
| --- | --- |
| Ethereum PublicNode RPC | Factory xác minh 8 pool/2 fee tiers mỗi cặp; token0/token1/decimals, slot0/liquidity ở block finalized; tick bitmap/net/gross quanh giá; mẫu swap/mint/burn có checkpoint |
| GeckoTerminal | OHLCV theo pool ngày/giờ, phân trang lùi đến khi nguồn dừng/giới hạn. Giá quote/base yêu cầu đúng địa chỉ token; volume lấy từ yêu cầu `currency=usd` riêng, ghép đúng timestamp. Nguồn công khai có giới hạn lịch sử |
| Binance | Toàn bộ kline ngày/giờ nguồn trả về cho ETHUSDT, BTCUSDT, ETHUSDC, USDCUSDT, ETHBTC. Chỉ là tham chiếu CEX; volume tuyệt đối không được dùng như volume pool |
| DefiLlama | Context TVL/volume hiện tại, toàn bộ TVL history trả về cho các pool khớp chain/token contracts/fee tier. Không đưa APY/APR vào dataset xử lý hay mô hình |
| CoinGecko | 365 ngày giá USD/market-wide volume; không gán volume toàn thị trường cho pool. Điểm intraday cuối được giữ đúng thời gian, không coi là nến ngày hoàn chỉnh |
| FRED | CSV công khai DFF, CPIAUCSL, DTWEXBGS nếu truy cập được. Vintage mới nhất có thể được sửa; `predictive_eligible=false`. DTWEXBGS là chỉ số USD rộng có trọng số thương mại, không phải ICE DXY |
| The Graph | Adapter có key tùy chọn, ID cursor/pinned block/checkpoint cho day/hour, swaps, mints, burns, ticks; kiểm thử bằng HTTP fixture. Chưa xác minh live vì phiên này không có key |
| BigQuery | Không sử dụng, không bật billing; là phương án thay thế cho indexer |
| Kaiko, X, Reddit, CryptoPanic | `fetch(...)` báo `NotImplementedError`; không sinh dữ liệu thay thế |

Không có toàn bộ swaps/mints/burns từ khi pool được tạo trong bản tải công khai này. Mặc định CLI lấy cửa sổ 2.000 block finalized gần nhất cho mỗi pool, tối đa hai chunk. `complete_requested_window` chỉ có nghĩa đủ **cửa sổ block đã ghi**, không có nghĩa đủ lịch sử pool. Tick là snapshot quanh giá, không phải lịch sử mọi tick; gas là base fee một block, không phải lịch sử chi phí giao dịch. Không gán snapshot hôm nay ngược về 2022–2024.

The Graph không chạy trong public CLI. Khi gọi adapter trực tiếp cho day/hour ở block lịch sử, cung cấp `block_timestamp` UTC của đúng block để loại kỳ chưa đóng tại snapshot đó. Thiếu timestamp này, dữ liệu Graph aggregate được đánh dấu `predictive_eligible=false`, không tự dùng cho backtest hoặc ghi đè history từ nguồn công khai. `_meta` có TTL ngắn; các trang đã pin block có cache immutable. Live schema/indexer còn cần được xác minh với key của người dùng.

Để backfill RPC một khoảng xác định, đặt start/end block và giới hạn chunk. Chạy lại cùng start sẽ tiếp tục checkpoint. End phải không vượt block finalized. Lệnh này có thể cần nhiều giờ/ngày tùy phạm vi và hạn mức RPC:

```powershell
.\.venv\Scripts\python.exe -m src.data.ingest --sources events --event-start-block <start-block> --event-end-block <finalized-end-block> --event-chunks 20
```

Khoảng block không được tự suy thành khoảng ngày. Event giữ block hash, transaction hash, log index, topic/data raw và integer dạng chuỗi; lượng token phụ trợ dùng decimals. Swap có giá quote/base, nhưng chưa gán USD lịch sử khi chưa có quote/USD point-in-time. Mẫu log có thể tiếp tục độc lập với OHLCV, không thay volume ngày của aggregator bằng số event trong cửa sổ ngắn.

Raw HTTP được lưu theo request hash rồi content hash. `request.json` chứa request đã loại thông tin bí mật, status, thời gian tải, hash và đường dẫn nội dung. HTTP cache xác minh lại hash, retry lỗi mạng/429/5xx có backoff, tôn trọng Retry-After số giây và rate limit (tối đa 2 request/s; GeckoTerminal/CoinGecko cách ít nhất 6,2s). Không sửa nội dung quan sát cũ. Parquet có bản canonical và các phiên bản theo content hash trong `_versions/`. Canonical có thể đổi khi cập nhật; phiên bản cũ vẫn được giữ. Checkpoint nằm ở `data/interim/checkpoints/`.

Binance/Gecko phân trang lại qua raw cache để tái dựng dataset đầy đủ; chỉ đuôi dữ liệu hết TTL mới cần tải lại. Đây là resume qua cache, không chỉ nhảy tới cursor cuối rồi làm mất phần đầu. Event và The Graph giữ raw page list cùng cursor để resume. Tránh chạy hai ingestion cùng thư mục trạng thái đồng thời vì CSV ledger/checkpoint được thiết kế cho một writer.

`data/source_log.csv` ghi mỗi file/hash, nguồn, endpoint đã loại key, thời gian tải, khoảng quan sát và số dòng. `data/lineage.json` nối dataset chuẩn hóa với raw payload. `data/processed/research.duckdb` materialize các bảng Parquet để truy vấn khi chuyển thư mục vẫn dùng được; `catalog_manifest.json` cho phép bỏ qua rebuild khi hash không đổi. `catalog.duckdb` và `mock_pools` của các bước trước vẫn là fixture minh họa, được ghi nhãn riêng.

`data/quality_report.json` kiểm tra hash của tất cả payload hiện tại và cấu trúc thời gian/giá. `features_<pool>.parquet` dùng dữ liệu trễ một kỳ cho vol và mean volume 7/30 ngày; trả null nếu cửa sổ đi qua ngày trống. Không forward-fill hay backfill. Nến mang timestamp cuối kỳ; nến chưa đóng bị loại. Nguồn không cho lịch sử trước 2025 không thể được gọi là tập train 2022–2023; backtest đầy đủ vẫn cần bổ sung lịch sử pool phù hợp.

Các split train 2022–2023, validation 2024 và test 2025–2026 giữ nguyên. Bước 3 chỉ thu thập/chuẩn hóa/kiểm tra dữ liệu, chưa chọn mô hình, width, ngưỡng hoặc đánh giá hiệu quả trên test. Bước 4 sẽ nối registry/ticks/inputs quan sát và frontend; bước 5 mới làm backtest/hồi quy.

Tham chiếu chính thức: [Binance public market data](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md), [Ethereum JSON-RPC](https://ethereum.org/developers/docs/apis/json-rpc/), [Uniswap active liquidity](https://developers.uniswap.org/docs/sdks/v3/guides/managing-liquidity/active-liquidity), [Uniswap v3 schema](https://github.com/Uniswap/v3-subgraph/blob/main/src/v3/schema.graphql), [GeckoTerminal API](https://api.geckoterminal.com/docs/index.html), [DefiLlama API](https://api-docs.defillama.com/), [FRED DTWEXBGS](https://fred.stlouisfed.org/series/DTWEXBGS).

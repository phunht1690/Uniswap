# RangeLab — tích hợp giao diện Stitch và backend nghiên cứu

Thiết kế tham chiếu: `stitch_rangelab_uniswap_v3_analytics (1).zip`, gồm năm màn hình. Giữ bố cục sidebar/topbar, nền trắng/lavender, màu tím/teal, Inter và JetBrains Mono; bổ sung responsive cho cửa sổ hẹp. Template gốc nằm trong `frontend/templates`. Bản build loại script demo và dùng JavaScript kết nối API cùng origin; font và CSS được phục vụ cục bộ.

## Ma trận tính năng

| Màn hình / đường dẫn | Tính năng đã nối | Backend / dữ liệu |
|---|---|---|
| Tổng quan `/` hoặc `/overview` | KPI số pool/chiến lược, tìm kiếm, bốn bộ lọc, nút phân tích, chọn pool cho chart, 7/30/90 ngày và 1 năm, giá/volume/volatility thật, tooltip | `GET /api/v1/pools`, `/pools/{id}/history?days=...` |
| Tối ưu `/lp-optimizer` | Chọn cặp và fee tier; vốn; 7/30/90 ngày hoặc tùy chỉnh; hồ sơ rủi ro; σ lịch sử/ghi đè; volume ghi đè; gas; policy; năm giới hạn; slippage; GBM/bootstrap/GARCH; N/seed/path/block; reset; preview; chạy thật | `POST /api/v1/workbench/run` |
| Kết quả `/optimization-results?run_id=...` | Range, tick tham khảo đúng chiều token, hiệu quả vốn, sáu KPI, LP/HODL, phân rã, giá/wealth path, bảng chiến lược và lưới; chia sẻ; sửa tham số; stress; backtest; PDF/JSON | `/workbench/runs/{id}`, `/summary.pdf`, `/export.json` |
| Rủi ro `/risk-and-research?run_id=...` | Năm kịch bản preset và tùy chỉnh; ba slider; stress backend; LP/HODL/IL/trạng thái range; chart so sánh; quét volatility 10 mức với biên sửa được; bảng số liệu; tab phương pháp | `POST /workbench/stress`, `/workbench/sensitivity` |
| Backtest `/strategy-backtesting` | Pool/fee, ngày, vốn, gas; giả định nâng cao; gợi ý khoảng liên tục; năm chiến lược; bật/tắt chart; USD/%; tooltip; bảng xếp hạng ex-post; phí/IL; gas; nhận định theo số liệu; hai nút xuất CSV | `POST /backtests/compare`, `/pools/{id}/backtest-availability`, `/backtests/comparisons/{id}/export.csv` |
| Dữ liệu & Phương pháp `/data-and-methodology` | Coverage theo nguồn/dataset, số dòng/khoảng trống, phương trình mở rộng, run/data hash, seed, PDF phương pháp, JSON, tải 25 file nghiên cứu lưu trữ | `/data/status`, `/research/status`, `/research/files/{name}`, `/workbench/runs/{id}/methodology.pdf` |
| Dùng chung | Điều hướng thật, thuật ngữ, thông tin workspace, lỗi và loading, kiểm tra đầu vào, cấu hình lưu trình duyệt, kết quả lưu content hash, bảo vệ phản hồi cũ | FastAPI/Pydantic + file cache nguyên tử |
| Tin tức & cộng đồng `/risk-and-research?tab=news` | Đọc không cần run; chọn pool độc lập; lọc nguồn/token; tiêu đề, ngày đăng/lần lấy, nhãn phiên bản và trạng thái từng nguồn; link tìm kiếm X/Reddit và mở CryptoPanic | `GET /api/v1/news?pool=...`; cache bộ nhớ 300 giây, hai nguồn công khai Uniswap Labs Blog + governance RSS; X/Reddit/CryptoPanic chưa kết nối API |

Nút chia sẻ tạo URL của run đã lưu, dùng được trên máy chủ có cùng run ID. Không tự công bố lên Internet. JSON xuất chứa config/result/provenance, không chứa toàn bộ raw dataset. Raw/Parquet và source log nằm trong thư mục `data` và bản ZIP đầy đủ.

## Dữ liệu và phạm vi sử dụng

- 14 pool: WETH/USDC, WETH/USDT, WBTC/WETH mỗi cặp 0,05%/0,30%/1,00%; USDC/USDT 0,01%/0,05%; ARB/WETH trên Arbitrum 0,05%/0,30%/1,00%.
- Ethereum/Arbitrum RPC xác minh factory, token order, fee, slot0 và active-L. GeckoTerminal cung cấp metadata và OHLCV theo giới hạn công khai. DefiLlama cung cấp TVL. Binance/CoinGecko là giá tham chiếu, không thay volume pool.
- 14/14 pool chạy được mô phỏng. Backtest toàn khoảng quan sát có thể chạy trên 10 pool không có ngày trống. Bốn pool phí 1% cần đoạn liên tục được gợi ý, không tự điền ngày thiếu.
- Các đoạn liên tục kiểm tra được cho fee 1%: WETH/USDC 11/05–13/06/2026 (33 ngày replay, warmup 14N); WETH/USDT 12/05–25/07/2026 (74 ngày); ARB/WETH 05/04–21/10/2026 (199 ngày). WBTC/WETH chỉ đủ 17/03–24/03/2026 (7 ngày replay, warmup 7N), nên inference rất hạn chế. Nút áp dụng ghi rõ khi đổi warmup.
- Gợi ý khoảng chọn theo số ngày liên tục và ngày kết thúc, không dùng lợi nhuận để chọn khoảng.
- Thời điểm snapshot khác nhau theo pool; UI hiển thị thời điểm và mạng của pool đang chọn. Không dùng các nhãn “live subgraph”, “12ms”, “10.000 đường”, APY hoặc OOS cố định từ bản demo.

## Mô hình và giới hạn

`rangelab-workbench-v3` dùng đường giá chung để so sánh các chiến lược. Mục tiêu là kỳ vọng chênh lệch LP–HODL dưới ràng buộc xác suất từng rời range tại các mốc ngày. Range log liên tục; tick làm tròn ra ngoài chỉ để tham khảo, chưa áp vào định giá. Tỷ lệ không rời range là tần suất mô phỏng, không phải confidence interval.

Volume ghi đè là USD/ngày cố định. Nếu không ghi đè, engine dùng volume lịch sử và kịch bản volume đã công khai trong assumptions. Phí giữ dưới dạng USD cash; active-L snapshot và quote/USD giữ cố định trong forward, kể cả quote WETH. Lợi nhuận quy năm trên UI là ngoại suy tuyến tính, không phải protocol APR.

Policy `none` giữ range; `weekly` recenter sau mỗi bảy ngày; `threshold` recenter khi tỷ trọng base lệch ngưỡng đặt; `hedged` short delta inventory theo ngày. Hedge tính gas và turnover bps lúc mở, điều chỉnh và đóng hedge. Không có funding, borrow, margin hoặc ràng buộc khả năng thanh toán; đây là xấp xỉ rời rạc cho tính năng hedging trong thiết kế.

Stress giữ giá cuối kỳ theo shock và dùng GBM log bridge cho đường đi; volatility làm thay đổi thời gian trong range và phí. Không tối ưu lại range theo shock đã biết. Sensitivity dùng GBM, volume cố định, cùng seed và tối ưu lại mỗi σ; không phải kiểm định ngoài mẫu.

`rangelab-comparison-v1` dùng cùng khoảng ngày và đầu vào cho năm chiến lược. Cố định mặc định ±0,15 log; volatility dùng rolling 14 ngày trễ và cập nhật mỗi tuần; dynamic giữ độ rộng volatility lúc entry và recenter tuần; full range và HODL giữ vị thế. Giá và volume là quan sát; active-L lịch sử, fee-growth, protocol fee/gas vintage và crossing nội ngày chưa được tái dựng. TVL dùng độ trễ giả định, chưa xác minh vintage công bố. Chưa đủ pool price/volume 2022–2024 để xác nhận OOS 2025–2026.

Các engine/API bước 1–5 và dashboard gốc còn ở `/legacy`, `/dashboard/`. Các run cũ và nghiên cứu lưu trữ không bị ghi đè. Lệnh research mới giữ phạm vi tám pool Ethereum ban đầu và có phiên bản riêng; sáu pool thêm chưa tự được đưa vào nghiên cứu hồi quy đã công bố.

Giao diện RangeLab không còn liên kết điều hướng sang dashboard gốc. Tin tức hoạt động bằng worker riêng, không ghi vào registry, lịch sử, source ledger hoặc run đã lưu. Hai URL nguồn được cố định phía máy chủ; không nhận URL tùy ý từ trình duyệt. Bài lỗi định dạng hoặc quá cũ/tương lai bị bỏ qua, nội dung trùng URL được gộp, phản hồi nguồn giới hạn 2 MB. Nguồn hỏng giữ lần thành công trước và báo trạng thái. X/Reddit/CryptoPanic luôn được ghi rõ chưa kết nối, không có lời gọi API trả phí hay tài khoản tự động.

## Chạy và cập nhật

API và frontend build sẵn chạy bằng `.venv\Scripts\python.exe manage.py run` hoặc `run.cmd`, mở `http://127.0.0.1:8000/`.

Sửa frontend cần Node **20.18.1+**: `npm ci --prefix frontend`, rồi `npm run build --prefix frontend`. Node chỉ cần cho build/kiểm thử, không dùng trong mô phỏng Python.

`manage.py data` chạy bộ thu thập gốc rồi bổ sung các pool RangeLab còn thiếu. `manage.py extend-pools` chỉ bổ sung pool chưa có. `manage.py refresh-references` nối nến tham chiếu ngày mới đóng, giữ nguyên giá trị lịch sử đã lưu. Mỗi cập nhật làm mới feature, DuckDB catalog, coverage, source ledger và kiểm tra hash. Mạng bị giới hạn có thể khiến một nguồn chưa sẵn có; coverage ghi lý do.

Tham số được kiểm tra bằng Pydantic: vốn 1–100 triệu USD, H 1–365, N 1–5000, N×H≤1.000.000, path_index<N. Chạy cùng cấu hình, dữ liệu và phiên bản cho cùng run ID. Snapshot thay đổi thì stress/sensitivity của run cũ yêu cầu chạy mới, tránh trộn dữ liệu.

## Xác minh

Kiểm thử gồm engine và parity cũ, accounting các policy mới, hedge/recenter timing, rolling volatility không nhìn trước, timestamp ns/us, volume override, cache/hash, stress occupation, sensitivity, API routes và PDF/JSON/CSV. Smoke trên dữ liệu quan sát kiểm tra 14 mô phỏng và 14 backtest trên khoảng hợp lệ, ba mô hình giá, bốn policy, năm stress preset, mười mức σ và 25 file nghiên cứu khớp SHA256.

Giao diện được kiểm tra trong trình duyệt cho đủ năm màn hình, bộ lọc, cấu hình, kết quả thật, stress/độ nhạy, nguồn dữ liệu, backtest, chuyển USD/%, bật/tắt chuỗi, thuật ngữ và liên kết tải. PDF đã render và kiểm tra tiếng Việt, bố cục và font.

## Cập nhật câu chữ và biểu đồ rủi ro — 21/10/2026

Các nhãn chính dùng tiếng Việt dễ hiểu hơn: khoảng giá, mức biến động, phí mạng, giữ token và thử chiến lược trong quá khứ. Thuật ngữ/mã mô hình vẫn có trong cài đặt nâng cao và phần giải thích phương pháp. Bộ lọc lịch sử phân biệt rõ “7 ngày”, “30 ngày”, “90 ngày” và “1 năm”.

Lỗi biểu đồ stress trước đây: chỉ số dùng phản hồi của tình huống vừa chọn nhưng biểu đồ luôn vẽ năm tình huống mẫu cố định. Biểu đồ chính nay dùng đúng phản hồi vừa chạy, ghi rõ ba tham số và số tiền LP/HODL. Năm tình huống mẫu nằm riêng trong mục mở rộng, được tính một lần cho mỗi kết quả gốc. Lỗi tải tình huống tham khảo không chặn kết quả chính. Trạng thái hiển thị phân biệt tham số chưa chạy, đang tính, đã cập nhật và lỗi.

Mô hình tính toán giữ nguyên. Khi cố định giá cuối kỳ, tăng mức dao động có thể chỉ đổi thời gian trong khoảng giá và phí nhận được; tăng phí mạng không đổi tài sản HODL. Số tiền chính xác và phần chênh lệch giúp thấy thay đổi nhỏ mà chiều cao cột khó thể hiện.

Kiểm tra bổ sung: `node --test tests/stress_view.cjs` (3 kiểm thử hồi quy); `pytest tests/test_rangelab.py -o addopts='' -q` (13 kiểm thử API/mô hình). Trình duyệt đã kiểm tra riêng thay đổi giá, dao động và phí mạng trên kết quả người dùng đang xem, cùng bảng độ nhạy 10 mức.

## Cập nhật thị trường và hướng dẫn sử dụng — 21/10/2026

- `GET /api/v1/market/live`: bộ nhớ đệm thị trường mới cho 14 pool. Worker chạy khi API bật, kiểm tra RPC Ethereum/Arbitrum mỗi 30 giây; TVL, khối lượng 24h và quote/USD từ GeckoTerminal mỗi 300 giây. Giao diện đọc trạng thái mỗi 30 giây khi tab đang hoạt động. Đây là cập nhật gần thời gian thực bằng thăm dò định kỳ, có độ trễ nguồn, không phải luồng từng swap.
- RPC kiểm tra chain ID, gọi slot0/liquidity tại cùng một block latest và kiểm tra lại hash. Latest còn có thể bị sắp xếp lại. Từng nguồn có giờ lấy thành công, trạng thái mới/trễ/lỗi; không thay dữ liệu lỗi bằng số 0. API thị trường không ghi đè registry, lịch sử hoặc source ledger nghiên cứu.
- `POST /api/v1/market/snapshot` nhận `{pool}` và lưu một bộ đầu vào bất biến tại `outputs/market_snapshots/{hash}`. Lưu giá, active-L, quote/USD, TVL/volume, thời điểm riêng từng nguồn và bản lịch sử hiệu chỉnh có hash. Chưa thu thập lại toàn bộ phân bố tick trong luồng nhanh; không dùng tick cũ dưới nhãn dữ liệu mới.
- `POST /api/v1/workbench/run` nhận thêm `market_snapshot_id` tùy chọn. Cài đặt mặc định trên UI dùng dữ liệu thị trường mới; người dùng có thể bỏ chọn để chạy bộ nghiên cứu đã lưu. Stress/độ nhạy của run live đọc đúng bộ đầu vào đã chụp, kể cả khi worker tiếp tục cập nhật. Hash cũ được giữ nguyên khi không dùng trường mới.
- Thiếu dữ liệu mới, thiếu thanh khoản hoạt động hoặc nguồn bị trễ thì tạo run live báo lý do; không tự chuyển sang snapshot cũ. Biến động/historical replay vẫn dùng lịch sử đã thu thập, không tự bổ sung nến lịch sử theo mỗi lần poll.
- Nút tài khoản được thay bằng `ⓘ Thông tin`, mở hướng dẫn về mục đích, 5 màn hình, các bước, thuật ngữ, stress test, thời điểm dữ liệu và giới hạn mô hình. Bản Markdown nằm trong `docs/dashboard_user_guide.md`. Không kết nối ví hoặc gửi giao dịch.

Xác minh: 128 kiểm thử Python, 3 kiểm thử hồi quy biểu đồ, kiểm tra nguồn thật cho 14/14 pool, tối ưu/stress bằng dữ liệu live với WETH/USDC, WBTC/WETH và ARB/WETH, cùng thao tác tối ưu qua trình duyệt. Giá live được cập nhật trong khi kết quả đã lưu giữ nguyên.

Tài liệu giao thức: [Ethereum JSON-RPC](https://ethereum.org/developers/docs/apis/json-rpc/), [Uniswap V3 pool state](https://github.com/Uniswap/v3-core/blob/main/contracts/interfaces/pool/IUniswapV3PoolState.sol), [GeckoTerminal API](https://api.geckoterminal.com/docs/index.html).

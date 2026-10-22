# Phạm vi và quyết định triển khai

Yêu cầu thực thi hiện tại là nội dung dán “nối dashboard với backend Python”, gồm 5 bước và dừng báo cáo sau mỗi bước. Các tài liệu đính kèm là đầu vào nghiên cứu; lệnh của prompt cũ được đối chiếu với yêu cầu hiện tại, không tự động thay thế nó.

| Khác biệt | Quyết định |
| --- | --- |
| Prompt cũ yêu cầu Streamlit + 8 trang, prompt hiện tại yêu cầu FastAPI + giữ HTML | Dùng FastAPI và HTML hiện có; bổ sung frontend ở bước 4 |
| Prompt cũ có Giai đoạn 0 và 8 giai đoạn, nội dung dán có 5 bước | Làm 5 bước mới; bàn giao bước 1 rồi dừng báo cáo |
| Đề cương Word đề xuất 2022–giữa 2026, người dùng yêu cầu toàn bộ lịch sử | Phạm vi tải là earliest→latest từng nguồn; chia nghiên cứu 2022–2024/2025–2026 vẫn cố định; 2021 dùng warmup |
| Bản HTML có 4 preset, đề cương yêu cầu ít nhất 2 fee tiers/cặp khi khả dụng | Giữ 4 preset cho bước 1; discovery nhiều fee tier thuộc ingestion thật |
| Tài liệu dùng thông tin tới t, nội dung dán yêu cầu tới t−1 | Dùng lag một kỳ bảo thủ hơn cho quyết định tại t; kiểm thử thực tế ở bước engine/data |
| HTML dùng fixed w=0.2 nhưng gọi ±20% | Đây là ±20% theo log, tương đương e^(±0.2), không phải [0.8P0,1.2P0]; giữ để parity rồi diễn giải rõ |
| HTML dùng μ=0 GBM và volume theo |ε|, CONC=3 | Chỉ là giả định để đối chiếu JS; không gọi là phí/thanh khoản thật |
| Công thức phân rã dễ trừ IL hai lần | Dùng ΔR=(LP_inventory+fees−gas−rebalance_cost−HODL)/capital; nếu inventory đã phản ánh IL thì không trừ lại |
| WBTC/WETH có p0 bằng WETH nhưng vốn USD | Engine thật cần WETH/USD point-in-time; không giả định WETH=1 USD |
| Optimizer HTML chọn range rộng nhất khi không có nghiệm thỏa ràng buộc | Bước 2 phải trả trạng thái không khả thi rõ ràng; không gọi fallback là optimum khả thi |
| `agg()` HTML chia cả active share và exit probability cho capital | Lỗi chuẩn hóa có sẵn, làm xác suất hiển thị gần 0 và ràng buộc rủi ro sai; giữ bản gốc ở bước 1, tách parity toán v3 khỏi sửa aggregation ở bước 2 |
| GBM giữa Python/JS dùng PRNG khác nhau | Parity kiểm tra bằng cùng đường giá đầu vào; seed tái lập trong từng engine, không mặc định seed bằng nhau cho đường bằng nhau |

Toàn bộ thời gian không đồng nghĩa mọi nguồn đều có cùng độ phủ. Bước 3 cần manifest độ phủ theo pool/nguồn/cấp dữ liệu, phân trang, retry, cache và checkpoint. Tick snapshot hiện tại không được gán ngược cho lịch sử. Backfill từng swap hoặc tái dựng tick lịch sử phụ thuộc subgraph/RPC/quyền BigQuery và hạn mức; không tự bật truy vấn tính phí không giới hạn.

API key không được gửi vào chat, ghi vào source log hoặc nhúng trong URL được lưu. Bước 1 không đọc và không kiểm tra key; `.env.example` chỉ liệt kê tên biến môi trường cần cho các bước sau.

Sau bước 2, các việc sửa aggregation, trạng thái optimizer không khả thi, net LP return và σ=0 đã hoàn thành; oracle JS gốc vẫn giữ nguyên để đối chiếu. Engine bootstrap/GARCH được kiểm thử bằng dữ liệu tổng hợp, nhưng API chỉ chấp nhận lịch sử có source log và calibration_asof. Chi tiết triển khai và các khác biệt có chủ đích nằm trong `stage_2_report.md`. Chưa gọi API nguồn thị trường, chưa đưa ra kết quả ngoài mẫu thật.

Tham chiếu triển khai: [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/), [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), [Static files](https://fastapi.tiangolo.com/tutorial/static-files/). Nội dung kinh tế lượng và kết quả các bài báo trong Word chưa được xác minh lại ở bước hạ tầng này.

Bước 3: người dùng chọn **tiếp tục bằng nguồn công khai** khi chưa có key The Graph/BigQuery. Triển khai RPC Ethereum + GeckoTerminal làm nguồn pool công khai bổ sung, cùng Binance/CoinGecko/DefiLlama và FRED tùy chọn. Có adapter The Graph được kiểm thử bằng fixture nhưng chưa gọi live, BigQuery không dùng. Public OHLCV có ranh giới quyền truy cập, RPC state cũ cần personal token; vì vậy chỉ báo độ phủ thực tải, không coi mẫu events hoặc tick snapshot là toàn bộ lịch sử. Chi tiết và bằng chứng ở `ingestion.md`, `stage_3_report.md` và `data/coverage.json`.

Bước 5 triển khai historical replay có phí mô hình thay vì gán active liquidity hiện tại ngược về quá khứ. Dùng TVL lagged với publication lag giả định, công bố việc thiếu vintage, gas và protocol fee lịch sử. Không thể hoàn thành yêu cầu nghiên cứu **xác nhận OOS** khi thiếu pool price/volume 2022–2024; trạng thái này được ghi vào manifest, report và UI, không giả là tiêu chí đã đạt. Volatility/volume tại entry dùng strictly-before-entry; thông tin quote/base tại execution và realized volume của bar là biến outcome, không dùng chọn range bằng tương lai.

Đề cương Word ưu tiên τ=0.1/0.5/0.9 và HAC/Driscoll–Kraay thay vì cụm theo vài pool: triển khai đúng lựa chọn này; quantile bootstrap theo common-time blocks. Fee tier bất biến theo pool bị hấp thụ bởi pool FE, nên bỏ khỏi mô hình pool FE và thêm mô hình pair FE riêng. Các quy tắc range/seed/chi phí được cố định trước khi tính outcome, không chọn hyperparameter từ kết quả 2025–2026.

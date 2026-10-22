# Báo cáo bước 2

Đã thay API fixture bằng engine NumPy có seed và giữ nhãn **Dữ liệu minh họa**. Công cụ mô phỏng nghiên cứu, không phải lời khuyên đầu tư. Chưa tải dữ liệu thị trường thật và chưa nối biểu đồ HTML với `/simulate`.

Các phần đã hoàn thành:

- `v3.py`: liquidity từ vốn/range, inventory theo ba vùng, công thức IL v2 và tick↔price có decimals/thứ tự token. Tính bằng expm1 để ổn định ở range rất hẹp.
- `price_models.py`: GBM μ=0; paired stationary block bootstrap trên log return–volume; GARCH(1,1) ước lượng bằng arch và mô phỏng bằng RNG NumPy có seed.
- `fees.py`/`strategies.py`: phí theo liquidity share, bốn chiến lược dùng cùng thị trường, min_gap, max_rebalances, gas hai giao dịch/recenter và slippage bps tùy chọn.
- Optimizer quét 20 độ rộng log, tối đa hóa mean ΔR chỉ trong tập khả thi. Không có nghiệm thì trả optimum=null và thông báo; không đưa range vi phạm làm khuyến nghị.
- Metrics: fees, IL, gas, slippage, net LP return, ΔR, Q5, CVaR5, active share, xác suất từng rời range và số rebalance. Có kiểm tra cộng các thành phần bằng ΔR.
- Features trễ một kỳ; snapshot lấy timestamp < calibration_asof. Tuning sample chỉ chứa 2022–2024, không chứa test 2025–2026. Các test thay dữ liệu tương lai kiểm tra cả feature, bootstrap, GARCH fit và API run_id/result.
- Lịch sử dùng qua API phải có hash khớp source_log.csv. Thiếu lịch sử/asof, ngày trống, dữ liệu sai hoặc GARCH không hội tụ được báo rõ; không tự tạo lịch sử giả cho người dùng.
- Run hash gồm config/seed, snapshot dữ liệu sử dụng, provenance, settings, model version và các phiên bản thư viện số. Cache JSON vẫn tái đọc được sau khởi động lại; run bước 1 có thể đọc tiếp.

Đối chiếu với bản JS gốc:

`tests/fixtures/original_math.js` được trích nguyên các hàm pos/run/agg từ HTML người dùng cung cấp, kèm hash nguồn. Node chạy oracle thật; Python và JS nhận cùng đường giá và innovation. Các kiểm tra giá trị vị thế dưới/trong/trên range và cashflow full/fixed/dynamic đạt sai số tuyệt đối <1e−6. Không yêu cầu cùng seed tạo cùng đường giữa PCG64 của Python và mulberry32 của JS.

Những khác biệt có chủ đích:

| Bản gốc | Bước 2 |
| --- | --- |
| agg chia active/exit cho vốn | Tính trung bình tỷ lệ/xác suất trực tiếp |
| Không có range khả thi vẫn chọn range rộng nhất | API trả optimum=null; JS ghi rõ nếu không khả thi |
| Lưới cũ thường quá hẹp để thỏa ngưỡng rủi ro | 20 điểm từ min_width đến max(0.5,4σ√T), hoặc max_width do người dùng đặt |
| KPI net bị tính giống ΔR | Net bao gồm lợi suất inventory; ΔR giữ benchmark HODL riêng |
| σ=0 gây chia 0 khi ước lượng volume | Dùng volume trung bình đã khai báo |
| Dynamic không giới hạn số recenter | max_rebalances, mặc định 52; min_gap giữa các lần recenter |

Các sửa aggregation, net, σ=0, grid và giới hạn recenter cũng đã áp vào JS minh họa. CSS giữ nguyên. Banner ghi rõ engine Python hoạt động nhưng biểu đồ vẫn dùng JS; fetch/debounce/loading/error và tick thật thuộc bước 4.

Kiểm tra: **67 kiểm thử pytest đạt trong chính .venv của dự án**, bao phủ parity, seed, edge cases, decomposition, temporal split, no-look-ahead, provenance, quyền ghi cache và API. Node smoke kiểm tra KPI, bốn biểu đồ, bảng/stress, đổi đường giá, active/exit/net và hoạt động file offline. Có một cảnh báo deprecation TestClient/httpx của Starlette, không gây test lỗi. pip check không phát hiện phụ thuộc lỗi.

HTTP thực tại localhost đã kiểm tra health, POST simulate, GET run và gửi lại config đã lưu: cùng run_id và toàn bộ result giống nhau. Ví dụ GBM seed 42, 300 đường, 60 ngày được lưu trong gói bàn giao. Dashboard đã khởi động lại, banner xác nhận engine Python bước 2 hoạt động. Biểu đồ vẫn tính bằng JS minh họa theo phạm vi bước 4.

Đã xử lý thêm lỗi quyền ghi trong phiên chạy bị hạn chế trên Windows: tạo file cache theo đường dẫn UUID với chế độ exclusive để lỗi quyền trả ngay, tránh vòng lặp thử tên tạm của NamedTemporaryFile. API trả 503 có thông báo thư mục cần kiểm tra khi cache không ghi/đọc được. Máy chủ hiện chạy với quyền ghi thư mục dự án người dùng đã chỉ định.

Giả định còn dùng ở bước 2:

- Giá ngày, quan sát active tại cuối ngày, biên bao gồm hai đầu để khớp JS; bỏ qua crossing và giao dịch trong ngày.
- TVL, volume và CONC=3 vẫn là preset minh họa; L_nền=TVL×CONC/2 không phải thanh khoản tick thật. Volume GBM/GARCH phụ thuộc innovation theo giả định cũ; bootstrap giữ cặp lịch sử.
- Giá chuẩn hóa p0=1; quote/USD cố định, kể cả WETH ở WBTC/WETH. Không trình bày đây là dự báo chung USD của hai tài sản.
- Phí giữ riêng, không tái đầu tư; gas mở một lần, hai lần/recenter, chưa tính gas đóng. Slippage là bps×inventory dời range và ghi thành cash cost riêng. Chưa áp ràng buộc khả năng tài trợ khi phí gas làm wealth âm.
- Stress ±30% cộng phí kỳ vọng giữ nguyên; không nội sinh hóa volume/thanh khoản. Optimizer chọn và đo trên tập Monte Carlo chung, có thể lạc quan do chọn mẫu; chưa có đánh giá ngoài mẫu thật.
- Chưa mô hình hóa MEV/JIT, impact, gas lịch sử, thanh khoản nền biến thiên hoặc LVR của thanh khoản tập trung.

Còn lại theo lộ trình: bước 3 tải/chuẩn hóa toàn bộ lịch sử khả dụng, ticks/liquidity thật và provenance; bước 4 nối frontend API và tab backtest; bước 5 backtest, hồi quy panel/quantile và đánh giá ngoài mẫu. Dừng sau bước 2 theo yêu cầu của người dùng.

# Báo cáo bước 1

Đã dựng khung dự án theo yêu cầu FastAPI và giữ dashboard HTML đính kèm. Bước 1 chỉ dùng **Dữ liệu minh họa**; chưa có kết quả nghiên cứu trên dữ liệu thật.

Đã triển khai:

- API `/api/v1`: health, pools, simulate fixture, lưu/tái đọc runs và backtest trả 501 rõ lý do.
- Pydantic schema, giới hạn đầu vào, lỗi tiếng Việt, CORS localhost.
- Run id SHA256 có config/seed/hash dữ liệu/settings/model_version và file JSON ghi nguyên tử.
- Fixture raw JSON, Parquet, DuckDB và nhật ký nguồn có hash. Sinh lại cùng fixture không tải hay ghi log trùng.
- Cấu hình toàn bộ lịch sử khả dụng theo từng pool/nguồn, cùng train 2022–2023, validation 2024, test 2025–2026 tách biệt.
- Dashboard giữ CSS và engine JS, thêm banner phân biệt API mock với số liệu JS; chế độ file cục bộ vẫn hoạt động.
- README, từ điển dữ liệu, danh sách quyết định khi tài liệu mâu thuẫn.

Kiểm tra đã chạy:

- `python manage.py test`: **25 passed**; có một cảnh báo deprecation của Starlette về TestClient/httpx, không có test lỗi.
- Node smoke test: KPI, bốn biểu đồ, bảng chiến lược, stress và nút đổi đường giá của JS gốc chạy offline, không gọi mạng.
- `python manage.py data`: tạo fixture 4 pool, Parquet/DuckDB, source log; CLI tiếng Việt chạy trên Windows.
- Máy chủ Uvicorn khởi động; HTTP thực tới `/`, `/api/v1/health`, `/api/v1/simulate` hoạt động.
- Kiểm tra trình duyệt: banner hiển thị API bước 1 hoạt động; dashboard render các biểu đồ.
- Tắt backend rồi bấm kiểm tra API và đổi đường giá trên trang đã mở: thông báo nêu lỗi kết nối, P&L vẫn đổi bằng JS.
- Cùng cấu hình được tái đọc và gửi lại sau khởi động ứng dụng cho cùng run_id/result. Đã sửa chuẩn hóa giá trị mặc định int/float gây hash khác nhau.
- Kiểm thử dùng thư mục tạm riêng mỗi lần chạy để tránh lỗi quyền của `pytest-of-ADMIN` khi đổi ngữ cảnh Windows; dọn thư mục do chính lần chạy tạo ra sau khi hoàn tất.

Lỗi đã xác định trong bản HTML gốc: `agg()` chia nhầm active share và exit probability cho vốn. Lỗi này ảnh hưởng ràng buộc optimizer. Bước 1 giữ mã toán gốc để đối chiếu; bước 2 sẽ tách kiểm tra parity v3 khỏi việc sửa aggregation. Mọi biểu đồ hiện tại chỉ có tính minh họa.

Chưa triển khai: engine NumPy/v3 parity/GBM/bootstrap/GARCH, ingestion thị trường thật, tick thật, frontend gọi simulate, backtest, hồi quy và kiểm chứng ngoài mẫu. Source adapters The Graph/BigQuery, DefiLlama, Binance/CoinGecko, FRED hiện mới là kế hoạch trong config; Kaiko/X/Reddit/CryptoPanic đánh dấu chưa triển khai. Chưa có API key nào được đọc hoặc lưu.

Giả định/giới hạn: fixture API là giá hằng, phí/IL=0, gas chỉ mở vị thế; optimum chưa được tối ưu, stress chưa tính và tick để rỗng. Quy đổi WBTC/WETH sang USD cần giá WETH/USD theo thời điểm. MEV/JIT, trượt giá rebalance và thanh khoản nền biến thiên chưa mô hình hóa. Chưa thể khẳng định không look-ahead trong engine vì engine thật chưa tồn tại.

Phạm vi bước kế tiếp: port toán v3 và engine NumPy, test parity bằng cùng đường giá đầu vào với sai số <1e−6, sửa aggregation và xử lý range không khả thi, kiểm thử seed và các trường hợp biên. Dừng ở đây theo quy trình báo cáo sau mỗi bước của yêu cầu hiện tại.

# Báo cáo bước 4 — tích hợp dashboard/API

Ngày bàn giao: **21/10/2026 (UTC+7)**. Thư mục cài: `C:\Users\ADMIN\Downloads\uniswap`. Dashboard: <http://127.0.0.1:8000/>. API 0.4.0; model `stage4-observed-inputs-v2`. Phạm vi bước này là giao diện và nối dữ liệu đầu vào, chưa triển khai engine backtest của bước 5.

## Đã thực hiện

- Giữ màu, CSS và cấu trúc dashboard gốc; bổ sung bố cục responsive, trạng thái nguồn/loading/lỗi, data_asof, run_id và ghi chú giả định. KPI, P&L, sweep, đường giá, stress và bảng chiến lược đọc trực tiếp kết quả Python, không tính lại bằng JS khi API thành công.
- Gọi API cùng origin. Thay đổi input debounce 300 ms; AbortController hủy request cũ, revision guard loại kết quả đến trễ, timeout 20 giây. Input sai được báo tại giao diện. Trạng thái đang tính giải thích biểu đồ còn giữ kết quả trước.
- Danh sách **8 pool**: WETH/USDC, WETH/USDT, WBTC/WETH có fee 500/3000; USDC/USDT fee 100/500. Thêm realized vol 7/30 ngày, giá, TVL, volume, block/asof và nguồn dữ liệu.
- Đọc registry, lịch sử và ticks từ byte đã xác minh SHA256/source_log. Kiểm tra đơn vị raw/normalized L, giá theo decimals/thứ tự token và block snapshot. Registry tồn tại nhưng hỏng trả 503, không dùng preset giả bên trong API.
- Engine dùng p0 và active L đã quan sát, không suy L từ TVL. Bootstrap dùng volume đi cùng return. GBM/GARCH fit mean volume theo volatility regime trễ trên lịch sử trước asof; công bố fallback, các hệ số kịch bản và số mẫu trong meta.
- Tick chart dùng tick thật, L đã đổi đơn vị và interval đúng khi đảo thứ tự giá. Profile chỉ có trong cửa sổ ticks đã tải. Vị thế người dùng là overlay, không giả làm thanh khoản on-chain đã thực hiện.
- **Sao chép cấu hình** lưu engine/run_id/effective_config; có textarea khi clipboard bị chặn. Nạp cấu hình bằng run_id hoặc URL `/#run=<sha256>`, giữ cả tham số nâng cao không có control riêng, rồi tính lại với dữ liệu/phiên bản hiện tại. Run lưu gốc vẫn truy xuất qua API.
- Giữ **JS minh họa offline** khi mở HTML trực tiếp hoặc API lỗi. Gắn nhãn nguồn và lý do fallback, không giữ nhãn dữ liệu thật trên kết quả JS. Offline GBM giới hạn 300 đường và khai báo giới hạn này; không giả chạy GARCH/bootstrap offline. Có nút thử lại API.
- Tab Backtest có pool, ngày và chiến lược, gọi endpoint thật và báo rõ HTTP 501. Không tạo đường lịch sử từ kết quả Monte Carlo. Theme sáng/tối được lưu theo origin.

## Dữ liệu được nối

Snapshot block **26234741**, hash `0x00df570439888c84839a9a333cb06215907472f6c563b14551ecdd6c061f8d72`, timestamp **2026-10-20T15:37:59Z**. WETH/USDC 500 có p0 **2430.8415871251077 USDC/WETH**. Context TVL/volume/quote USD được tải riêng và ghi thời điểm khả dụng riêng; không coi tất cả trường có cùng timestamp block.

Lịch sử pool ngày: **364 dòng/pool**, close từ 2025-10-22 đến 2026-10-20. Số tick theo thứ tự 8 pool trong registry: **940, 167, 439, 167, 412, 155, 128, 37**. Đây là snapshot và lịch sử indexer công khai có giới hạn; không phải toàn bộ swaps/liquidity từ lúc pool tạo. Không tải lại dữ liệu trong bước 4. Chi tiết nguồn và phạm vi giữ trong báo cáo bước 3, coverage và source_log.

`calibration_asof` mặc định bằng thời điểm biết đầy đủ snapshot/context. API từ chối asof trước mốc này để tránh dùng current snapshot cho quá khứ. History và volume chỉ dùng timestamp trước asof. Các split train/validation/test chưa được dùng để tuyên bố kết quả ngoài mẫu trong bước này.

## Kiểm tra bàn giao

- **92 kiểm thử Python**: API, lưu/replay, v3/parity JS, chiến lược, edge cases, chia thời gian/no-look-ahead, ingestion/provenance; bổ sung quan sát, thay đổi TVL không thay L phí, dữ liệu sai hash/đơn vị, asof cũ, volume causal và thêm dữ liệu tương lai không đổi run.
- **2 chương trình kiểm thử Node** không cần npm: `frontend_flow.cjs` kiểm tra các giá trị trả từ API, tick, debounce, phản hồi đảo thứ tự, fallback/phục hồi, copy, infeasible, input lỗi, backtest 501 và nạp run_id; `offline_smoke.cjs` kiểm tra file:// không gọi API, biểu đồ, đổi path, sigma=0, clipboard fallback và theme.
- Kiểm tra HTTP trực tiếp trên bản cài: 8 pool GBM, bootstrap/GARCH, hash/provenance, replay, truy xuất run cũ và backtest 501. Bằng chứng máy đọc được: `uniswap-stage4-verification.json` trong gói bàn giao.
- Kiểm tra trình duyệt thật: nguồn quan sát, KPI/chart, mô hình nâng cao, trạng thái backtest và nạp cấu hình; ảnh chụp dashboard bàn giao kèm báo cáo. Không bổ sung thư viện phụ thuộc.

## Giới hạn cần giữ khi đọc kết quả

L tương lai được giữ bằng current active L theo mọi ngày/giá, chưa chạy LP nền theo profile tick hoặc lịch sử. Quote/USD giữ cố định, đặc biệt WBTC/WETH chưa có mô hình chung WETH/USD. Volume regime và innovation multiplier là mô hình đơn giản, chưa kiểm định ngoài mẫu. Gas do người dùng chọn; slippage là bps giả định; chưa có MEV/JIT, market impact hoặc crossing intraday. Không dùng APY/APR dựng sẵn để suy lợi nhuận.

Kết quả tối ưu chỉ là điểm khả thi có ΔR cao nhất trên lưới Monte Carlo, không bảo đảm hiệu suất thực tế. Bước 5 còn lại: backtest point-in-time, benchmark/ablation, panel/quantile regression, xuất bảng/hình và đánh giá tập test chưa dùng để chọn mô hình.

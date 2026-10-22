# Bàn giao bước 5 — historical replay, hồi quy và báo cáo

Ngày: **21/10/2026 (UTC+7)**. Dự án: `C:\Users\ADMIN\Downloads\uniswap`; dashboard <http://127.0.0.1:8000/>. API 0.5.0, historical engine `stage5-historical-replay-v2`.

## Kết quả triển khai

Endpoint backtest đã thay HTTP 501 bằng historical replay cho full, fixed, volatility-scaled, dynamic và optimizer. Kết quả có curve LP/HODL, phân rã phí–IL–gas–slippage, active share, drawdown, Sharpe/Sortino, số rebalance, gas hòa vốn, run_id và assumptions. Có CSV và JSON tải trực tiếp từ dashboard/API. Kết quả cũ của Monte Carlo vẫn đọc được.

Mỗi entry dùng volatility/mean volume từ timestamp trước entry. Optimizer chọn range bằng GBM trên thông tin quá khứ và cùng đường giả lập cho mọi width; không nhìn realized future return. Dynamic recenter sau khi đã quan sát close trước; không đặt range bằng close tương lai. Chi phí mở/đóng được tính một gas mỗi lần và hai gas/recenter. Nếu không có range khả thi, curve rỗng và trạng thái infeasible được giữ rõ.

Các phần nghiên cứu hoàn tất bằng dữ liệu hiện có:

| Nội dung | Quy mô |
|---|---:|
| Pool / chiến lược toàn kỳ | 8 / 5, tổng 40 run |
| Phạm vi chuẩn sau warmup | 22/11/2025–20/10/2026 |
| Cửa sổ 30 ngày / monthly strategy rows | 11 / 440 |
| Panel fixed width + dynamic | 440 dòng |
| Độ nhạy vốn × gas × min_gap × 3 quy tắc | 648 dòng |
| Robustness C / protocol fee / slippage / vol window / reference | 234 dòng |
| Gas hòa vốn dynamic so với static cùng width | 72 dòng |
| Bảng hệ số OLS + quantile | 57 dòng |
| File nghiên cứu công bố | 13 CSV, 8 PNG, 3 JSON, 1 báo cáo Markdown |

Research ID: `2cffb7795d463ca13906ef19d9fca43de2aef9c2e946294d9d14cec4c9e38c8e`. Manifest ghi hash input, code/config, versions và SHA256 từng file. Bản đầy đủ ở `outputs/research/<id>/`, báo cáo đọc nhanh ở `paper/research_report.md`. Chạy lại bằng `python manage.py research` hoặc `make research`.

## Phương pháp kinh tế lượng và diễn giải

Pool FE dùng vol/log mean volume trước entry, log width và policy dynamic dự kiến. Fee tier bất biến theo pool nên bị hấp thụ bởi pool FE; không trả một hệ số fee tier không được nhận diện. Mô hình pair FE riêng ước lượng liên hệ fee tier giữa các pool cùng cặp.

OLS dùng Driscoll–Kraay HAC, lag 2 và bậc tự do theo số kỳ. Quantile τ=0.1/0.5/0.9 dùng common-time circular block bootstrap 99 lần, block 2 kỳ; không dùng p-value IID. Số lần không hội tụ được ghi riêng trong diagnostics. ADF, Breusch–Pagan, VIF và condition number được xuất. Chỉ có 11 kỳ chung nên CI/p-value có tính thăm dò. Quan hệ với volume/fee có thể xuất hiện cơ học từ chính fee model; không xem các hệ số là quan hệ nhân quả hay ước lượng từ phí LP tái dựng.

So sánh optimizer−fixed trên 88 cặp pool–window dùng 999 circular time-block bootstrap, giữ pairing và lấy mẫu thời gian chung cho mọi pool. Trong mô hình C=3/gas=15, mean chênh lệch ΔR 30 ngày khoảng **+1,48 điểm phần trăm**, CI thăm dò **+0,94 đến +2,04 điểm phần trăm**. Đây là kết quả có điều kiện trên mô hình phí, không xác nhận hiệu quả đầu tư thực tế hoặc ngoài mẫu theo thiết kế gốc.

Sensitivity có cả fixed w=0.2 và static cùng width entry với dynamic; gas hòa vốn dùng chuẩn cùng width để tách tác động recenter. Threshold âm hoặc không có extra gas units được đánh dấu, không gọi là mức gas khả thi. Robustness cửa sổ vol 7/30/60 ngày dùng cùng thời kỳ để tránh đổi mẫu; không thay volume Uniswap bằng volume Binance.

## Giả định dữ liệu và phần chưa thể xác nhận

Giá/volume pool ngày quan sát từ 22/10/2025 đến 20/10/2026. **Không có pool price/volume train 2022–2023 hoặc validation 2024**, dù nguồn CEX tham chiếu/TVL có lịch sử dài hơn. Giữ split gốc, không chuyển ngày test sang train, không chọn hyperparameter trên outcome test. Trạng thái xác nhận OOS là `unavailable_missing_2022_2024_pool_calibration`.

Chưa có active liquidity/fee-growth lịch sử đầy đủ. Backtest dùng proxy `C×TVL_lag/(2×sqrt(P_previous_normalized)×quote_USD_ratio_previous)`, C=3 chưa hiệu chỉnh, robustness C=1/3/10. Không gán tick snapshot hiện tại cho lịch sử. TVL publication lag giả định 1 ngày, chỉ join trước quyết định, stale tối đa 7 ngày; không có archived publication vintage nên chỉ là event-time replay, chưa bảo đảm vintage point-in-time.

Phí ước tính từ volume pool và indicator trong range tại close, chưa tái dựng intraday crossing hoặc fee growth; giữ phí bằng USD cash. Protocol fee lịch sử chưa xác minh; haircut 25% là scenario. Gas phẳng và slippage bps giả định. Quote WETH/USDC có reference USD lịch sử, USDT/USD giả định bằng 1. Chưa mô hình hóa MEV/JIT, market impact hoặc ràng buộc tài trợ chi phí. Các giới hạn này có trong meta, UI, CSV và caption PNG.

The Graph chưa có key live, BigQuery không dùng; FRED chưa tải được trong bước 3; Kaiko/X/Reddit/CryptoPanic vẫn stub. Không tải thêm nguồn thị trường hoặc đưa dữ liệu tổng hợp vào kết quả nghiên cứu bước 5.

## Kiểm tra và vận hành

- **104 kiểm thử Python** đạt: parity v3/JS, seed, no-look-ahead, dữ liệu/hash, khoảng trống/warmup/TVL stale, USD quote exposure, protocol-fee scenario, negative wealth, optimizer infeasible, API replay/CSV và manifest whitelist/hash.
- **2 bộ kiểm tra Node** đạt: offline không gọi API; API/debounce/kết quả đến trễ, fallback, copy/restore, historical replay labels/charts, invalidation khi đổi input, infeasible, CSV/JSON và manifest nghiên cứu.
- Kiểm tra trực tiếp API và trình duyệt trên bản cài; kiểm tra curve trùng run lưu và tính lại, 8 pool/5 chiến lược, các file nghiên cứu theo SHA256. `pip check` đạt; 52 dependency versions được khóa trên Windows/Python 3.12.
- Dữ liệu nguồn được giữ nguyên; audit 1.082 payload quan sát hợp lệ. Không ghi đè `.env`, `.venv`, source data hoặc run cũ khi cập nhật code.

Nguồn phương pháp: [Uniswap v3 whitepaper](https://app.uniswap.org/whitepaper-v3.pdf), [statsmodels covariance](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html), [QuantReg](https://www.statsmodels.org/stable/generated/statsmodels.regression.quantile_regression.QuantReg.fit.html), [pandas merge_asof](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html), [Uniswap protocol fees](https://developers.uniswap.org/docs/protocols/protocol-fee/concepts/fees).

Công cụ mô phỏng nghiên cứu, không phải lời khuyên đầu tư.

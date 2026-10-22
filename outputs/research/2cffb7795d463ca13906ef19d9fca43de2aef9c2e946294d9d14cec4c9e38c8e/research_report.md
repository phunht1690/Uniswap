# Báo cáo nghiên cứu — historical replay có giả định

**Giá/volume lịch sử quan sát; phí LP ước tính từ TVL trễ. Không phải lợi nhuận LP thực tế đã tái dựng.**

Phạm vi sau warmup: 2025-11-22T00:00:00+00:00 → 2026-10-20T00:00:00+00:00; 8 pool. Có 440 dòng panel, 11 cửa sổ thời gian.

## Khả năng diễn giải

Dữ liệu pool giá/volume chỉ có từ cuối 2025. Không có tập hiệu chỉnh pool 2022–2024 nên chưa thể xác nhận optimizer ngoài mẫu theo thiết kế gốc. Các quy tắc và lưới được cố định trước khi tính lợi suất; không dùng lợi suất test để chọn hyperparameter. Các hồi quy dưới đây là mô tả trên historical replay có giả định, không phải thiết kế nhận diện nhân quả.

## Kết quả theo chiến lược

| Chiến lược | Median ΔR | Median phí | Median IL |
|---|---:|---:|---:|
| dynamic | 16.10% | 16.73% | 0.51% |
| fixed | 21.24% | 23.06% | 1.65% |
| full | 4.05% | 4.28% | 0.16% |
| optimizer | 16.26% | 16.89% | 0.46% |
| vol_scaled | 16.10% | 16.73% | 0.51% |

Các giá trị là trên vốn ban đầu cho toàn kỳ, không phải APR. So sánh giữa pool chịu ảnh hưởng mạnh từ giả định thanh khoản nền và protocol fee. Xem robustness.csv trước khi diễn giải dấu lợi nhuận.

## RQ và giả thuyết

- H1/RQ1: bảng strategy_returns và fee_decomposition tách fees, IL, gas, slippage; ΔR=fees−IL−gas−slippage. Chưa thể khẳng định lợi nhuận LP thực tế khi active L lịch sử thiếu.
- H2/RQ2: width_panel dùng 4 độ rộng cố định và cửa sổ 30 ngày không chồng lấn theo từng chiến lược. Đồ thị width_tradeoff mô tả phí/IL/active và Sharpe của ΔR theo cửa sổ; không dùng chọn tham số test.
- H3/RQ3: pool FE bỏ fee tier vì bất biến theo pool; mô hình pair FE riêng ước lượng liên hệ fee tier giữa các pool cùng cặp. Volatility/mean volume trễ trước entry; rebalance_policy là quy tắc dự kiến, không dùng số rebalance tương lai làm predictor. OLS dùng Driscoll–Kraay HAC; quantile 0.1/0.5/0.9 có time-block bootstrap. Số thời kỳ ít nên inference chỉ thăm dò.
- H4/RQ4: sensitivity so sánh vốn × gas × min_gap, cả fixed ±0.2 và static có cùng độ rộng ban đầu với dynamic. gas_break_even dùng static cùng độ rộng để tách chi phí recenter. Threshold âm nghĩa là dynamic đã kém static ngay khi gas bằng 0; không diễn giải như mức gas khả thi.
- H5/RQ5: optimizer dùng GBM và volume trước entry để chọn range theo ràng buộc, không nhìn giá tương lai; CI chênh lệch optimizer−fixed dùng circular block bootstrap theo cửa sổ chung cho mọi pool. Đây là bằng chứng có điều kiện trên fee model, chưa phải xác nhận OOS.

## Giả định và giới hạn

Active L proxy = C×TVL trễ/(2√P_norm×quote_USD_ratio), C=3 không hiệu chỉnh; kiểm tra C=1/3/10. TVL có publication lag giả định 1 ngày, join chỉ trước quyết định và giới hạn stale 7 ngày. Không dùng tick snapshot hiện tại cho quá khứ. Không có archived publication vintage nên chỉ kiểm soát event-time leakage, chưa bảo đảm data-vintage point-in-time.

Phí theo volume pool thực tế và trạng thái trong range tại close, không tái dựng crossing intraday hay fee-growth theo tick. Phí chuyển thành USD cash, không tái đầu tư. Protocol fee lịch sử chưa xác minh; sensitivity haircut 25% là kịch bản, không phải cấu hình quan sát. Gas phẳng; slippage bps; chưa có MEV/JIT hay market impact. USDT/USD giả định 1; WETH và USDC được định giá bằng reference lịch sử, không giữ current USD price ngược về quá khứ.

## Tái lập

`python manage.py research` sinh manifest có hash dữ liệu đầu vào, code, settings và phiên bản thư viện. Mỗi backtest API lưu config/result và run_id trong outputs/backtests. `/api/v1/runs/{id}` đọc lại; `/api/v1/backtests/{id}/curve.csv` xuất curve. Hình PNG và bảng CSV có cùng nhãn mô hình.

Nguồn phương pháp: [Uniswap v3 whitepaper](https://app.uniswap.org/whitepaper-v3.pdf), [statsmodels covariance](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html), [QuantReg](https://www.statsmodels.org/stable/generated/statsmodels.regression.quantile_regression.QuantReg.fit.html), [pandas merge_asof](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html), [protocol fee](https://developers.uniswap.org/docs/protocols/protocol-fee/concepts/fees).

Công cụ mô phỏng nghiên cứu, không phải lời khuyên đầu tư.

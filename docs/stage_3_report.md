# Bàn giao bước 3 — ingestion dữ liệu công khai

Đã cập nhật dự án `C:\Users\ADMIN\Downloads\uniswap`, không cần key, theo lựa chọn của người dùng. Tải toàn bộ trang công khai mà nguồn cho phép, lưu raw/Parquet/DuckDB, source log, checkpoint, lineage, coverage và kiểm tra hash. Không tuyên bố đã đủ toàn bộ lịch sử on-chain.

## Phạm vi thực tải

| Pool | Nến ngày / phạm vi | Nến giờ / khoảng trống | Ticks snapshot | Events trong cửa sổ mẫu |
| --- | --- | --- | --- | --- |
| WETH/USDC 0.05% | 364 / 2025-10-22 → 2026-10-20 | 4,999 / 0 | 940 | 1,591 |
| WETH/USDC 0.3% | 364 / 2025-10-22 → 2026-10-20 | 4,995 / 18 | 167 | 170 |
| WETH/USDT 0.05% | 364 / 2025-10-22 → 2026-10-20 | 4,999 / 0 | 439 | 1,248 |
| WETH/USDT 0.3% | 364 / 2025-10-22 → 2026-10-20 | 4,999 / 0 | 167 | 587 |
| WBTC/WETH 0.05% | 364 / 2025-10-22 → 2026-10-20 | 4,999 / 0 | 412 | 371 |
| WBTC/WETH 0.3% | 364 / 2025-10-22 → 2026-10-20 | 3,865 / 1569 | 155 | 22 |
| USDC/USDT 0.01% | 364 / 2025-10-22 → 2026-10-20 | 4,999 / 0 | 128 | 441 |
| USDC/USDT 0.05% | 364 / 2025-10-22 → 2026-10-20 | 3,306 / 2133 | 37 | 2 |

| Nguồn / dataset | Dòng | Phạm vi / trạng thái |
| --- | --- | --- |
| binance / reference_ethusdt_1d | 3,351 | 2017-08-18 → 2026-10-20 / complete_available |
| binance / reference_ethusdt_1h | 80,307 | 2017-08-17 → 2026-10-20 / complete_available |
| binance / reference_btcusdt_1d | 3,351 | 2017-08-18 → 2026-10-20 / complete_available |
| binance / reference_btcusdt_1h | 80,307 | 2017-08-17 → 2026-10-20 / complete_available |
| binance / reference_ethusdc_1d | 2,703 | 2018-12-16 → 2026-10-20 / complete_available |
| binance / reference_ethusdc_1h | 64,797 | 2018-12-15 → 2026-10-20 / complete_available |
| binance / reference_usdcusdt_1d | 2,701 | 2018-12-16 → 2026-10-20 / complete_available |
| binance / reference_usdcusdt_1h | 64,741 | 2018-12-15 → 2026-10-20 / complete_available |
| binance / reference_ethbtc_1d | 3,385 | 2017-07-15 → 2026-10-20 / complete_available |
| binance / reference_ethbtc_1h | 81,123 | 2017-07-14 → 2026-10-20 / complete_available |
| defillama / pool_context | 8 | — → — / observed |
| defillama / tvl_weth-usdc-500 | 1,641 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_weth-usdc-3000 | 1,641 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_weth-usdt-500 | 1,661 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_weth-usdt-3000 | 1,661 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_wbtc-weth-500 | 1,661 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_wbtc-weth-3000 | 1,661 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_usdc-usdt-100 | 1,641 | 2022-03-27 → 2026-10-20 / complete_available |
| defillama / tvl_usdc-usdt-500 | 1,641 | 2022-03-27 → 2026-10-20 / complete_available |
| coingecko / usd_reference_ethereum | 366 | 2025-10-21 → 2026-10-20 / provider_limited |
| coingecko / usd_reference_bitcoin | 366 | 2025-10-21 → 2026-10-20 / provider_limited |
| coingecko / usd_reference_usd-coin | 366 | 2025-10-21 → 2026-10-20 / provider_limited |
| coingecko / usd_reference_tether | 366 | 2025-10-21 → 2026-10-20 / provider_limited |
| fred / macro_dff | 0 | — → — / unavailable |
| fred / macro_cpiaucsl | 0 | — → — / unavailable |
| fred / macro_dtwexbgs | 0 | — → — / unavailable |

RPC snapshot: block **26234741**, hash `0x00df570439888c84839a9a333cb06215907472f6c563b14551ecdd6c061f8d72`, thời gian **2026-10-20T15:37:59+00:00**. TVL/volume/quote USD của aggregator có thời gian context riêng trong registry, không giả định cùng block RPC.

## Kiểm tra và cách dùng

- Hash/cấu trúc: **1,082 payload hiện tại**, không có hash thiếu hoặc dataset giá/thời gian sai trong audit.
- 84 kiểm thử Python đạt trên môi trường dự án, gồm parity JS <1e−6, no-look-ahead, cache/retry/redaction/checkpoint, nến đóng, decimals/đảo giá, raw integers và quy đổi liquidity theo USD. Kiểm tra JS offline và pip check đạt.
- `GET /api/v1/data/status` trả coverage/quality. `python manage.py data` hoặc `make data` cập nhật public sources; `python manage.py mock-data` chỉ sinh fixture minh họa.
- `docs/ingestion.md` hướng dẫn tải từng nguồn, backfill theo block, cache và giới hạn. `docs/data_dictionary.md` mô tả trường/đơn vị/thời gian. `data/coverage.csv` tiện xem độ phủ từng dataset.
- `data/source_log.csv` ghi nguồn/endpoint, UTC tải, khoảng thời gian, số dòng và SHA256; raw được lưu theo request/content hash, Parquet cũ giữ trong `_versions/`. Không lưu key thật hoặc thay dữ liệu thiếu bằng số giả.

## Phần còn thiếu và giả định

- Chưa đủ swaps/mints/burns từ ngày pool ra đời. Event chỉ đủ cửa sổ 2.000 block đã nêu trong coverage, có cursor để tải tiếp. Tick là snapshot quanh giá, gas là base fee một block; chưa có lịch sử active liquidity hoặc gas USD.
- Public RPC đã trả lỗi yêu cầu personal token khi đọc state cũ. Downloader lấy toàn bộ ticks sớm ở một block finalized mới trước khi tải OHLCV chậm; không gán snapshot hiện tại ngược về lịch sử.
- OHLCV công khai bị giới hạn lịch sử; các trang cũ bị HTTP 401 được giữ làm bằng chứng. Đã phân trang bình thường và dừng ở ranh giới quyền truy cập; không mượn key. Khoảng trống nến được giữ, không fill. Các lỗi rate limit còn lại nếu có được ghi rõ trong status/stop_reason.
- FRED timeout trong lần tải này nên các series macro chưa có dữ liệu. Adapter giữ latest-vintage là descriptive-only để tránh dùng số sửa lại làm thông tin đã biết trong quá khứ. DTWEXBGS không phải ICE DXY.
- The Graph optional adapter đã có, chưa chạy live vì không có key. BigQuery không sử dụng. Kaiko/X/Reddit/CryptoPanic vẫn là stub explicit.
- Binance là tham chiếu CEX; CoinGecko volume toàn thị trường không phải volume pool. Dữ liệu xử lý DefiLlama không có APY/APR. Quote/USD snapshot dùng để đổi đơn vị current L, chưa là chuỗi USD point-in-time cho WBTC/WETH.
- Chưa đủ pool history để train 2022–2023, validate 2024 và test đầy đủ 2025–2026. Split cố định vẫn giữ nguyên; bước này chưa chọn/tune tham số, chưa backtest/hồi quy và chưa kết luận hiệu quả tài chính.

## Điểm dừng theo yêu cầu

Dừng ở bước 3. Dashboard và `/pools`/GBM vẫn giữ preset/JS minh họa có nhãn; chưa tự nối dữ liệu mới vào các biểu đồ hoặc thay thanh khoản nền trong mô phỏng. Bước 4 sẽ nối registry/inputs/ticks với engine và frontend, xử lý loading/error/fallback/copy config. Bước 5 mới backtest/hồi quy/đánh giá ngoài mẫu. Dashboard vẫn chạy tại http://127.0.0.1:8000/.

Nguồn kỹ thuật chính thức và mô tả giới hạn nằm trong `docs/ingestion.md`. Bộ dữ liệu raw thực tải là bằng chứng cho độ phủ nêu trên. Công cụ mô phỏng nghiên cứu, không phải lời khuyên đầu tư.

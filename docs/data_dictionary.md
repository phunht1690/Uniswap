# Từ điển dữ liệu — bước 4 và hợp đồng mô phỏng

`/pools` và Monte Carlo dùng registry quan sát đã kiểm tra hash, có `data_kind=observed_snapshot`. Khi không có registry, API dùng fixture có nhãn `illustrative`; khi registry tồn tại nhưng hỏng, API trả lỗi, không thay bằng fixture. Frontend offline hoặc gặp lỗi API dùng JS minh họa với nhãn riêng. Lịch sử tổng hợp chỉ nằm trong kiểm thử.

| Trường pool | Đơn vị / ý nghĩa |
| --- | --- |
| id | Mã nội bộ `{base}-{quote}-{fee_tier}`, chưa phải địa chỉ hợp đồng |
| base, quote | Cặp chuẩn hóa; p0 luôn là quote/base |
| fee_tier | Phần triệu: 500 = 0,05%; 3000 = 0,3% |
| fee_rate | Tỷ lệ: 0.0005 = 0,05% |
| p0 | Quote token cho một base token; WBTC/WETH = WETH/WBTC, không phải USD |
| tvl_usd, volume_24h_usd | USD tại context snapshot; TVL không phải active L |
| vol_assumption_annual | Mặc định GBM bằng vol 30d quan sát; null nếu không đủ lịch sử. Người dùng có thể đổi kịch bản |
| vol_realized_7d, vol_realized_30d | Sample std log returns ×sqrt(365), cần 8/31 giá ngày liên tiếp trước available_at, không fill gap |
| data_kind | `observed_snapshot` hoặc `illustrative` |
| data_asof | Thời gian UTC của block RPC; không phải thời gian context aggregator |
| available_at | Max(block timestamp, metadata available_at, context_available_at); không dùng snapshot trước mốc này |
| address, block_number | Pool contract trên Ethereum và block snapshot |
| quote_usd | USD/quote tại context snapshot, giữ cố định trong mô phỏng |
| background_liquidity_normalized_usd | Current active raw L đổi sang đơn vị USD ban đầu tại normalized P=1 |
| history_start, history_end | Timestamp close đầu/cuối lịch sử pool trước available_at; null nếu chưa có |
| sources, warnings | Nguồn cung cấp và phần dữ liệu thiếu; không tự thay vol thiếu bằng số quan sát giả |

| Trường mô phỏng | Đơn vị / ý nghĩa |
| --- | --- |
| capital, gas_usd | USD |
| half_width | Nửa độ rộng log: PL=P0·exp(−w), PU=P0·exp(w); không phải phần trăm số học |
| p_low, p_high, sample_paths | Giá tuyệt đối quote/base; full range là p0×[1e−9,1e9] để khớp JS |
| fees, il, gas, net, excess_vs_hodl, q5 | Tỷ lệ trên vốn ban đầu, không phải USD hoặc % đã nhân 100 |
| net | Tổng lợi suất LP sau chi phí; ΔR = net − lợi suất HODL |
| il | Chi phí so với HODL: (HODL − giá trị LP chưa phí)/vốn; tránh trừ IL hai lần |
| q5 | Phân vị 5% của ΔR, khác CVaR trung bình đuôi 5% |
| cvar5 | Trung bình ceil(5%×N) terminal ΔR thấp nhất |
| active_share | Tỷ lệ thời gian trong khoảng; khác 1−xác suất từng rời khoảng |
| exit_prob | Tỷ lệ đường từng rời khoảng trong kỳ |
| pnl_path.lp, pnl_path.hodl | Lợi suất tích lũy trên vốn ban đầu |
| stress.* | Cú sốc ±30% trên range tối ưu, giữ phí kỳ vọng cố định; rỗng nếu không có range khả thi |
| liquidity_ticks | `{tick,price,liquidity}`; price quote/base, liquidity đơn vị engine; tăng theo raw tick, chưa chắc tăng theo price |
| rebalance_count | Số lần recenter trung bình, tối đa max_rebalances trên mỗi đường |
| rebalance_cost | Chi phí slippage giả định / vốn, tách khỏi gas và IL |
| feasible | exit_prob ≤ risk_max_exit_prob trên kịch bản Monte Carlo |
| optimum | Null nếu không điểm nào trên lưới khả thi; không chọn fallback vi phạm |
| meta.run_id | SHA256(config+seed+snapshot hash+provenance+settings+model_version+phiên bản thư viện số) |
| meta.engine_status | `numpy_simulation` cho run mới; trạng thái mock được giữ để đọc run bước 1 |
| meta.optimization_status | `feasible` hoặc `infeasible` cho run mới |
| calibration_asof | Mốc UTC; chỉ dùng dữ liệu có timestamp nhỏ hơn mốc |
| bootstrap_mean_block_days | Độ dài khối kỳ vọng của stationary bootstrap; xác suất restart=1/block_days |
| meta.assumptions.effective_config | Cấu hình thực tế sau khi giải calibration_asof; dùng cho copy/replay |
| meta.assumptions.market_snapshot | Registry/tick hash, provenance, block/hash, available_at/context_available_at |
| meta.assumptions.volume_method | Cách fit volume, số mẫu, cutpoints, mean từng regime, lag và các hệ số kịch bản |
| meta.assumptions.background_liquidity | Nguồn/đơn vị L và tuyên bố giữ cố định theo giá/thời gian tương lai |

`net` bao gồm biến động inventory, phí và chi phí; không đồng nghĩa ΔR. `active_share`/`exit_prob` không chia cho vốn. P&L ngày 0 của LP đã trừ gas mở; HODL ngày 0 bằng 0. Xác suất exit chỉ quan sát theo ngày, không đo crossing giữa hai mốc. Q5 là sorted[ floor(N×0.05) ], không nội suy.

Lịch sử chuẩn hóa cho bootstrap/GARCH: Parquet `history_<pool>.parquet` với timestamp UTC, price quote/base, volume_usd. File được xác minh qua hash source_log trước khi đọc. Không backfill, không bỏ qua ngày trống. Hash run dựa trên các dòng trước asof; thêm/sửa các dòng tương lai với provenance cùng nguồn không đổi run trước mốc đó.

| source_log.csv | Ý nghĩa |
| --- | --- |
| source, endpoint | `local_mock`, `local://supplied-html-pool-presets` cho file cục bộ |
| downloaded_at_utc | Thời điểm sinh/tải file; UTC, không phải data_asof |
| period_start, period_end | Để trống với preset không có thời gian quan sát |
| row_count | Số dòng pool, hiện 4 |
| file_path | Đường dẫn tương đối trong thư mục trạng thái |
| sha256 | SHA256 byte của file đã lưu |
| data_kind | Nhãn phân biệt minh họa và dữ liệu thật |

Engine chuẩn hóa p0=1 và L theo giá trị USD ban đầu; không cắm raw L trực tiếp vào mẫu số phí. WBTC/WETH giữ quote/USD cố định, chưa mô phỏng WETH/USD chung. Chế độ quan sát dùng L từ snapshot thay cho TVL×CONC/2. Tick chart vẽ interval giữa hai raw tick kế tiếp: L của tick i áp dụng phía phải theo raw tick, kể cả khi trục price bị đảo. Phạm vi tick tải có giới hạn; không ngoại suy profile ra ngoài cửa sổ đã tải. L nền trong fee model vẫn giữ current active L cố định, chưa di chuyển theo profile tick hoặc mô hình hóa LP khác.

Volume GBM/GARCH: feature vol 30d trễ một ngày, yêu cầu cửa sổ ngày liên tiếp; fit cutpoints 1/3, 2/3 và mean volume trong 180 ngày trước asof. Mean từng regime cần 10 mẫu, nếu thiếu dùng mean 30 ngày (thiếu lịch sử dùng volume 24h quan sát). Nhân `min(3, abs(innovation)/(0.8*daily_sd))`; sigma=0 dùng hệ số 1. Bootstrap giữ cặp return/volume đã lấy mẫu. Đây là mô hình volume có điều kiện đơn giản, chưa được xác thực ngoài mẫu.

Tab backtest gọi endpoint v1, trả `returns_unit="fraction_of_initial_capital"`, `equity_curve=[{timestamp,lp,hodl,...}]`, `summary`, `meta`. Nhãn riêng `historical_replay_modelled_fees`: giá/volume lịch sử quan sát, phí ước tính bằng mô hình TVL trễ. Frontend không dùng Monte Carlo để điền vào biểu đồ backtest. Nếu optimizer không có range khả thi, `status=infeasible`, summary null và curve rỗng.

## Historical replay và kết quả nghiên cứu bước 5

| Trường | Ý nghĩa |
|---|---|
| start, end | UTC close dates; entry ở close start, lợi suất của các bar (start,end] |
| requested_start/end, effective_start/end | Khoảng yêu cầu và phần dữ liệu thật sau warmup; partial_period công bố việc giới hạn phạm vi |
| feature_asof | Giá cuối dùng ước lượng vol/mean volume, phải < entry timestamp |
| tvl_timestamp, tvl_available_at, decision_time | Timestamp TVL; available_at=timestamp+1 ngày giả định; join backward strict trước decision_time, không quá stale 7 ngày |
| original_publication_vintages_verified | False: không có archived release vintage; kiểm soát event-time, không chứng nhận vintage PIT |
| concentration | C của proxy L; mặc định 3, chưa hiệu chỉnh; kiểm tra C=1/3/10 |
| background L proxy | C×TVL_lag/(2√P_previous_normalized×quote_USD_ratio_previous); cùng đơn vị với L vị thế, không gọi là active L đã quan sát |
| protocol_fee_fraction | Fraction phí swap chuyển khỏi LP; kịch bản mặc định 0 và robustness 0.25, chưa xác minh lịch sử governance từng pool |
| quote_usd | USDT=1 giả định; USDCUSDT/ETHUSDT reference tại close cho quote USDC/WETH; không dùng current quote/USD ngược quá khứ |
| curve.lp, hodl | Lợi suất tích lũy / vốn ban đầu, không phải wealth index hoặc APR |
| curve.fees, il, gas, rebalance_cost | Thành phần tích lũy / vốn; ΔR=fees−IL−gas−rebalance_cost |
| curve.price, p_low, p_high | Giá quote/base và range áp dụng tại close đó |
| curve.rebalance_count | Số recenter đã thực hiện; gas mở 1, đóng 1, mỗi recenter 2 giao dịch giả định |
| sharpe_lp_daily, sortino_lp_daily | Từ simple wealth returns ngày, annualized sqrt(365), rf=0; chi phí mở tính vào kỳ đầu; null nếu variance/downside=0 hoặc wealth không dương |
| max_drawdown | Min(wealth/running_peak−1), có baseline vốn ban đầu; có thể thấp hơn −1 khi mô hình cash-cost không áp ràng buộc khả năng tài trợ |
| q5_daily_excess_increment, cvar5_daily_excess_increment | Đuôi của thay đổi ΔR ngày, không phải phân phối terminal Monte Carlo Q5 |
| monthly_risk_summary q5/cvar5_terminal_30d_excess | Đuôi của terminal ΔR qua các cửa sổ 30 ngày quan sát; 11 kỳ/pool, không phải Monte Carlo |
| break_even_gas_vs_hodl_usd | (fees−IL−slippage)×capital/gas_units; threshold âm không có mức gas dương hòa vốn |
| gas_break_even.csv | Dynamic so với static cùng độ rộng entry, chỉ thay gas; threshold=chênh USD trước gas / extra_gas_units khi extra>0 |
| panel.vol_annual, log_volume_usd | Vol từ giá trước entry; log1p(mean volume USD quá khứ); không dùng volume tương lai để chọn range/hồi quy |
| panel.width, log_width | Half width log và ln(width); rebalance_policy là indicator quy tắc dynamic được chọn trước kỳ |
| regressions z_* | Predictor đã chuẩn hóa theo SD của mẫu mô tả; hệ số là ΔR/fraction khi predictor tăng 1 SD; mean/SD lưu trong diagnostics |
| pool_FE_DK | OLS pool fixed effects, bỏ fee_bps vì bất biến theo pool; covariance Driscoll–Kraay HAC maxlag=2, df theo số kỳ |
| pair_FE_fee_DK | OLS asset-pair FE để ước lượng liên hệ fee tier giữa pool cùng cặp; không diễn giải nhân quả |
| quantile_0.1/0.5/0.9_pool_FE | QuantReg, CI/SE từ 99 circular common-time block bootstrap, block 2 kỳ; p_value để trống, số fit không hội tụ lưu diagnostics |
| optimizer_paired_bootstrap | CI mean optimizer−fixed trên 30-day windows; bootstrap chung kỳ theo block=2 để giữ pairing và tương quan các pool, 999 lần seed 42 |
| research_id | Hash version/spec/settings/input snapshots/code hashes/numerical versions; manifest gồm SHA256 của từng file xuất |

Các bảng/hình đều có nhãn phí mô hình, không phải phí LP tái dựng. Tham số fixed/lưới/cửa sổ được khai báo trước, chưa chọn theo kết quả test. Train/validation pool price/volume 2022–2024 có 0 dòng; do đó trạng thái `confirmatory_oos_status=unavailable_missing_2022_2024_pool_calibration`. Hồi quy thăm dò trên 2025–2026 không được gọi là xác nhận ngoài mẫu. File derived outputs có hash/manifest; nguồn thị trường giữ nhật ký ở source_log.

## Dataset ingestion quan sát

| Dataset / trường | Đơn vị, thời gian, nguồn |
| --- | --- |
| onchain_pool_snapshot / id, address | ID nội bộ và hợp đồng pool do Uniswap v3 Factory trả về, chainId=1 |
| base_address, quote_address, token0, token1 | Địa chỉ hợp đồng, lowercase; không suy thứ tự từ tên ticker |
| decimals0, decimals1 | `decimals()` của token contract tại cùng block finalized |
| fee_tier, fee_rate | Phần triệu và tỷ lệ; xác minh bằng `fee()` của pool |
| sqrt_price_x96 | Raw uint160 dạng chuỗi; P_raw=(sqrtPriceX96/2^96)^2 là token1_raw/token0_raw |
| p0, inverted | p0 luôn quote/base human units; P_human=P_raw×10^(decimals0−decimals1), đảo nếu base=token1 |
| tick, liquidity_raw | int24 và uint128 hiện tại; liquidity nguyên dạng chuỗi, không mất chính xác float |
| block_number, block_hash, data_asof | Block finalized và timestamp UTC của block; cùng snapshot không pha trộn nhiều block |
| available_at | UTC lúc đọc metadata; không được coi dataset đã biết trước mốc này |
| pool_registry.json | Snapshot kết hợp RPC với context aggregator, có timestamp từng nguồn; không phải lịch sử |
| context_<pool> / tvl_usd, volume_24h_usd, quote_usd | USD, rolling 24h volume, giá USD của quote; snapshot GeckoTerminal lúc tải |
| defillama_pool_context / defillama_id | Pool key khớp Ethereum/uniswap-v3/token contracts/fee tier; không dùng APY |
| tvl_<pool> / timestamp, tvl_usd | TVL lịch sử theo timestamp do DefiLlama trả; không phải liquidity active L |
| ticks_<pool> / tick, price | Tick initialized trong cửa sổ ±5.000 tick quanh current tick; price quote/base |
| liquidity_net_raw, liquidity_gross_raw | int128/uint128 nguyên dạng chuỗi, từ `ticks(int24)` |
| ticks / liquidity_raw | Active raw L ngay bên phải tick theo thứ tự tick gốc. Khi đảo giá, phía phải theo tick là phía giá thấp hơn |
| liquidity_normalized_usd | L đổi về đơn vị engine với initial normalized P=1 bằng quote/USD snapshot; không phải TVL, không dùng ngược cho lịch sử |
| background_liquidity_normalized_usd | Anchor L hiện tại đã đổi đơn vị từ `liquidity()`; giữ cùng block với pool metadata |
| history_<pool>, hourly_<pool> / period_start | UTC mở kỳ thực tế của aggregator; không fill kỳ không có giao dịch |
| timestamp | UTC cuối kỳ, đại diện thời điểm nến đóng; chỉ lưu nến đã đóng |
| open, high, low, price | Quote/base; price là close, token được yêu cầu bằng địa chỉ base contract |
| volume_usd | Volume **pool** của cùng kỳ, lấy từ OHLCV `currency=usd` riêng, không giả định stablecoin=1 USD |
| source, dataset_kind | `geckoterminal`, `onchain_aggregator`; là ước lượng của indexer công khai, chưa xác minh từng swap toàn kỳ |
| features_<pool> / vol_realized_7d, vol_realized_30d | Độ lệch chuẩn mẫu log return ×sqrt(365), dùng dữ liệu tới kỳ trước; null qua khoảng trống |
| mean_volume_7d_usd, mean_volume_30d_usd | Trung bình volume pool USD trễ một kỳ; chưa là mô hình volume có điều kiện |
| reference_<symbol>_<1d/1h> | Binance CEX: timestamp cuối kỳ; open/high/low/price theo quote của symbol |
| volume_base, volume_quote, trade_count | Đơn vị token base, quote và số giao dịch CEX; không gắn nhãn USD hoặc volume Uniswap |
| usd_reference_<coin> / price_usd | Giá USD CoinGecko tại timestamp UTC; điểm intraday cuối không coi là close ngày |
| aggregate_market_volume_usd | Volume thị trường tổng hợp CoinGecko, không phải pool hoặc chỉ một sàn |
| events_<pool> / event | `swap`, `mint`, `burn`, chỉ trong cửa sổ block khai báo |
| transaction_hash, log_index, block_number, block_hash | Khóa (tx hash, log index), vị trí/khối finalized; loại removed logs và trùng |
| data_raw, topics_raw | ABI hex nguyên bản để kiểm chứng; không dùng float để lưu lượng nguyên |
| amount0_raw, amount1_raw, liquidity_raw | Chuỗi số nguyên chính xác; swap amount có dấu theo delta của pool, mint/burn là lượng dương |
| amount0, amount1, amount_base, amount_quote | Human token units phụ trợ từ decimals; không quy USD lịch sử bằng giá quote/USD hiện tại |
| tick_lower, tick_upper | Bounds mint/burn; tick sau swap nằm ở `tick` |
| price_quote_per_base | Giá sau swap từ sqrtPriceX96, có decimals và đảo token đúng |
| gas_block_snapshot / base_fee_gwei | Base fee của một block, Gwei; không phải gas USD hay giá giao dịch thực tế |
| graph_* | Adapter optional lưu entity ID, raw số dạng chuỗi và snapshot_block; day/hour có giá từ sqrtPrice, timestamp cuối kỳ. Chưa tải live |
| macro_* / value, series | FRED: DFF %/năm; CPIAUCSL index; DTWEXBGS broad USD index, không phải ICE DXY |
| vintage, predictive_eligible | Latest revised vintage, false; ngày quan sát không bảo đảm ngày công bố. Không dùng trong predictive backtest chưa có release/vintage |

Với sqrtP0_raw = sqrtPriceX96/2^96 và U = quote/USD tại snapshot, hệ số đổi raw L thành L_engine là sqrtP0_raw×U/10^decimals1 khi base=token0; U/(sqrtP0_raw×10^decimals0) khi base=token1. Đã kiểm thử bằng giá trị USD của vị thế raw đối chiếu vị thế normalized. Đây vẫn là một snapshot L, chưa mô hình hóa thanh khoản nền thay đổi theo thời gian/giá.

`coverage.json/csv`: source, dataset, status, rows, start/end quan sát, missing_intervals, note; event có requested_start_block/requested_end_block/next_block. `complete_available` là toàn bộ trang nguồn trả trong lần tải, vẫn có thể có ngày trống. `provider_limited` không chứng nhận đủ lịch sử pool. `credentials_unavailable`, `unavailable`, `not_implemented` phân biệt thiếu quyền, lỗi tải và stub. `quality_report.json` ghi kiểm tra hash/thời gian/giá; `lineage.json` nối processed → raw; hash của các phiên bản cũ được giữ trong `_versions/`. Xem [quy trình ingestion](ingestion.md).

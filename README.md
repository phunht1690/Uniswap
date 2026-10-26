# RangeLab — Uniswap LP Research Simulator

RangeLab là web mô phỏng việc cung cấp thanh khoản trên Uniswap v3. Bạn có thể xem thị trường, tìm khoảng giá, so sánh LP với giữ token, thử tình huống rủi ro và thử chiến lược với dữ liệu quá khứ. Giao diện và API Python chạy cùng một máy chủ. Ứng dụng không kết nối ví hay gửi giao dịch.

Giao diện có hiệu ứng ngắn khi đổi tab, vẽ biểu đồ và nhận số liệu mới. Giá trị thật luôn xuất hiện ngay; các lần kiểm tra API không có số mới sẽ không làm số liệu nhấp nháy. Hiệu ứng tự tắt khi thiết bị bật **Giảm chuyển động**.

Xem [hướng dẫn sử dụng hiện tại](docs/dashboard_user_guide.md) và [đối chiếu bài luận với dashboard ngày 26/10/2026](docs/thesis_alignment_audit.md) để hiểu cấu hình, quy tắc và phạm vi bằng chứng. [Tài liệu Word về chức năng, dữ liệu và mô hình](docs/dashboard_giai_thich_chuc_nang_du_lieu_mo_hinh.docx) cùng [bản đọc trực tiếp](docs/dashboard_explained_vi.md) là bản **22/10/2026**, chưa mô tả các preset mới; đọc kèm bản đối chiếu ngày 26/10/2026. Bài luận Word gốc không được sửa bởi cập nhật dashboard này.

## Mở web trên máy hiện tại

Dự án đang nằm tại `C:\Users\ADMIN\Downloads\uniswap` và đã có môi trường `.venv`. Mở PowerShell rồi chạy:

```powershell
Set-Location -LiteralPath 'C:\Users\ADMIN\Downloads\uniswap'
.\run.cmd
```

Khi terminal hiện `Uvicorn running on http://127.0.0.1:8000`, mở **[http://127.0.0.1:8000](http://127.0.0.1:8000)**. Nếu máy chủ đã chạy, chỉ cần mở địa chỉ này. Giữ cửa sổ terminal mở trong lúc sử dụng; nhấn **Ctrl+C** trong terminal để dừng máy chủ.

Bạn cũng có thể nhấp đúp `run.cmd` trong File Explorer. Chạy từ PowerShell sẽ dễ đọc thông báo nếu có lỗi. Một lệnh trên phục vụ cả giao diện web và API.

## Cài lần đầu từ bản ZIP hoặc mã nguồn

### Windows PowerShell

1. Giải nén dự án vào một thư mục có quyền ghi. Đi vào thư mục chứa `manage.py`, `run.cmd` và `requirements.txt`.
2. Cài Python **3.11 trở lên**; bản đã kiểm tra dùng **Python 3.12**. Kiểm tra và tạo môi trường cho dự án:

```powershell
Set-Location -LiteralPath 'C:\Users\ADMIN\Downloads\uniswap'
py -3.12 --version
py -3.12 -m venv .venv
```

3. Cài thư viện. Với Windows/Python 3.12, dùng danh sách phiên bản đã kiểm tra:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock-windows-py312.txt
```

Nếu dùng Python 3.11 hoặc phiên bản khác được thư viện hỗ trợ, dùng `requirements.txt` thay cho file khóa ở trên. Nếu máy không có lệnh `py`, thay `py -3.12` bằng `python` hoặc đường dẫn Python của bạn, sau khi xác nhận phiên bản đủ mới. Nếu đã có `.venv` hoạt động, giữ môi trường đó và bỏ qua bước tạo lại.

4. Khởi động:

```powershell
.\run.cmd
```

5. Mở **[dashboard](http://127.0.0.1:8000/)** trong trình duyệt. Mở **[tài liệu API](http://127.0.0.1:8000/docs)** khi cần xem các endpoint.

Các lệnh dùng trực tiếp Python trong `.venv`, nên không cần kích hoạt môi trường hoặc đổi execution policy của PowerShell. Bản ZIP không chứa `.venv`; môi trường này phải được tạo trên máy sử dụng.

### macOS/Linux

Trong thư mục dự án đã giải nén:

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python manage.py run
```

Mở cùng địa chỉ **http://127.0.0.1:8000/** và dừng bằng **Ctrl+C**. Python cần từ 3.11 trở lên. Nếu `venv` chưa có trên bản Linux đang dùng, cài thành phần venv tương ứng qua trình quản lý gói của hệ điều hành rồi tạo lại môi trường.

### Những gì đã có sẵn

Giao diện đã build, CSS và font được lưu cục bộ. **Không cần Node.js để mở web.** Bản ZIP đầy đủ có dữ liệu nghiên cứu tại `data/` và các kết quả mẫu. Không cần chạy tải dữ liệu hay kiểm thử trước mỗi lần mở web.

Internet cần cho lần cài thư viện và cho chế độ theo dõi thị trường mới. Nguồn công khai mặc định không yêu cầu API key.

## Bắt đầu sử dụng dashboard

1. **Tổng quan:** tìm cặp token, chọn mức phí và bấm **Phân tích**. Cùng một cặp nhưng khác mức phí là các pool khác nhau.
2. **Tìm khoảng giá LP:** nhập vốn, số ngày, mức chấp nhận rủi ro và các giả định; bấm **Chạy tối ưu hóa RangeLab**.
3. **Kết quả tối ưu hóa:** đọc khoảng giá, phí, lợi nhuận ròng và chênh lệch với giữ token. Có thể tải PDF/JSON hoặc sao chép liên kết kết quả.
4. **Kiểm tra rủi ro & dữ liệu:** thử tình huống giá, dao động và phí mạng; phân tích độ nhạy; xem nguồn và cách tính. Sau khi chỉnh thanh trượt, bấm **Chạy kiểm tra rủi ro** để cập nhật biểu đồ.
5. **Thử chiến lược trong quá khứ:** chọn bộ cấu hình, pool và khoảng ngày, rồi chạy so sánh trên cùng dữ liệu và tải CSV. Màn hình mới mặc định **Tái lập quy tắc nghiên cứu**; cấu hình và kết quả đã lưu vẫn giữ quy tắc của chúng. Nếu thiếu ngày, dùng khoảng liên tục được gợi ý.

Nút **Thuật ngữ** giải thích các từ và chỉ số trong dashboard, kèm ví dụ. Nút **ⓘ Thông tin** giới thiệu mục đích, quy trình và cách đọc kết quả. Xem thêm [hướng dẫn sử dụng đầy đủ](docs/dashboard_user_guide.md) và [ma trận tính năng/API](docs/rangelab_integration.md).

## Chọn đúng cấu hình khi so sánh quá khứ

Comparison mới dùng `rangelab-comparison-v2`, có trường `strategy_mode` để phân biệt hai quy tắc. Giao diện gọi `GET /api/v1/backtests/presets` và mặc định chọn preset nghiên cứu khi chưa có cấu hình lưu. Mỗi preset đặt vốn 50.000 USD, gas 15 USD/đơn vị, seed 42, hệ số thanh khoản 3, trượt giá 0 và tối đa 52 lần dời khoảng; người dùng vẫn có thể sửa thành cấu hình tùy chỉnh.

| Tham số hoặc chiến lược | Tái lập quy tắc nghiên cứu | Biến thể hằng tuần của giao diện cũ |
| --- | --- | --- |
| `strategy_mode` | `research` | `weekly` |
| Fixed `half_width` | 0,20 log | 0,15 log |
| Cửa sổ biến động | 30 ngày | 14 ngày |
| `dynamic` | Giữ độ rộng tại entry; dời tâm sau quan sát giá ra ngoài khoảng | Giữ độ rộng tại entry; xét dời tâm hằng tuần |
| `vol_scaled` | Giữ độ rộng và khoảng tính từ biến động tại entry | Cập nhật độ rộng và tâm hằng tuần từ biến động rolling trễ |

Giao diện so sánh **năm nhóm LP, gồm optimizer, cùng HODL**. Đổi preset hoặc tham số chưa làm thay đổi kết quả đang xem cho đến khi chạy lại. Bảng cấu hình của kết quả, nhãn chiến lược và CSV ghi quy tắc của chính lần chạy đó; không đổi nhãn một kết quả cũ theo lựa chọn hiện tại.

Để tương thích client cũ, API `POST /api/v1/backtests/compare` **không gửi `strategy_mode`** vẫn dùng `weekly` và các mặc định schema 0,15/14. Muốn quy tắc nghiên cứu qua API phải gửi rõ `strategy_mode='research'`, `half_width=0.20`, `volatility_window_days=30` và các tham số cần khớp khác. `strategies` của API vẫn hỗ trợ danh sách tường minh; thêm `optimizer` khi cần so với bộ tối ưu. Các bản ghi comparison v1 được đọc lại nguyên vẹn và nhận diện là quy tắc weekly; run mới có phiên bản v2 và danh tính riêng.

Preset khớp quy tắc không bảo đảm khớp số đã công bố: cần cùng pool, kỳ thực tế, dữ liệu/hash, chi phí và phiên bản nghiên cứu. Xem [bảng đối chiếu và kiểm tra số liệu gốc](docs/thesis_alignment_audit.md).

## Tin tức & cộng đồng

Mở **Tin tức & cộng đồng** trong menu hoặc trong **Kiểm tra rủi ro & dữ liệu**. Không cần chạy mô phỏng trước. Chọn pool để lọc bài liên quan đến token của cặp; chọn nguồn hoặc xem thông tin chung của hệ sinh thái Uniswap. Nhãn v3/v4 giúp phân biệt phiên bản được nhắc đến, không khẳng định tin áp dụng trực tiếp cho vị thế v3 đang mô phỏng.

- **Đã nối nguồn công khai:** Uniswap Labs Blog và diễn đàn quản trị Uniswap. Máy chủ kiểm tra mỗi **5 phút**, dùng chung bộ nhớ đệm cho mọi người xem. Giao diện đọc bộ nhớ đệm mỗi 30 giây khi mục tin tức đang mở. Hiển thị tối đa 100 tiêu đề trong 90 ngày gần nhất; đây không phải luồng sự kiện tức thời hay toàn bộ lịch sử bài đăng.
- **Đọc thời gian:** ngày đăng do nguồn cung cấp khác với lần lấy tin thành công. Khi nguồn lỗi, giữ tin lần trước và ghi rõ trạng thái trễ/lỗi. Đề xuất trên diễn đàn là thảo luận cộng đồng, không đồng nghĩa đã được biểu quyết hoặc triển khai.
- **Liên quan đến pool:** nhãn token chỉ cho biết bài có nhắc tới token hoặc tên tương ứng; chỉ gắn nhãn địa chỉ pool khi tìm thấy đúng địa chỉ. Tin tức không được dùng làm đầu vào tự động cho PnL, stress hay tối ưu hóa.

API `GET /api/v1/news?pool=weth-usdc-500` cung cấp bản tin và trạng thái nguồn; giao diện chỉ hiển thị Uniswap Labs Blog và diễn đàn quản trị Uniswap. Trình duyệt đọc bộ nhớ đệm trên máy chủ. Đặt `UNISWAP_NEWS_ENABLED=0` trước khi chạy để tắt kiểm tra tin. Nếu không đặt biến này, `UNISWAP_LIVE_ENABLED=0` cũng tắt tin tức.

## Dữ liệu thị trường mới và kết quả đã lưu

- **Thị trường đang theo dõi:** giá và thanh khoản được kiểm tra mỗi **30 giây**; TVL, khối lượng 24 giờ và giá quy đổi USD mỗi **300 giây**. Giao diện đọc trạng thái mỗi 30 giây khi tab hoạt động. Đây là cập nhật gần thời gian thực theo chu kỳ, có độ trễ của nguồn.
- **Thời điểm dữ liệu:** giờ của block khác với giờ lấy dữ liệu thành công. TVL/khối lượng có mốc lấy riêng; vừa kiểm tra không có nghĩa mọi số liệu tại nguồn đều mới. Trạng thái mới/trễ/lỗi được hiển thị riêng.
- **Mô phỏng mới:** mặc định chọn **Dữ liệu thị trường mới**. Khi bấm chạy, hệ thống chụp giá, thanh khoản và thông tin pool thành một bộ đầu vào cố định, cùng bản lịch sử hiệu chỉnh đã lưu. Thiếu dữ liệu mới hoặc thanh khoản hoạt động thì báo lý do.
- **Kết quả đã lưu:** giá mới không tự sửa kết quả cũ. Stress và độ nhạy dùng đúng đầu vào đã lưu của kết quả đang xem. Muốn dùng thời điểm khác, tạo mô phỏng mới.
- **Dữ liệu nghiên cứu:** lịch sử và biến động được tính từ bộ dữ liệu đã thu thập. Worker thị trường không tự tải lại toàn bộ lịch sử hay cập nhật kết quả backtest theo mỗi lần kiểm tra giá.

Ứng dụng hỗ trợ **14 pool**: 11 Ethereum và 3 ARB/WETH trên Arbitrum. Phạm vi lịch sử khác nhau giữa các pool. Giá/volume quan sát không đồng nghĩa đã tái dựng chính xác phí của một vị thế NFT theo từng giao dịch. Kết quả backtest hiện mang tính mô tả, chưa xác nhận hiệu quả ngoài mẫu.

## Chạy với dữ liệu đã lưu khi không có mạng

Sau khi đã cài thư viện và có bộ dữ liệu nghiên cứu, có thể tắt bộ theo dõi thị trường trước khi khởi động. Windows PowerShell:

```powershell
$env:UNISWAP_LIVE_ENABLED = '0'
.\run.cmd
```

Trong màn hình **Tìm khoảng giá LP**, bỏ chọn **Dữ liệu thị trường mới** để dùng bộ nghiên cứu đã lưu. Các kết quả đã lưu vẫn có thể xem lại. Muốn bật cập nhật, dừng máy chủ, đặt `$env:UNISWAP_LIVE_ENABLED = '1'`, rồi chạy lại. macOS/Linux dùng `UNISWAP_LIVE_ENABLED=0 ./.venv/bin/python manage.py run`.

Mở trực tiếp `dashboard/index.html` là **dashboard gốc chạy JavaScript minh họa**, khác với RangeLab chạy bằng Python qua địa chỉ web. Bản gốc cũng có tại `/legacy` và `/dashboard/`.

## Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Không tìm thấy `.venv\Scripts\python.exe` | Làm phần cài lần đầu; bản ZIP không chứa môi trường Python. |
| `py` không được nhận diện hoặc thiếu Python 3.12 | Dùng Python 3.11+ đang có sau khi kiểm tra phiên bản, hoặc cài Python 3.12 rồi tạo `.venv`. |
| Thiếu thư viện / `ModuleNotFoundError` | Cài lại requirements bằng **Python trong `.venv`**, không dùng pip của môi trường khác. |
| Không mở được `127.0.0.1:8000` | Kiểm tra terminal còn chạy và đã hiện dòng `Uvicorn running...`; đọc lỗi xuất hiện trước đó. |
| Cổng 8000 đã được dùng | Nếu là dashboard đã chạy, mở trình duyệt để dùng bản đó. Nếu là ứng dụng khác, dùng lệnh cổng thay thế bên dưới. |
| Nguồn giá hoặc TVL báo trễ/lỗi | Đọc thời điểm thành công gần nhất; đợi chu kỳ tiếp theo. Có thể chủ động bỏ chọn dữ liệu mới để mô phỏng bằng bộ nghiên cứu. |
| Chưa có dữ liệu nghiên cứu hoặc hash không khớp | Dừng máy chủ, chạy bộ thu thập ở phần tiếp theo, kiểm tra thông báo và khởi động lại. Không tự đổi sang dữ liệu giả trong API. |
| Không có khoảng giá đáp ứng giới hạn rủi ro | Đây là kết quả mô hình, không phải lỗi mở web. Xem lại thời gian, giới hạn rủi ro và độ rộng được thử. |

Chạy cổng khác khi cần:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn api.main:app --host 127.0.0.1 --port 8002
```

Sau đó mở **http://127.0.0.1:8002/**. Trong một phiên sử dụng, nên giữ cùng địa chỉ truy cập vì cấu hình trình duyệt được lưu theo địa chỉ và cổng.

Biến môi trường tùy chọn: `ETHEREUM_RPC_URL`, `ARBITRUM_RPC_URL`, `UNISWAP_LIVE_ENABLED` và `UNISWAP_STATE_DIR`. Web chạy qua `run.cmd`/`manage.py run` tự nạp file `.env` tại thư mục dự án; biến môi trường của tiến trình được ưu tiên. Nếu cần thay đổi cấu hình hoặc khóa, sửa `.env` rồi khởi động lại máy chủ. Không cần cấu hình các key tùy chọn chỉ để dùng nguồn công khai mặc định.

## Tải hoặc cập nhật dữ liệu nghiên cứu — khi cần

Các lệnh sau khác với worker thị trường mới. Chạy bằng Python trong `.venv` ở thư mục dự án:

```powershell
# Tải/cập nhật bộ nghiên cứu công khai; có thể mất vài phút.
.\.venv\Scripts\python.exe -X utf8 manage.py data

# Chỉ bổ sung các pool chưa có; không làm mới snapshot của pool đã có.
.\.venv\Scripts\python.exe -X utf8 manage.py extend-pools

# Nối nến giá tham chiếu ngày đã đóng; không thay thế giá pool live.
.\.venv\Scripts\python.exe -X utf8 manage.py refresh-references
```

Chạy từng downloader nghiên cứu một và khởi động lại máy chủ sau khi cập nhật registry. Coverage ghi rõ nguồn không truy cập được, phạm vi và ngày thiếu. Xem [trạng thái dữ liệu](http://127.0.0.1:8000/api/v1/data/status), `data/coverage.json` và [chi tiết thu thập](docs/ingestion.md). `manage.py mock-data` chỉ sinh dữ liệu minh họa; không dùng để thay bộ nghiên cứu quan sát.

## Sửa giao diện hoặc chạy kiểm thử — dành cho phát triển

Chỉ cần Node **20.18.1+** khi build giao diện hoặc chạy các kiểm thử JavaScript. Tại thư mục dự án:

```powershell
npm ci --prefix frontend
npm run build --prefix frontend
```

Các template thiết kế gốc nằm ở `frontend/templates`; JavaScript kết nối API nằm trong `frontend/`. Build tạo các trang và tài nguyên cục bộ tại `dashboard/rangelab/`, có mã phiên bản để trình duyệt tải bản mới.

Kiểm thử tùy chọn, không phải bước bắt buộc để mở web:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
node --test tests/stress_view.cjs tests/motion.cjs
node tests/frontend_flow.cjs dashboard/index.html
node tests/offline_smoke.cjs dashboard/index.html
```

Bộ kiểm thử parity với JavaScript cần Node; kiểm thử tự động dùng dữ liệu cô lập, không tự tải thị trường thật.

## Dashboard gốc: hành vi riêng

Dashboard tại `/legacy` hoặc `dashboard/index.html` có debounce 300 ms, sao chép/khôi phục cấu hình JSON và hash `#run=`. Khi mở trực tiếp file, nó chạy minh họa offline. Khi mở qua HTTP, có thể chuyển sang minh họa có nhãn nếu API lỗi và dùng **Thử lại API** để kết nối lại. Các cơ chế này thuộc dashboard gốc; RangeLab dùng nút chạy và đường dẫn kết quả `/optimization-results?run_id=...`.


## API v1

### Các endpoint của giao diện RangeLab

| Route | Chức năng |
|---|---|
| POST /api/v1/workbench/run | Tối ưu theo cấu hình; có thể chỉ định `market_snapshot_id` cho dữ liệu thị trường đã chụp |
| GET /api/v1/workbench/runs/{run_id} | Xem cấu hình và kết quả RangeLab đã lưu |
| POST /api/v1/workbench/stress | Chạy tình huống rủi ro trên bộ đầu vào của kết quả gốc |
| POST /api/v1/workbench/sensitivity | Thử nhiều mức biến động giá và tối ưu lại từng mức |
| GET /api/v1/backtests/presets | Hai preset research/weekly, tham số và phiên bản comparison |
| POST /api/v1/backtests/compare | So sánh chiến lược với `strategy_mode`, cấu hình hiệu lực và quy tắc từng chuỗi |
| GET /api/v1/research/reconciliation | Đối chiếu archive đã kiểm tra hash: H4, phân rã từng hàng và bootstrap optimizer−fixed |
| GET /api/v1/backtests/comparisons/{run_id}/export.csv | Tải chi tiết backtest |

Kết quả RangeLab nằm ở `outputs/workbench/`; các bản đầu vào thị trường đã chụp nằm ở `outputs/market_snapshots/`. Trường `run_id` của RangeLab dùng endpoint `/workbench/runs/{run_id}`, không dùng endpoint `/runs/{run_id}` của engine gốc.

### Ví dụ tái lập một lần chạy workbench

Giao diện tối ưu hóa dùng body có `config` lồng bên trong. Ví dụ sau dùng dữ liệu nghiên cứu đã lưu; nó không tạo snapshot thị trường mới và không tái lập đồng thời báo cáo 8 pool hoặc comparison lịch sử:

```powershell
$config = @{pool='weth-usdc-500'; capital=50000; horizon_days=60; vol_annual=0.65; gas_usd=15; risk_max_exit_prob=0.4; min_rebalance_gap_days=7; price_model='gbm'; n_paths=300; seed=42; path_index=0}
$request = @{
    config = $config
    rebalance_policy = 'none'
    delta_threshold = 0.1
    volume_daily_override_usd = $null
    market_snapshot_id = $null
}
$run = Invoke-RestMethod -Method Post `
    -Uri 'http://127.0.0.1:8000/api/v1/workbench/run' `
    -ContentType 'application/json' -Body ($request | ConvertTo-Json -Depth 20)
$saved = Invoke-RestMethod -Uri ('http://127.0.0.1:8000/api/v1/workbench/runs/' + $run.meta.run_id)
$replay = Invoke-RestMethod -Method Post `
    -Uri 'http://127.0.0.1:8000/api/v1/workbench/run' `
    -ContentType 'application/json' -Body ($saved.config | ConvertTo-Json -Depth 20)
$run.meta.run_id -eq $saved.result.meta.run_id -and $run.meta.run_id -eq $replay.meta.run_id
```

Kết quả workbench dùng `rangelab-workbench-v3` và lưu trong `outputs/workbench/`. Gửi lại nguyên cấu hình hiệu lực đã lưu, cùng snapshot, dữ liệu và môi trường số để kiểm tra cùng `run_id`. Nếu dùng thị trường mới, chụp snapshot một lần và gửi lại đúng `market_snapshot_id`; không tạo snapshot mới cho lần tái lập.

### Dữ liệu chung và API legacy của engine gốc

| Route | Trạng thái bước 5 |
| --- | --- |
| GET /api/v1/health | Stage 5, trạng thái registry quan sát; degraded nếu dữ liệu lỗi |
| GET /api/v1/data/status | Coverage từng nguồn/dataset và kết quả kiểm tra hash/thời gian/giá |
| GET /api/v1/pools | 14 pool trong bộ nghiên cứu đã lưu, giá/TVL/volume/vol/asof; thiếu registry mới dùng 4 fixture có nhãn |
| GET /api/v1/market/live | Giá/active-L theo block mới và TVL/volume có thời điểm/trạng thái riêng; đọc cache tức thì |
| POST /api/v1/market/snapshot | Chụp đầu vào thị trường mới và lịch sử hiệu chỉnh thành bản bất biến cho mô phỏng |
| POST /api/v1/simulate | **Legacy:** mô phỏng NumPy của engine gốc, không thay cho workbench; bootstrap/GARCH cần lịch sử và calibration_asof |
| GET /api/v1/runs/{run_id} | **Legacy:** đọc config + result của engine gốc hoặc historical replay, không đọc run workbench |
| GET /api/v1/backtest/{pool}?start&end&strategy | Historical replay với giá/volume quan sát và phí mô hình từ TVL trễ |
| GET /api/v1/backtests/{run_id}/curve.csv | Curve CSV có nhãn và run_id |
| GET /api/v1/research/status | Manifest CSV/PNG, phạm vi và giới hạn nghiên cứu |
| GET /api/v1/research/files/{name} | Tải file nằm trong manifest, xác minh SHA256 |

Input **legacy** `/simulate`: `pool`, `capital`, `horizon_days`, `vol_annual`, `gas_usd`, `risk_max_exit_prob`, `min_rebalance_gap_days`, `price_model`, `n_paths`, `seed`, `path_index`. Ví dụ `pool="weth-usdc-500"`, `vol_annual=0.65` nghĩa là 65%/năm. Giới hạn: horizon 1–365, n_paths 1–5000, n_paths×horizon≤1.000.000. Sai schema trả 422; pool/asof sai trả 400, run không tồn tại trả 404, dữ liệu quan sát thiếu/hỏng trả 503, phạm vi backtest không đủ trả 400. Dashboard gọi API cùng origin. CORS bổ sung chỉ cho localhost cổng 3000/5173.

Tham số bổ sung: `max_rebalances` (mặc định 52), `rebalance_slippage_bps` (0), `min_half_width` (0.005), `max_half_width` (null → tự tính), `bootstrap_mean_block_days` (10), `calibration_asof` (ISO 8601 có múi giờ). Vốn từ 1 đến 100 triệu USD. API tính lợi suất theo tỷ lệ vốn: 0.01 = 1%, không phải 0.01 USD.

Không đọc/ghi được cache trả 503 kèm thông báo quyền thư mục; có thể trỏ UNISWAP_STATE_DIR tới thư mục được phép ghi rồi khởi động lại. Việc ghi run dùng file tạm riêng và rename nguyên tử.

`optimum=null`, `meta.optimization_status="infeasible"` và thông báo rõ nếu không điểm nào trên lưới thỏa ngưỡng rủi ro. Không trả range vi phạm như một nghiệm tối ưu. Khi đó `pnl_path`/`stress` rỗng và bảng chỉ có bốn chiến lược cơ sở. Ngưỡng rủi ro là xác suất rời range từng ghi nhận tại các mốc ngày trên tập Monte Carlo, chưa phải bảo đảm ngoài mẫu.



Với **legacy `/simulate`**, run được lưu tại `outputs/runs/<sha256>.json`. Hash bao gồm cấu hình chuẩn hóa, registry/tick hash, snapshot lịch sử trước asof, provenance, YAML settings, model_version và phiên bản thư viện số; không gồm thời gian chạy. Phiên bản engine legacy là `stage4-observed-inputs-v2`; đây không phải phiên bản của workbench hoặc comparison. Cùng config/seed/dữ liệu/settings/phiên bản cho cùng run_id và result, kể cả khởi động lại. Thay code mô hình phải tăng model_version. Đổi `path_index` cũng đổi run_id. Thêm dữ liệu sau calibration_asof không đổi snapshot lịch sử/hash trước mốc đó khi registry/ticks/settings không đổi. Run cũ vẫn đọc được; muốn tái tính phiên bản cũ cần giữ code/config/data tương ứng. Có thể đặt `UNISWAP_STATE_DIR` để chuyển vị trí data và outputs.

Trong chế độ quan sát, thiếu `calibration_asof` được giải thành mốc muộn nhất giữa thời gian block, thời gian tải metadata và context. Không cho đặt asof sớm hơn thời điểm biết snapshot hiện tại. Đây là dự báo có điều kiện trên snapshot đã tải, chưa phải backtest lịch sử.

## Engine và kiểm thử nghiên cứu

- `v3.py`: giá trị vị thế theo ba vùng giá, liquidity từ vốn/range, tick ↔ price có decimals và đảo token. Dùng expm1 để tránh mất chính xác khi range rất hẹp. Full range giữ biên chuẩn hóa hữu hạn 1e−9..1e9 của JS; range rất rộng hội tụ về CPMM v2.
- `price_models.py`: GBM μ=0, seed PCG64; stationary block bootstrap trên cặp log return–volume; GARCH(1,1) ước lượng bằng `arch`, sau đó mô phỏng bằng NumPy có seed riêng. Python và JS dùng PRNG khác nhau; parity dùng **cùng đường giá/innovation đầu vào**, không yêu cầu cùng seed tạo cùng đường giữa hai ngôn ngữ.
- `strategies.py`: full, fixed log ±0.2, volatility-scaled 1.5σ√T và dynamic recenter. Phí không tái đầu tư; một gas mở, hai gas/recenter, chưa tính gas đóng. `min_gap` ngăn hai lần recenter quá gần; lần đầu có thể xảy ra ngày 1, giống JS. Recenter sau khi tính phí của bar; range mới sinh phí từ bar sau. Slippage là bps × giá trị inventory được dời, ghi riêng vào cash cost. Không áp ràng buộc khả năng tài trợ khi gas lớn, nên tổng wealth có thể âm.
- Optimizer dùng chung đường giá cho mọi range/chiến lược. Lưới log 20 điểm từ min_half_width đến max_half_width; mặc định max = max(0.5, 4σ√T), thay lưới cũ quá hẹp. Chỉ chọn điểm khả thi có ΔR kỳ vọng cao nhất. Đây là tối ưu trong kịch bản mô phỏng; kiểm chứng ngoài mẫu còn thiếu dữ liệu hiệu chỉnh pool.
- `fees.py`: quan sát dùng current raw L đã quy đổi đúng đơn vị engine, **không suy L từ TVL**. Giữ L này cố định theo thời gian và giá tương lai; tick chart là profile snapshot, chưa dùng tick tương lai để thay L nền. Bootstrap lấy cặp return–volume lịch sử. GBM/GARCH hiệu chỉnh ba mức volume theo volatility trễ một kỳ trên 180 ngày trước asof (tối thiểu 10 mẫu/mức), fallback mean 30 ngày hoặc volume 24h quan sát nếu thiếu lịch sử. Hệ số innovation, cap 3 và scale 0.8 vẫn là giả định kịch bản được ghi trong meta. σ=0 dùng mean của regime. Chế độ fixture/offline giữ giả định TVL×CONC/2 có nhãn.
- `evaluation/metrics.py` tổng hợp fees, IL, gas, slippage, net, ΔR, Q5, CVaR5, active, exit và số rebalance. Workbench có phòng hộ dùng ΔR = (inventory + fees − gas − slippage + hedge_pnl − HODL)/capital. Tương đương ΔR = (fees − IL_loss − gas − slippage + hedge_pnl)/capital với IL_loss = HODL − inventory là khoản thiếu hụt theo quy ước dương. Không phòng hộ có hedge_pnl = 0; không trừ IL hai lần khỏi inventory. Q5 theo order statistic floor(N×0.05), CVaR lấy trung bình ceil(N×0.05) kết quả xấu nhất.
- `features/point_in_time.py` dùng rolling features trễ một kỳ, snapshot chỉ lấy timestamp < calibration_asof, không backfill. Hàm tuning chỉ trả train+validation 2022–2024, loại test 2025–2026.

Bootstrap/GARCH qua API yêu cầu `data/processed/history_<pool>.parquet` gồm `timestamp` (UTC), `price` (quote/base), `volume_usd`; giá ngày liên tiếp, không trùng, không thiếu, giá dương và volume không âm. File phải có SHA256 khớp `data/source_log.csv`. Bootstrap cần ≥31 quan sát giá; GARCH ≥101 và lợi suất không hằng. Thiếu lịch sử/asof hoặc fit không hội tụ trả 400 có lý do, không tự chuyển sang dữ liệu giả. Bộ tải bước 3 đã cung cấp lịch sử theo phạm vi aggregator cho phép; nguồn có ngày trống có thể chưa đủ điều kiện chạy mô hình ngày. Các unit test lịch sử dùng dữ liệu tổng hợp trong thư mục tạm có nhãn.

Với bootstrap/GARCH, volatility dùng chọn S3/lưới là ước lượng trước asof; `vol_annual` điều khiển GBM. Giá p0 và L nền lấy snapshot đã xác minh. Giữ quote/USD tại snapshot cho mọi pool; riêng WBTC/WETH điều này giữ WETH/USD cố định, chưa phải mô hình chung hai tài sản theo USD. Stress ±30% của engine legacy giữ phí kỳ vọng không đổi. Stress workbench dùng log bridge có giá cuối kỳ cố định, chạy lại policy và tính phí theo thời gian trong khoảng, nhưng giữ volume trung bình và active-L cố định; không mô hình hóa phản ứng thị trường đầy đủ với cú sốc.

## Dữ liệu toàn bộ lịch sử

Theo yêu cầu, `config/sources.yaml` đặt `mode: all_available`, start null, end `latest_available`. Downloader đã tìm đầu/cuối nguồn thực tế, phân trang và cache. Binance lấy toàn bộ ngày/giờ nguồn trả; lịch sử pool công khai có giới hạn riêng. RPC mặc định chỉ lấy mẫu 2.000 block finalized và ticks quanh current tick, có CLI để backfill tiếp. Chưa có toàn bộ swaps/mint/burn hoặc liquidity lịch sử từ khi pool tạo. Không tự bật dịch vụ cloud tính phí. Xem `docs/ingestion.md` để chạy theo nguồn hoặc theo khoảng block.

Dữ liệu dùng hiệu chỉnh và kiểm tra vẫn tách cố định trong `config/research.yaml`: train 2022–2023, validation 2024, test 2025 đến bản ghi mới nhất khả dụng trong 2026; dữ liệu sớm hơn dùng warmup. Unit test đã kiểm tra việc loại test khỏi tuning và loại dữ liệu tại/sau asof. Chưa có xác nhận ngoài mẫu theo thiết kế gốc; historical replay bước 5 là phân tích mô tả có giả định.

Key được đặt ở môi trường chạy, không gửi vào chat. Ví dụ:

```powershell
$env:THE_GRAPH_API_KEY = '<your-key>'
$env:UNISWAP_SUBGRAPH_ID = '<subgraph-id>'
```

`.env.example` liệt kê biến tùy chọn; `.env` nằm trong `.gitignore`. Web tự nạp `.env` khi startup; CLI ingestion đọc biến môi trường của process, không tự nạp `.env`. Chế độ tải công khai hiện tại không dùng Graph/BigQuery/key. Adapter The Graph tùy chọn cần key của bạn và đã kiểm thử bằng fixture, chưa xác minh live trong phiên không có key.

## Cấu trúc và phạm vi tiếp theo

```text
api/{main.py,schemas.py,routes/}
config/{pools.yaml,sources.yaml,research.yaml}
data/{raw/,interim/,processed/,source_log.csv}
dashboard/index.html
docs/{data_dictionary.md,requirements_decisions.md,stage_1_report.md,stage_2_report.md}
src/{data/,features/,models/,evaluation/,utils/}
tests/
outputs/{runs/,tables/,figures/}
notebooks/
paper/
```

1. **Đã triển khai:** repo, config, API contract mock, phục vụ dashboard gốc, lưu run, Parquet/DuckDB fixture, source log, kiểm thử API.
2. **Đã triển khai:** engine NumPy, v3/JS parity, GBM/bootstrap/GARCH, optimizer có trạng thái khả thi và tests no-look-ahead.
3. **Đã triển khai nguồn công khai, có giới hạn độ phủ:** Binance/CoinGecko, DefiLlama, Ethereum RPC, GeckoTerminal, FRED tùy chọn; source log/hash, Parquet/DuckDB, checkpoint, quality/coverage. Tin tức công khai đọc riêng từ Uniswap Labs Blog và diễn đàn quản trị, không đưa vào tập dữ liệu mô phỏng. The Graph có adapter optional chưa chạy live; BigQuery không dùng. Các bản tin không tham gia mô hình hay tập dữ liệu nghiên cứu. Adapter ingestion Kaiko vẫn chưa triển khai. Full raw on-chain history vẫn thiếu.
4. **Đã triển khai:** frontend API/debounce/loading/error, 8 pool quan sát, tick thật, copy/nạp cấu hình theo run_id và JS fallback có nhãn.
5. **Đã triển khai công cụ:** historical replay, panel/quantile regression, bootstrap theo thời gian, sensitivity/robustness và xuất CSV/PNG. **Chưa thể xác nhận OOS theo thiết kế gốc** vì thiếu pool price/volume 2022–2024 và active liquidity/gas lịch sử. Không coi kết quả có giả định là phí LP thực tế.

Các giả định và chỗ khác nhau giữa tài liệu được ghi ở `docs/requirements_decisions.md`; đơn vị dữ liệu ở `docs/data_dictionary.md`. Không áp công thức LVR σ²/8 của CPMM cho thanh khoản tập trung. Các giới hạn cần xử lý/công bố: MEV/JIT, trượt giá rebalance, gas lịch sử, thanh khoản nền thay đổi, tick trong từng khoảng và quy đổi WBTC/WETH sang USD point-in-time.

Kiểm thử bước 2 bao phủ parity toán và cashflow so với JS gốc với sai số tuyệt đối <1e−6, seed, no-look-ahead, chia thời gian, edge cases, API và provenance. Chưa có kết quả kiểm định tài chính trên dữ liệu thật. Một cảnh báo deprecation TestClient/httpx từ Starlette không ảnh hưởng kết quả kiểm thử.

Chạy `node tests/offline_smoke.cjs dashboard/index.html` và `node tests/frontend_flow.cjs dashboard/index.html` để kiểm tra offline và luồng API (giá trị trả về, debounce, phản hồi đến trễ, lỗi/phục hồi, copy, infeasible, historical replay, tải kết quả và nạp run_id), không cần cài package npm.

Đã sửa lỗi gốc: không chia active/exit cho vốn, không gọi range vi phạm là optimum, tách net LP return khỏi ΔR, và xử lý σ=0. `tests/fixtures/original_math.js` giữ nguyên các hàm gốc, có hash nguồn ở `reference_provenance.json`, để đối chiếu mà không kế thừa lỗi aggregation. Không dùng các số minh họa hiện tại làm kết luận nghiên cứu.

Nguồn kỹ thuật: [Uniswap LiquidityAmounts](https://github.com/Uniswap/v3-periphery/blob/main/contracts/libraries/LiquidityAmounts.sol), [arch forecasting](https://arch.readthedocs.io/en/stable/univariate/forecasting.html). Chi tiết định nghĩa và độ lệch so với HTML được ghi trong báo cáo bước 2.


## Historical replay và nghiên cứu bước 5

```powershell
.\.venv\Scripts\python.exe manage.py research
# hoặc trên macOS/Linux: make research
```

Lệnh đọc dữ liệu đã ghi nguồn, không cần key và không tải thêm mạng. Kết quả ở `outputs/research/<research_id>/`; `outputs/research/latest.json` là manifest có SHA256 từng CSV/PNG/JSON/Markdown, hash code/config/input và phiên bản thư viện. Các file có thể tải từ tab **Dữ liệu & Phương pháp → Kết quả nghiên cứu lưu trữ & hồi quy**. Lệnh không chọn hyperparameter theo kết quả test. Một lần chạy đầy đủ có thể mất vài phút.

Backtest API nhận thêm: `capital`, `gas_usd`, `half_width` (fixed), `min_rebalance_gap_days`, `max_rebalances`, `rebalance_slippage_bps`, `risk_max_exit_prob`, `concentration` (mặc định 3), `protocol_fee_fraction` (mặc định 0, chỉ là kịch bản), `volatility_window_days` (30), `price_source=pool|reference`, `allow_partial=true`, `seed` (42). Không dùng volatility slider GBM cho lịch sử: ước lượng từ dữ liệu trước entry.

Ví dụ:

```powershell
$url = 'http://127.0.0.1:8000/api/v1/backtest/weth-usdc-500?start=2025-11-22&end=2026-10-20&strategy=dynamic&capital=50000&gas_usd=15'
$backtest = Invoke-RestMethod $url
$record = Invoke-RestMethod ('http://127.0.0.1:8000/api/v1/runs/' + $backtest.meta.run_id)
# CSV: /api/v1/backtests/<run_id>/curve.csv
```

`start` và `end` là UTC close dates. Entry thực hiện ở close start; feature dùng timestamp **< start**, các kỳ lợi suất là (start, end]. Cần window+1 giá ngày trước start. Nếu allow_partial=true, API ghi rõ requested/effective period khi thiếu dữ liệu hoặc warmup; false trả lỗi. Không fill ngày trống hoặc dùng TVL quá cũ. `status=infeasible` trả curve rỗng, không thay bằng range vi phạm. Kết quả có `returns_unit=fraction_of_initial_capital`, `equity_curve`, `summary`, `meta` và được lưu tại `outputs/backtests/`. `/runs/{id}` đọc được cả Monte Carlo lẫn historical replay. Cùng config/dữ liệu/settings/version cho cùng ID; khác loại run có namespace/hash riêng.

Fee model lịch sử là **ước tính**, không dùng current ticks/active L ngược về quá khứ:

- L nền = C × TVL trễ / (2 × sqrt(previous normalized price) × previous quote/USD ratio). C=3 là giả định chưa hiệu chỉnh, kiểm tra C=1/3/10.
- TVL được giả định công bố sau timestamp 1 ngày, chỉ join trước quyết định và không quá stale 7 ngày. Không có archived release vintage nên đây là kiểm soát **event-time**, chưa chứng nhận thông tin thực sự đã công bố tại thời điểm đó.
- Volume là volume pool của bar lịch sử; fee allocation dùng trạng thái trong range tại close. Chưa tái dựng intraday crossing hoặc fee-growth. Phí giữ bằng USD cash, không reinvest; protocol fee lịch sử chưa xác minh, có sensitivity haircut 25%.
- WETH/USD và USDC/USD dùng Binance ETHUSDT/USDCUSDT tại cùng close; USDT/USD giả định 1. WBTC/WETH có biến động WETH/USD lịch sử, khác giả định quote cố định trong Monte Carlo. Không thay WBTC bằng BTC cho robustness reference.
- Gas: 1 mở + 1 đóng + 2/recenter; slippage là bps trên inventory được dời. Dynamic quyết định trên close trước, range mới chỉ thu phí từ bar sau. Không áp ràng buộc khả năng tài trợ; nếu tổng wealth âm, Sharpe/Sortino trả null.
- Full/fixed/volatility-scaled giữ range ban đầu; dynamic giữ độ rộng ban đầu và recenter khi rời range. Optimizer chọn một range tại entry bằng GBM, vol/mean volume quá khứ và cùng đường giả lập cho mọi range; horizon bằng kỳ giữ được yêu cầu. Không nhìn outcome tương lai để chọn range.

Nghiên cứu mặc định: 8 pool, 5 chiến lược toàn kỳ; các vị thế 30 ngày không chồng lấn trong mỗi pool/chiến lược, lưới w=0.05/0.1/0.2/0.4, panel thêm dynamic. Các quy tắc có sẵn được giữ cố định. Hồi quy dùng vol và log mean volume trễ trước entry, log width, rebalance policy dự kiến. Pool FE **bỏ fee tier vì đồng tuyến tính**; mô hình pair FE riêng nhận diện liên hệ fee tier giữa hai pool cùng cặp. OLS dùng Driscoll–Kraay HAC và bậc tự do theo số kỳ; quantile τ=0.1/0.5/0.9 có circular common-time block bootstrap 99 lần (ghi rõ fit không hội tụ), không dùng p-value IID. ADF/Breusch–Pagan/VIF là chẩn đoán mô tả. Chỉ có 11 kỳ nên inference mang tính thăm dò.

So sánh optimizer−fixed có CI block bootstrap 999 lần, giữ pairing và lấy mẫu chung theo thời gian cho tất cả pool. `GET /api/v1/research/reconciliation` đọc các tệp cùng manifest, kiểm tra SHA256 và trả bằng chứng cho giao diện; không chạy lại hoặc ghi đè archive. Với archive `2cffb779…c38e`:

- **H4:** 72/72 dòng có lợi ích tăng thêm trước gas bằng 0 và số đơn vị gas tăng thêm bằng 0; ngưỡng gas hòa vốn để trống. Chưa đủ bằng chứng đánh đổi chi phí do dời khoảng, không phải ngưỡng gas bằng 0 hoặc H4 đã được xác nhận.
- **Phân rã từng hàng:** 40/40 kết quả toàn kỳ có gas 0,06% vốn, trượt giá 0 và không dời khoảng. Hiệu `median(phí) − median(IL) − median(ΔR)` không phải trung vị chi phí; kiểm tra residual trên từng hàng thay vì suy chi phí từ các trung vị độc lập.
- **Hai cách đo optimizer:** trung vị toàn kỳ theo pool là 16,26% cho optimizer và 21,24% cho fixed; trung bình chênh lệch ghép cặp theo cửa sổ 30 ngày là **+1,48 điểm phần trăm**, CI bootstrap thăm dò 95% **+0,94 đến +2,04 điểm phần trăm**, trên 88 cặp và 11 cửa sổ. Hai kết quả khác chân trời và phép tổng hợp, nên có thể khác dấu mà không mâu thuẫn; chưa phải xác nhận OOS.

Bảng sensitivity so sánh vốn 5k/50k/500k USD × gas 0/15/100 × min_gap 1/7/30; phải dùng static cùng độ rộng với dynamic để tách ảnh hưởng dời tâm khi nghiên cứu gas hòa vốn. Bảng robustness kiểm tra thanh khoản C, protocol fee, slippage, cửa sổ vol và nguồn giá; so sánh cửa sổ vol dùng cùng thời kỳ để tránh thay đổi mẫu.

Các bảng chính: đặc điểm pool, returns/decomposition, monthly returns/risk, width panel, regressions, ADF, sensitivity, gas break-even, robustness, split coverage và daily equity. Hình: equity curves, fee decomposition, width tradeoff, price/ranges, optimal width–volatility, regression coefficients, gas sensitivity và current ticks (ghi rõ không dùng cho lịch sử).

**Điều kiện còn thiếu để nghiên cứu xác nhận:** giá/volume pool 2022–2024; active L/fee growth và protocol fee point-in-time; historical gas USD; archived publication vintages. Do đó không ghi “đã kiểm chứng optimizer ngoài mẫu” hoặc suy luận nhân quả từ các bảng này. Báo cáo tự sinh diễn giải H1–H5 ở `research_report.md`; phương pháp ở `docs/stage_5_report.md` và `docs/data_dictionary.md`.

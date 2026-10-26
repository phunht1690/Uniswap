# Đối chiếu bài luận với dashboard RangeLab

Ngày đối chiếu: 26 tháng 10 năm 2026.

## Phạm vi và kết luận

Bản đối chiếu này kiểm tra bài `Pyhton final report.docx` người dùng cung cấp với mã nguồn dashboard và bộ nghiên cứu lưu trữ. Bài luận và sản phẩm dùng chung nền tảng định giá, lịch sử quan sát và mô hình phí, nhưng không phải mọi màn hình đều chạy đúng chiến lược và cấu hình của báo cáo nghiên cứu. Vì vậy, cùng pool và cùng khoảng ngày chưa đủ để tái lập một kết quả nếu khác quy tắc dời khoảng, cửa sổ biến động, độ rộng hoặc cách tổng hợp.

Bài Word gốc được giữ nguyên. Những chỗ cần chỉnh nội dung bài được nêu riêng dưới đây; việc điều chỉnh dashboard không có nghĩa các đoạn đó trong Word đã được sửa.

Các tham chiếu `block` là vị trí khối văn bản hoặc bảng trong bản trích từ cấu trúc DOCX, **không phải số trang**. Số mục và tên bảng giúp tìm lại nội dung trong Word.

Nguồn kết quả định lượng được đối chiếu là nghiên cứu có mã:

`2cffb7795d463ca13906ef19d9fca43de2aef9c2e946294d9d14cec4c9e38c8e`

Bộ này có phiên bản `stage5-descriptive-research-v2`, dựa trên historical replay `stage5-historical-replay-v2`. Nó gồm 8 pool Ethereum, 40 kết quả toàn kỳ và 440 kết quả theo cửa sổ. Phạm vi toàn kỳ là từ 22 tháng 11 năm 2025 đến 20 tháng 10 năm 2026, tương ứng 332 kỳ lợi suất ngày. Các tệp gốc được giữ nguyên để không thay đổi bằng chứng đã dùng trong bài.

## Tám điểm cần phân biệt

| Vấn đề | Vị trí trong Word | Kết quả đối chiếu | Điều chỉnh thuộc dashboard | Nội dung Word còn cần cập nhật |
| --- | --- | --- | --- | --- |
| Cùng tên khoảng động nhưng khác chiến lược | Mục 3.5, Bảng 11, block 208; mục 4.4, block 304; chương 5, block 358–361 | Nghiên cứu dời tâm khi giá ra ngoài khoảng; comparison v1 trên giao diện dời tâm hằng tuần. Khác biệt này làm thay đổi dòng phí, inventory và chi phí ngay cả khi giữ nguyên pool và khoảng ngày. | Phân biệt rõ chế độ nghiên cứu và biến thể hằng tuần; ghi quy tắc hiệu lực của từng chuỗi trong kết quả và metadata. | Không mô tả kết quả lưu trữ như thể đại diện cho mọi quy tắc đang có trên giao diện. |
| Cấu hình chuẩn chưa đồng bộ | Bảng 9, block 192; Bảng 11, block 208; mô tả mẫu tại block 262 | Baseline nghiên cứu dùng độ rộng cố định 0,20 và cửa sổ biến động 30 ngày; giao diện cũ dùng 0,15 và 14 ngày. | Có preset nêu tên, bảng đối chiếu cấu hình và công bố giá trị hiệu lực; không âm thầm đổi kết quả cũ. | Ghi riêng cấu hình nghiên cứu, mặc định sản phẩm và các cấu hình tùy chỉnh. |
| Ví dụ tái lập dùng API cũ | Mục 5.7, block 383–395; đối chiếu Bảng 21, block 378 | Ví dụ gọi `/api/v1/simulate` và `/api/v1/runs`, trong khi màn hình hiện tại dùng `/api/v1/workbench/run` và `/api/v1/workbench/runs`. | Cung cấp ví dụ body workbench có `config` lồng bên trong và đọc lại đúng kiểu bản ghi. API legacy vẫn có thể được giữ để tái lập kết quả legacy. | Thay hoặc phân loại ví dụ 5.7; không gọi ví dụ legacy là tái lập toàn bộ chức năng workbench. |
| H4 bị diễn giải vượt bằng chứng | Mục 4.4, block 303, 306–307; bảng giả thuyết block 328; kết luận block 403, 408 | Cả 72 dòng gas hòa vốn có lợi ích tăng thêm trước gas bằng 0, số đơn vị gas tăng thêm bằng 0 và không có ngưỡng hòa vốn số. | Hiển thị trạng thái chưa nhận diện được đánh đổi lợi ích–chi phí; không biến giá trị thiếu hoặc trường hợp hòa thành ngưỡng gas bằng 0. | Bỏ cách suy nguyên nhân kém hiệu quả cho gas hoặc kết luận bằng chứng cùng hướng H4 từ mẫu không phát sinh dời khoảng. |
| Bảng 16 gán phần dư trung vị cho chi phí | Mục 4.2, block 265, 279–283; Bảng 16 tại block 281 | 40 kết quả toàn kỳ đều có gas bằng 0,0006 vốn và trượt giá bằng 0. Phần dư 0,07–0,17 điểm phần trăm tính từ các trung vị độc lập không phải chi phí thực. | Phân rã từng kết quả, hiển thị gas và trượt giá trực tiếp cùng sai số kế toán; tổng hợp các đại lượng sau khi kiểm tra từng hàng. | Không gán hiệu của các trung vị độc lập cho gas và trượt giá; sửa nhận xét phần dư tăng cùng tái cân bằng. |
| Thiếu kết quả quan trọng của optimizer | Tóm tắt block 6; mục 4.2 block 272; mục 4.7 block 328, 330; kết luận block 404 | Trung vị toàn kỳ theo pool và trung bình chênh lệch ghép cặp trên cửa sổ 30 ngày đo hai đại lượng khác nhau. Word chưa báo đầy đủ kết quả bootstrap theo cửa sổ. Giao diện comparison v1 cũng chưa đưa optimizer vào nhóm lựa chọn, dù backend hỗ trợ. | Đưa optimizer vào nhóm so sánh; đặt cạnh nhau các phép đo với nhãn chân trời, mẫu số, cách tổng hợp và phạm vi; công bố CI thăm dò đúng nghĩa. | Giải thích đồng thời cả hai kết quả thay vì kết luận chung rằng optimizer không cải thiện so với fixed. |
| Công thức chung thiếu lãi lỗ phòng hộ | Mục 2.6, công thức (9)–(10), block 124–127; tái xuất ở block 159, 252 và TC-02 block 448 | `simulate_policy` cộng `hedge_pnl` vào tài sản LP, lợi nhuận ròng và chênh lệch HODL khi bật phòng hộ. Công thức không hedge chỉ đúng cho phạm vi không hedge. | Hiển thị thành phần hedge và công thức đầy đủ, kèm quy ước dấu IL; không cộng hoặc trừ IL hai lần. | Bổ sung thành phần phòng hộ hoặc giới hạn rõ công thức (9)–(10) cho chiến lược không phòng hộ. |
| Trộn trạng thái trước và sau khi bổ sung kết quả | Mục 4.7 block 328; tiểu kết block 347; mục 6.1 block 400–404 | Những đoạn này vẫn nói thiếu phân rã theo pool, bảng theo độ rộng hoặc hệ số, mặc dù đã có tại block 286, 296, 313 và 316. | Trình bày trạng thái bằng chứng theo các tệp nghiên cứu thực có; phân biệt đã có số liệu với đã đủ cơ sở xác nhận giả thuyết. | Viết lại bảng trạng thái, tiểu kết và kết luận theo bộ bằng chứng cuối cùng. Dashboard không tự sửa được các đoạn trong Word. |

## Bảng đối chiếu cấu hình và quy tắc

Hai chế độ dưới đây phải được xem là hai thiết kế chiến lược khác nhau. Việc chọn preset chỉ là cách áp dụng bộ tham số đã công bố; cấu hình hiệu lực của lần chạy vẫn cần được ghi riêng nếu người dùng sửa tham số sau đó.

| Thành phần | Tái lập quy tắc nghiên cứu | Biến thể hằng tuần của sản phẩm |
| --- | --- | --- |
| Định danh chế độ comparison | `strategy_mode = research` | `strategy_mode = weekly` |
| Preset độ rộng fixed | `half_width = 0.20` | `half_width = 0.15` |
| Preset cửa sổ biến động | `volatility_window_days = 30` | `volatility_window_days = 14` |
| Chiến lược `dynamic` | Tính độ rộng tại entry; dời tâm khi giá trước quyết định nằm ngoài khoảng, chịu giới hạn khoảng cách và số lần | Tính độ rộng tại entry; xét dời tâm sau mỗi 7 ngày, chịu cùng các giới hạn được cấu hình |
| Chiến lược `vol_scaled` | Tính độ rộng từ biến động trước entry và giữ khoảng đó; không rolling cập nhật độ rộng hằng tuần | Dùng biến động rolling trễ; cập nhật độ rộng và tâm theo tuần |
| Chiến lược `optimizer` | Phải được cung cấp để so với baseline nghiên cứu; chọn độ rộng tại entry trên dữ liệu trước entry | Có thể so trong chế độ tùy chỉnh, nhưng không gộp mặc định thành bằng chứng của báo cáo lưu trữ |
| Kết quả nghiên cứu đã lưu | Tải theo `research_id`, phiên bản và manifest gốc | Không đổi nhãn của các bản ghi nghiên cứu thành weekly |
| Kết quả comparison v1 đã lưu | Phải giữ và nhận diện theo metadata gốc | v1 dùng weekly cho dynamic và rolling weekly cho vol_scaled; không gán lại quy tắc mới dựa trên nhãn preset hiện tại |

Trong bản comparison mới, lựa chọn chế độ là một phần của cấu hình và danh tính kết quả. Thay đổi quy tắc yêu cầu phiên bản comparison mới; `rangelab-comparison-v1` không được dùng như tên gọi cho các kết quả đã thay ngữ nghĩa. Báo cáo lưu trữ vẫn giữ phiên bản và dữ liệu gốc. Các nhãn chiến lược khi mở một kết quả phải căn cứ cấu hình và quy tắc của **kết quả đó**, không chỉ căn cứ form hiện đang chọn.

### Ví dụ cho thấy chỉ đổi quy tắc đã làm kết quả khác nhau

Đối chiếu trực tiếp trên cùng dữ liệu WETH/USDC mức phí 0,05%, từ ngày 22 tháng 11 năm 2025 đến ngày 20 tháng 10 năm 2026, vốn 50.000 USD, gas 15 USD mỗi đơn vị, trượt giá 0, cửa sổ biến động 30 ngày và nửa độ rộng ban đầu `0.9965738952292797`. Hai lần replay đều có 332 kỳ ngày, cùng khoảng cách tối thiểu 7 ngày và giới hạn 52 lần dời khoảng.

| Quy tắc của dynamic | Chênh lệch LP so với HODL | Số lần dời khoảng | Gas theo tỷ lệ vốn | Trượt giá theo tỷ lệ vốn |
| --- | --- | --- | --- | --- |
| Khi ra khỏi khoảng | 13,642819530981187% | 0 | 0,06% | 0% |
| Hằng tuần | 5,062521418369070% | 47 | 2,88% | 0% |

Phép đối chiếu này giữ cùng độ rộng và cửa sổ để tách ảnh hưởng của quy tắc dời tâm. Nó không có nghĩa mọi chênh lệch giữa hai preset mặc định chỉ do tái cân bằng: nếu đồng thời đổi độ rộng, cửa sổ, dữ liệu hoặc chi phí thì các yếu tố đó cũng làm đổi kết quả. Nó cũng không chứng minh phần giảm chênh lệch bằng đúng chi phí gas; dời tâm còn thay đổi inventory và lượng phí được nhận.

## Bằng chứng định lượng và cách diễn giải

### H4 chưa được kiểm tra bằng mẫu có phát sinh dời khoảng

Tệp `gas_break_even.csv` có 72 dòng, bằng 8 pool nhân 3 mức vốn nhân 3 mức khoảng cách tối thiểu. Kiểm tra trực tiếp cho thấy:

- `dynamic_minus_static_before_gas_usd = 0` ở 72 trên 72 dòng.
- `extra_gas_units = 0` ở 72 trên 72 dòng.
- `break_even_gas_usd` để trống ở 72 trên 72 dòng.
- Nhãn gốc là `dynamic_not_better_at_zero_gas`; nhãn này không tự chứng minh dynamic thua ở gas bằng 0, vì dữ liệu ở đây là hòa với chiến lược tĩnh cùng độ rộng ban đầu.

Tệp `dynamic_vs_fixed.csv` có 216 dòng quét vốn, gas và khoảng cách. Cần dùng cột so sánh với `static_matched_width` để nghiên cứu tác động dời tâm; cột `fixed` dùng baseline độ rộng khác nên không tách riêng tác động tái cân bằng.

Về mặt toán học, khi lợi ích tăng thêm trước gas và số đơn vị gas tăng thêm đều bằng 0 thì phép tính ngưỡng hòa vốn là trường hợp 0 chia 0, không nhận diện được một mức gas hữu hạn. Đây là **chưa đủ bằng chứng cho H4**, không phải H4 đã được xác nhận hay đã bị bác bỏ.

Wording phù hợp trên giao diện: “Trong bộ thử này không phát sinh dời khoảng. Lợi ích tăng thêm trước gas và số đơn vị gas tăng thêm đều bằng 0, nên chưa xác định được ngưỡng gas hòa vốn hoặc đánh đổi lợi ích–chi phí.”

### Kiểm tra chi phí phải thực hiện theo từng hàng

Trong `strategy_returns.csv`, cả 40 trên 40 kết quả đều có:

- `gas = 0.0006`, tức **0,06% vốn** hoặc 30 USD trên vốn 50.000 USD.
- `rebalance_cost = 0` và `rebalance_count = 0`.
- Hai đơn vị gas gồm mở và đóng vị thế trong historical replay.

Với quy ước IL là khoản thiếu hụt dương so với HODL, kiểm tra từng hàng là:

```text
residual = excess_vs_hodl - (fees - il - gas - rebalance_cost)
```

Sai số tuyệt đối lớn nhất trên 40 hàng là khoảng `3.82e-12` theo phân số vốn, tương đương `3.82e-10` điểm phần trăm. Đây là sai số số học rất nhỏ. Phần dư từ các trung vị trong Bảng 16 không được dùng thay cho `gas` hoặc `rebalance_cost` của dữ liệu gốc.

Nói chung, `median(F) - median(IL) - median(DeltaR)` không bằng `median(G + C)`. Nếu cần bảng tổng hợp trung vị, vẫn phải công bố riêng trung vị chi phí thực được tính trên các hàng và ghi rõ các cột trung vị độc lập không có tính cộng.

### Optimizer theo cửa sổ và optimizer toàn kỳ đo hai đại lượng khác nhau

Từ `strategy_returns.csv`, trung vị chênh lệch LP so với HODL trên 8 pool của kết quả toàn kỳ là:

| Chiến lược | Trung vị chênh lệch toàn kỳ |
| --- | --- |
| Fixed | 21,2371573081% vốn |
| Optimizer | 16,25900353655% vốn |
| Dynamic | 16,10483103755% vốn |
| Vol scaled | 16,10483103755% vốn |
| Toàn dải | 4,04775987418% vốn |

Từ `monthly_returns.csv` và `optimizer_paired_bootstrap.json`, phép đo theo cửa sổ có đặc tả khác:

| Trường | Giá trị |
| --- | --- |
| Đại lượng | Trung bình chênh lệch `optimizer - fixed` trên các cặp pool và cửa sổ 30 ngày |
| Số cặp pool và cửa sổ | 88 |
| Số cửa sổ theo thời gian | 11 |
| Chênh lệch trung bình | `0.014790149709883975` phân số vốn, tức **+1,47901497099 điểm phần trăm** |
| Khoảng 95% bootstrap thăm dò | `[0.009446485901559205, 0.020386876700070267]`, tức **+0,94464859016 đến +2,03868767001 điểm phần trăm** |
| Số lần lấy mẫu lại | 999 |
| Cách lấy mẫu | Circular block theo thời gian, khối 2 cửa sổ; giữ ghép cặp và lấy mẫu chung giữa các pool |
| Seed | 42 |
| Trạng thái | Thăm dò, có điều kiện trên mô hình phí; `not_confirmatory_OOS = true` |

Tái tính chênh lệch từ CSV bằng cách ghép fixed và optimizer cùng pool, cùng ngày bắt đầu, lấy trung bình giữa pool cho từng cửa sổ rồi lấy trung bình theo thời gian cho kết quả `0.014790149709879784`. Chênh lệch nhỏ với JSON do làm tròn các số khi xuất CSV.

Kết quả trung vị toàn kỳ thấp hơn và kết quả trung bình ghép cặp theo cửa sổ dương có thể cùng đúng. Chúng khác chân trời nắm giữ, thời điểm chọn độ rộng, cách ghép cặp và phép tổng hợp; không lấy hiệu hai trung vị toàn kỳ để thay cho trung bình các chênh lệch ghép cặp. Khoảng bootstrap nêu trên cũng không biến mẫu 2025–2026 thành kiểm định ngoài mẫu theo thiết kế hiệu chỉnh 2022–2024.

## Công thức bao phủ policy phòng hộ

Đặt:

- `K` là vốn ban đầu bằng USD.
- `Vinv` là giá trị token trong vị thế LP cuối kỳ, chưa cộng phí và chi phí.
- `VHODL` là giá trị giữ nguyên lượng token ban đầu cuối kỳ.
- `F` là phí tích lũy; `G` là gas; `C` là ma sát giao dịch khác gas, cùng đơn vị USD.
- `H` là lãi hoặc lỗ phòng hộ tích lũy bằng USD, có dấu.
- `IL_loss = VHODL - Vinv` là khoản thiếu hụt inventory so với HODL theo quy ước dương khi inventory kém HODL. Đây là quy ước dấu của biến `il` dùng trong phân rã engine; giá trị không bị ép thành số dương nếu chênh lệch thực mang dấu ngược.

Khi đó:

```text
Wealth_LP = Vinv + F - G - C + H
R_LP      = Wealth_LP / K - 1
R_HODL    = VHODL / K - 1
DeltaR    = R_LP - R_HODL
          = (Vinv - VHODL + F - G - C + H) / K
          = (F - IL_loss - G - C + H) / K
```

Nếu giao diện hiển thị IL có dấu âm như `IL_signed = Vinv - VHODL`, công thức tương đương dùng **cộng `IL_signed`**, không trừ tiếp IL một lần nữa. Khi không phòng hộ, `H = 0` và công thức rút về trường hợp không hedge trong bài.

Đối chiếu `src/models/policies.py` cho thấy `hedge_pnl` được cộng vào tài sản LP, `excess` và `net`. Phòng hộ hiện tại là short delta inventory rời rạc theo ngày, có gas và ma sát, nhưng chưa có funding, lãi vay, ký quỹ, thanh lý hoặc ràng buộc khả năng tài trợ. Công thức đầy đủ không được dùng để ngụ ý các cơ chế đó đã được mô hình hóa.

## API và khả năng tái lập

Các lớp kết quả cần được phân biệt:

| Lớp | Endpoint và nơi lưu | Ý nghĩa |
| --- | --- | --- |
| Mô phỏng legacy | `POST /api/v1/simulate`, `GET /api/v1/runs/{run_id}`, `outputs/runs` | Hợp đồng cũ; không phải body hoặc tập tính năng đầy đủ của workbench |
| Workbench của giao diện | `POST /api/v1/workbench/run`, `GET /api/v1/workbench/runs/{run_id}`, `outputs/workbench` | Policy, ghi đè volume và snapshot thị trường nằm ở cấp ngoài `config`; mô hình workbench có phiên bản riêng |
| Comparison lịch sử | `POST /api/v1/backtests/compare`, `outputs/comparisons` | Cấu hình chế độ chiến lược và quy tắc hiệu lực của lần so sánh |
| Nghiên cứu lưu trữ | `GET /api/v1/research/status`, `outputs/research/{research_id}` | Bộ kết quả đã lưu với mẫu, cấu hình, manifest và phiên bản của lần nghiên cứu đó |

Block 258 trong Word còn gọi `stage4-observed-inputs-v2` là phiên bản hiện tại trong khi chương 5 mô tả workbench. Không dùng một chuỗi phiên bản đại diện cho cả bốn lớp. Metadata của kết quả đang xem là căn cứ để biết engine và hợp đồng của nó.

Ví dụ PowerShell dưới đây tái lập **một lần chạy workbench**, không phải tái lập đồng thời báo cáo nghiên cứu 8 pool hoặc comparison lịch sử. Ví dụ dùng bộ nghiên cứu đã lưu, không tạo một snapshot live mới cho lần gửi lại:

```powershell
$config = @{
    pool = 'weth-usdc-500'
    capital = 50000
    horizon_days = 60
    vol_annual = 0.65
    gas_usd = 15
    risk_max_exit_prob = 0.4
    min_rebalance_gap_days = 7
    price_model = 'gbm'
    n_paths = 300
    seed = 42
    path_index = 0
}
$request = @{
    config = $config
    rebalance_policy = 'none'
    delta_threshold = 0.1
    volume_daily_override_usd = $null
    market_snapshot_id = $null
}
$run = Invoke-RestMethod -Method Post `
    -Uri 'http://127.0.0.1:8000/api/v1/workbench/run' `
    -ContentType 'application/json' `
    -Body ($request | ConvertTo-Json -Depth 8)
$saved = Invoke-RestMethod -Uri (
    'http://127.0.0.1:8000/api/v1/workbench/runs/' + $run.meta.run_id
)
$replay = Invoke-RestMethod -Method Post `
    -Uri 'http://127.0.0.1:8000/api/v1/workbench/run' `
    -ContentType 'application/json' `
    -Body ($saved.config | ConvertTo-Json -Depth 8)
$run.meta.run_id -eq $replay.meta.run_id
```

Điều kiện tái lập vẫn là cùng dữ liệu, cấu hình hiệu lực, seed, phiên bản và môi trường số. Khi cần thị trường mới, tạo snapshot một lần và gửi lại đúng `market_snapshot_id` đã lưu; không chụp lại đầu vào ở mỗi lần so sánh rồi yêu cầu kết quả phải giữ nguyên.

## Những phần của bài luận cần cập nhật riêng

1. **Mục 3.5 và chương 5:** giải thích S3 giữ khoảng theo biến động tại entry trong nghiên cứu, S3 rolling hằng tuần trên sản phẩm và hai quy tắc S4. Bổ sung bảng cấu hình thay vì chỉ dùng các tên giống nhau.
2. **Mục 4.2 và Bảng 16:** giữ phép kiểm tra kế toán từng hàng, ghi chi phí thực 0,06% vốn và trượt giá 0 trong bộ 40 kết quả. Không suy chi phí từ hiệu các trung vị.
3. **Mục 4.4, 4.7 và RQ4 trong 6.1:** đổi trạng thái H4 thành chưa đủ bằng chứng vì không phát sinh dời khoảng trong bộ thử được dẫn. Phân biệt baseline fixed với static cùng độ rộng ban đầu.
4. **Mục 4.7, tiểu kết 4.10 và RQ1–RQ3 trong 6.1:** cập nhật trạng thái theo những bảng đã có: phân rã pool tại block 286, bảng độ rộng tại 296, hệ số OLS tại 313 và phân vị tại 316. Có hệ số không đồng nghĩa đã có nhận diện nhân quả hay mẫu ngoài mẫu.
5. **Tóm tắt, H5 và RQ5:** báo cáo cả trung vị toàn kỳ lẫn trung bình chênh lệch ghép cặp theo cửa sổ, nêu đúng số cặp, số kỳ và CI thăm dò. Không diễn giải cả hai thành cùng một kết luận về hiệu quả đầu tư.
6. **Công thức 9–10, bảng chỉ số và TC-02:** bổ sung thành phần hedge hoặc ghi rõ chỉ áp dụng cho chiến lược không phòng hộ; nêu quy ước dấu của IL.
7. **Mục 3.9 và 5.7:** phân biệt phiên bản legacy và workbench, body API, nơi lưu và điều kiện tái lập. Cập nhật kết luận sau khi đã thống nhất toàn bộ các mục trên.

## Tệp đã kiểm tra

Các tệp dưới đây nằm trong thư mục `outputs/research/2cffb7795d463ca13906ef19d9fca43de2aef9c2e946294d9d14cec4c9e38c8e/`:

- `gas_break_even.csv`: 72 dòng; kiểm tra trực tiếp lợi ích tăng thêm, số đơn vị gas tăng thêm và giá trị ngưỡng.
- `dynamic_vs_fixed.csv`: 216 dòng; phân biệt fixed baseline và static cùng độ rộng.
- `strategy_returns.csv`: 40 dòng; tính lại trung vị, số recenter, chi phí và residual theo từng hàng.
- `monthly_returns.csv`: 440 dòng; ghép 88 cặp optimizer và fixed theo pool và cửa sổ, tổng hợp qua 11 cửa sổ.
- `optimizer_paired_bootstrap.json`: trung bình chênh lệch, CI, 999 lần lấy mẫu, seed và trạng thái thăm dò.

SHA256 của `gas_break_even.csv`, `strategy_returns.csv`, `monthly_returns.csv` và `optimizer_paired_bootstrap.json` đã được đối chiếu với manifest được chỉ ra bởi `outputs/research/latest.json`. Quy tắc dời khoảng được đối chiếu với `src/evaluation/backtest.py`, wrapper comparison và `config/backtest.yaml`; dòng tiền hedge được đối chiếu với `src/models/policies.py`. Bản ghi này là báo cáo kiểm chứng bằng chứng và quy ước điều chỉnh, không thay cho biên bản kiểm thử runtime của bản dashboard sau khi tích hợp.

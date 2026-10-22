Chức năng dữ liệu và mô hình của dashboard RangeLab

Tài liệu giải thích hệ thống mô phỏng thanh khoản Uniswap v3

Cập nhật ngày 22 tháng 10 năm 2026. Phiên bản mô phỏng RangeLab workbench v3 và so sánh quá khứ v1.

RangeLab giúp người dùng tìm hiểu việc cung cấp thanh khoản trên Uniswap v3: chọn cặp token, tìm khoảng giá, so sánh với giữ nguyên token, thử tình huống rủi ro và đánh giá chiến lược trên dữ liệu quá khứ. Hệ thống chạy mô phỏng trên máy chủ Python; các kết quả phụ thuộc dữ liệu và giả định của từng lần chạy.

Tài liệu này dành cho người sử dụng dashboard và nhóm nghiên cứu cần giải thích hoặc kiểm tra kết quả. Nội dung trình bày các chức năng đang có, nguồn dữ liệu, mô hình tính toán, luồng xử lý và giới hạn khi diễn giải. Dashboard không kết nối ví, không gửi giao dịch và không sử dụng tiền thật.

## 1 Các chức năng người dùng có thể sử dụng

| Khu vực | Chức năng và kết quả |
| --- | --- |
| Tổng quan | Tìm kiếm và lọc 14 pool; xem giá đang theo dõi, TVL, khối lượng và biểu đồ lịch sử theo 7 ngày, 30 ngày, 90 ngày hoặc 1 năm. |
| Tìm khoảng giá LP | Đặt vốn, thời gian, rủi ro, mô hình giá và chi phí; chạy nhiều đường giá để tìm khoảng đáp ứng điều kiện. |
| Kết quả tối ưu hóa | Đọc khoảng giá, phí, IL, chi phí, lợi nhuận LP và chênh lệch với HODL; xem đường mẫu, lưới độ rộng và tải báo cáo. |
| Kiểm tra rủi ro và dữ liệu | Chạy stress test, quét độ nhạy, xem phương pháp và độ phủ dữ liệu. Tin tức nằm trong tab riêng của khu vực này. |
| Thử chiến lược trong quá khứ | So sánh các chiến lược trên cùng giai đoạn; đổi biểu đồ USD hoặc phần trăm, xem xếp hạng và xuất CSV. |

## Quy trình sử dụng

Bắt đầu từ Tổng quan, chọn cặp token và mức phí, đặt giả định rồi chạy tối ưu hóa. Đọc kết quả trước khi mở stress test hoặc phân tích độ nhạy. Dùng backtest để kiểm tra trên giai đoạn đã quan sát. Mục Thông tin và Thuật ngữ giúp tra cứu trong lúc sử dụng; bản tin có thể mở mà không cần tạo mô phỏng.

## 2 Dữ liệu được sử dụng

### Phạm vi pool

Bộ dữ liệu hiện có gồm 14 pool trên Ethereum và Arbitrum. Một cặp token khác mức phí được xem là một pool riêng; địa chỉ, mạng và thứ tự token được lưu để tránh nhầm cặp hoặc đảo chiều giá.

| Cặp token | Mạng | Mức phí | Số pool |
| --- | --- | --- | --- |
| WETH và USDC | Ethereum | 0,05%  0,30%  1,00% | 3 |
| WETH và USDT | Ethereum | 0,05%  0,30%  1,00% | 3 |
| WBTC và WETH | Ethereum | 0,05%  0,30%  1,00% | 3 |
| USDC và USDT | Ethereum | 0,01%  0,05% | 2 |
| ARB và WETH | Arbitrum | 0,05%  0,30%  1,00% | 3 |

### Nguồn và vai trò

| Nguồn | Dữ liệu và mục đích | Phạm vi đã lưu |
| --- | --- | --- |
| Ethereum và Arbitrum RPC | Danh tính pool, token, fee, giá, tick, thanh khoản hoạt động và block tại thời điểm chụp. | Snapshot ngày 20 và 21 tháng 10 năm 2026; luồng theo dõi mới chạy riêng. |
| GeckoTerminal | Giá và khối lượng OHLCV của pool, TVL và tỷ giá quote sang USD. | Các tập pool nằm trong khoảng 22 tháng 10 năm 2025 đến 21 tháng 10 năm 2026. |
| DefiLlama | TVL lịch sử phục vụ đánh giá quá khứ và đối chiếu. | Phạm vi gộp từ 27 tháng 3 năm 2022 đến 21 tháng 10 năm 2026. |
| Binance Spot | Giá tham chiếu của cặp giao dịch và giá quote sang USD. | Phạm vi gộp sớm nhất từ 14 tháng 7 năm 2017 đến 21 tháng 10 năm 2026. |
| CoinGecko | Giá USD tham chiếu và đối chiếu tài sản. | Phạm vi gộp từ 21 tháng 10 năm 2025 đến 20 tháng 10 năm 2026. |

Các mốc trên là biên sớm nhất và muộn nhất của từng nhóm dữ liệu trong coverage đã lưu, không có nghĩa mọi token hay pool đều có đủ ngày trong toàn khoảng. Giá tham chiếu từ sàn tập trung không thay cho khối lượng của pool. TVL là tổng vốn; active L là thanh khoản hoạt động tại giá hiện tại, khác đơn vị và cách dùng.

Danh mục dữ liệu nghiên cứu trên dashboard có 92 bản ghi trạng thái, trong đó 87 bản ghi có dữ liệu. FRED, The Graph và Kaiko chưa có dữ liệu sử dụng được trong bộ này, nên không được coi là đầu vào đã xác minh. Xem tab Dữ liệu và Phương pháp để biết phạm vi và khoảng trống của từng tập.

## 3 Thu thập cập nhật và lưu dữ liệu

### Ba luồng dữ liệu cần phân biệt

Dữ liệu lịch sử được thu thập theo đợt, lưu trong thư mục data và dùng cho hiệu chỉnh mô hình hoặc backtest. Luồng thị trường theo dõi giá hiện tại được cập nhật trong bộ nhớ máy chủ. Kết quả mô phỏng là đầu ra được tính từ một bộ đầu vào xác định và lưu riêng; nó không tự đổi theo giá mới trên thanh thị trường.

### Chu kỳ theo dõi thị trường

Worker thị trường kiểm tra giá và thanh khoản RPC mỗi 30 giây, kiểm tra TVL, khối lượng 24 giờ và quote sang USD từ GeckoTerminal mỗi 300 giây. Trang đọc bộ nhớ đệm mỗi 30 giây khi đang hoạt động. Đây là cập nhật gần thời gian thực bằng thăm dò định kỳ, có độ trễ mạng và nguồn, không phải luồng từng giao dịch swap.

RPC đọc trạng thái giá và thanh khoản tại cùng block, kiểm tra chain ID và hash block. Giao diện ghi thời điểm block, lần lấy thành công và trạng thái mới, trễ hoặc lỗi. Khi nguồn lỗi, giá cũ được giữ kèm thông báo; dữ liệu thiếu không tự được thay bằng 0. Block latest vẫn có thể bị sắp xếp lại.

### Chụp bộ đầu vào trước khi tính

Khi bật Dữ liệu thị trường mới và bấm chạy, máy chủ tạo một snapshot bất biến gồm giá, active L, quote sang USD, TVL, volume, thời điểm nguồn và bản lịch sử hiệu chỉnh đã lưu. Snapshot có mã hash riêng. Nếu thiếu dữ liệu bắt buộc hoặc nguồn quá trễ, hệ thống báo lỗi để người dùng biết.

Stress test và độ nhạy của lần chạy đó đọc lại đúng snapshot đã chụp. Luồng nhanh không làm mới toàn bộ phân bố thanh khoản theo tick và không tự tải thêm nến lịch sử. Nếu bỏ chọn dữ liệu mới, mô phỏng dùng bộ nghiên cứu đã lưu cùng thời điểm được ghi trong kết quả.

### Kiểm tra và truy xuất nguồn gốc

Luồng thu thập giữ bản thô, chuẩn hóa vào Parquet, lập danh mục DuckDB, tính đặc trưng và cập nhật coverage, source log, lineage cùng mã SHA256. Kiểm tra gồm thời gian UTC, giá dương, volume không âm, thứ tự và trùng timestamp, ngày thiếu và tính toàn vẹn file. Việc cập nhật lịch sử chạy theo đợt riêng; mở web hoặc nhận một giá mới không đồng nghĩa toàn bộ lịch sử đã mới.

### Tin tức công khai

Tab Tin tức và cộng đồng chỉ hiển thị Uniswap Blog và diễn đàn quản trị Uniswap. Máy chủ kiểm tra mỗi 5 phút, trang đọc cache mỗi 30 giây khi tab mở. Bản tin tối đa 100 tiêu đề trong 90 ngày gần nhất; có lọc nguồn, cặp token, nội dung giao thức và token, nhãn v3 hoặc v4, ngày đăng và lần lấy tin. Tin tức không tham gia tối ưu hóa, PnL hoặc chấm điểm cảm xúc. Đề xuất trên diễn đàn chưa đồng nghĩa đã được thông qua.

## 4 Các mô hình tạo đường giá

Monte Carlo chạy nhiều tình huống giá rồi tổng hợp kết quả. Người dùng chọn một trong ba mô hình bên dưới, số đường N, thời gian H và seed, tức mã khởi tạo số ngẫu nhiên để tạo lại tình huống. Các chiến lược trong cùng lần chạy được thử trên cùng các đường giá để việc so sánh nhất quán.

### GBM với biến động do người dùng đặt

GBM, hay chuyển động Brown hình học, giả lập thay đổi log giá mỗi ngày bằng nhiễu chuẩn với độ lệch chuẩn σ chia căn bậc hai của 365. Engine đặt xu hướng kỳ vọng của giá bằng 0; hệ số hiệu chỉnh âm một nửa phương sai được dùng khi chuyển từ log sang giá. Đây là giả định về dao động giá, không phải dự báo giá chắc chắn tăng.

Người dùng có thể nhập σ từ 0% đến 500% mỗi năm hoặc dùng con số lịch sử được gợi ý. Giữ N, H, seed và dữ liệu giống nhau sẽ tạo lại cùng các tình huống. GBM phù hợp để đặt câu hỏi theo giả định nhưng không biểu diễn đầy đủ nhảy giá, đuôi dày hay thay đổi chế độ thị trường.

### Bootstrap theo khối lịch sử

Stationary bootstrap lấy lại các đoạn lợi suất và khối lượng quan sát trước thời điểm hiệu chỉnh. Lợi suất và volume được lấy theo cặp cùng ngày; mỗi ngày có xác suất bắt đầu đoạn mới bằng nghịch đảo độ dài khối trung bình. Mặc định độ dài này là 10 ngày. Cách làm giữ một phần quan hệ theo thời gian và quan hệ giữa giá với volume trong mẫu đã có.

Mô hình yêu cầu ít nhất 31 giá ngày liên tiếp trước thời điểm hiệu chỉnh để tạo 30 cặp lợi suất và volume. Dữ liệu có ngày trống bị từ chối. Vì chỉ tái lấy mẫu lịch sử, bootstrap không tự tạo ra một chế độ thị trường chưa xuất hiện trong mẫu.

### GARCH với biến động thay đổi theo thời gian

GARCH(1,1) là mô hình phương sai có điều kiện: phương sai ngày tiếp theo được ước lượng từ mức nền, bình phương cú sốc trước đó và phương sai trước đó. Mô hình dùng trung bình bằng 0, nhiễu chuẩn và thư viện arch để hiệu chỉnh. Nó mô tả hiện tượng ngày biến động mạnh thường xuất hiện thành cụm.

GARCH cần ít nhất 101 giá ngày liên tiếp trước thời điểm hiệu chỉnh để có 100 lợi suất. Engine kiểm tra hội tụ và tính hợp lệ của tham số; dữ liệu gần như không đổi hoặc việc ước lượng không hội tụ sẽ báo lỗi. Giá được sinh từ phương sai điều kiện, không chỉ dùng một σ cố định cho toàn đường đi.

### Khối lượng giao dịch trong mô phỏng

Nếu người dùng ghi đè, volume được giữ cố định theo USD mỗi ngày. Nếu không, bootstrap sử dụng cặp volume đã lấy mẫu; GBM và GARCH dùng thông tin lịch sử trước thời điểm hiệu chỉnh để ước lượng mức volume, có thể theo các nhóm biến động trễ. Hệ số liên hệ volume với cú sốc giá và trần hệ số là giả định kịch bản được lưu trong metadata, không phải khối lượng tương lai đã quan sát.

## 5 Định giá LP và tìm khoảng giá

### Vị thế thanh khoản tập trung

Một vị thế v3 có hai biên giá và lượng thanh khoản L. Trong khoảng, vị thế giữ cả hai token. Khi giá tiến về một biên, vị thế chuyển dần về một token; ngoài biên, vị thế chỉ còn một token. Engine dùng công thức dự trữ theo căn bậc hai của giá để tính số token và giá trị vị thế tại mỗi mốc ngày.

Khoảng được đặt đối xứng theo log quanh giá P. Với nửa độ rộng w, biên dưới là P nhân exp của âm w và biên trên là P nhân exp của w. Ví dụ P bằng 100 và w bằng 0,1 cho khoảng xấp xỉ 90,48 đến 110,52; đây không phải biên đúng bằng cộng trừ 10%. Tick được làm tròn theo bước của pool để tham khảo; định giá hiện tại vẫn dùng biên liên tục.

### Phí thu được và chi phí

Phí một ngày được ước lượng bằng volume USD nhân fee rate nhân tỷ trọng L của vị thế trong tổng L của vị thế và nền, sau đó nhân điều kiện giá nằm trong khoảng. Active L nền được giữ cố định trong mô phỏng tương lai. Phí được giữ thành tiền mặt USD và không tự tái đầu tư.

Phí mạng là số USD người dùng đặt cho một đơn vị thao tác. Mở LP tính một đơn vị; mỗi lần đặt lại khoảng thường tính hai đơn vị và có thêm ma sát theo bps nếu đã cấu hình. Mô phỏng tương lai chưa tính một khoản đóng LP chung cuối kỳ. Phòng hộ có cách tính thao tác riêng nêu ở mục tiếp theo.

### Mốc so sánh và giá trị cuối kỳ

HODL dùng một nửa vốn ban đầu mua mỗi token rồi giữ nguyên lượng token đó. Tỷ trọng 50 trên 50 chỉ áp dụng lúc mở vị thế. Giá trị LP ròng cuối kỳ gồm giá trị token trong LP cộng phí cộng PnL phòng hộ nếu có, trừ phí mạng và ma sát. Lợi nhuận ròng bằng giá trị này chia vốn ban đầu rồi trừ một.

Chênh lệch do giá hay IL trên giao diện so sánh phần token trong LP với giữ token, trước phí và chi phí. Vì thế cần đọc IL cùng phí, gas và kết quả ròng. Chênh lệch LP với HODL được đo sau các thành phần liên quan; LP có thể hơn HODL mà vẫn lỗ so với vốn ban đầu.

### Quy tắc tối ưu hóa

Engine thử 20 độ rộng trên lưới theo cấp số nhân. Với mỗi độ rộng, nó chạy policy đã chọn trên cùng tập đường giá, tính kỳ vọng chênh lệch LP với HODL và tỷ lệ đường từng ra khỏi khoảng. Trong các phương án đạt giới hạn rủi ro, engine chọn phương án có kỳ vọng chênh lệch cao nhất. Nếu không có phương án đạt, kết quả ghi rõ không khả thi.

Giới hạn ra khỏi khoảng đo xác suất có ít nhất một mốc ngày nằm ngoài biên, không phải xác suất mất vốn hoặc trần thua lỗ. Tỷ lệ thời gian trong khoảng đo số ngày hoạt động trên toàn thời gian; hai chỉ số này trả lời hai câu hỏi khác nhau. Độ rộng tối ưu chỉ là tốt nhất trong lưới và giả định đã thử.

## 6 Điều chỉnh vị thế và kiểm tra rủi ro

### Các policy có thể chọn

| Policy | Cơ chế trong mô phỏng |
| --- | --- |
| Nắm giữ thụ động | Giữ khoảng ban đầu; không tự đặt lại khoảng khi giá đi ra ngoài. |
| Tái cân bằng hàng tuần | Xét đặt lại tâm khoảng sau mỗi 7 ngày, theo khoảng cách tối thiểu và số lần tối đa đã đặt; không recenter LP ở mốc cuối kỳ. |
| Theo ngưỡng tỷ trọng | Đặt lại khoảng khi tỷ trọng giá trị token cơ sở lệch khỏi 50% đến ngưỡng delta đã cấu hình; vẫn chịu các giới hạn số lần và khoảng cách. |
| Phòng hộ hằng ngày | Dùng vị thế short lượng token cơ sở của LP và điều chỉnh theo mốc ngày, có phí mạng và ma sát giao dịch; đóng hedge cuối kỳ. |

Policy phòng hộ là xấp xỉ rời rạc. Mô hình chưa tính funding, lãi vay, ký quỹ, thanh lý hay giới hạn khả năng thanh toán; không thể xem kết quả này là một vị thế phái sinh thực thi được ngoài thị trường. Chi phí mô hình có thể vượt vốn nếu người dùng đặt giả định quá lớn.

### Stress test hoạt động như thế nào

Stress test bắt đầu từ kết quả tối ưu đã lưu. Người dùng chọn một trong năm tình huống mẫu hoặc chỉnh mức tăng giảm giá cuối kỳ, hệ số dao động và hệ số phí mạng. Máy chủ dùng GBM log bridge để buộc giá kết thúc đúng mức shock, đồng thời tạo nhiều đường đi khác nhau đến mức đó bằng cùng seed.

Khoảng ban đầu không được tối ưu lại theo cú sốc đã biết; policy đã chọn vẫn được áp dụng trong kịch bản. Volume giữ ở mức trung bình của lần chạy gốc, active L và quote sang USD giữ cố định. Kết quả gồm tài sản LP, tài sản giữ token, IL, phí, chi phí và trạng thái giá cuối kỳ so với khoảng ban đầu.

Biểu đồ chính dùng đúng phản hồi của tình huống vừa chạy. Năm tình huống tham khảo cố định nằm trong mục mở rộng và không đổi khi sửa thanh trượt. Khi chưa bấm chạy sau khi sửa thông số, giao diện vẫn hiển thị lần tính trước và ghi trạng thái này.

Tăng dao động khi giá cuối kỳ cố định có thể chỉ đổi thời gian trong khoảng và phí LP; tài sản HODL cuối kỳ vẫn bằng nhau. Tăng gas không đổi HODL và không làm gì nếu gas gốc bằng 0. Thay đổi nhỏ khó nhận ra qua chiều cao cột, nên đọc thêm số tiền và phần chênh lệch.

### Phân tích độ nhạy

Chức năng này quét 10 mức biến động trong biên người dùng đặt. Mỗi mức dùng GBM, cùng seed, cùng quy tắc tạo đường và volume cố định, nhưng tìm lại khoảng giá tối ưu. Vì thế độ nhạy đánh giá ảnh hưởng của giả định σ tới giải pháp mới; stress test đánh giá vị thế đã chọn dưới tình huống khác. Cả hai không phải kiểm định ngoài mẫu.

## 7 Thử chiến lược với dữ liệu quá khứ

Backtest đi theo giá và volume của các ngày đã quan sát thay vì tạo giá tương lai. Người dùng chọn pool, thời gian, vốn, gas và các giả định nâng cao. Mọi chiến lược trong lần so sánh dùng cùng giai đoạn và cùng đầu vào để tạo đường tài sản có thể đối chiếu.

### Các chiến lược so sánh

| Chiến lược | Quy tắc |
| --- | --- |
| Toàn dải | Dùng khoảng rất rộng theo quy ước hữu hạn của engine để làm mốc thanh khoản trải rộng. |
| Khoảng cố định | Giữ độ rộng log do người dùng đặt; mặc định giao diện là cộng trừ 0,15 log quanh giá mở. |
| Theo biến động | Dùng biến động rolling trễ, mặc định cửa sổ 14 ngày; cập nhật độ rộng và tâm khoảng hằng tuần. |
| Điều chỉnh hằng tuần | Độ rộng theo biến động tại entry; giữ độ rộng đó và đặt lại tâm khoảng theo tuần. |
| Giữ token HODL | Giữ lượng hai token ban đầu, không thu phí LP và không tính gas giao dịch trong mốc so sánh. |

### Tránh dùng thông tin tương lai

Engine chỉ tính đặc trưng từ quan sát trước thời điểm quyết định. Biến động và volume lúc entry dùng dữ liệu trước entry; TVL được ghép lùi theo thời gian có độ trễ công bố giả định một ngày và giới hạn tuổi dữ liệu. Quyết định đặt lại khoảng có hiệu lực với các kỳ tiếp theo, không hồi tố để nhận phí của ngày đã biết.

Ngày thiếu không được tự nội suy hoặc bỏ qua để nối lợi suất. Trang kiểm tra khả năng backtest, gợi ý đoạn liên tục đủ warmup và cho biết ngày thực tế nếu phải thu hẹp. Gợi ý dựa trên độ dài đoạn liên tục, không dựa trên lợi nhuận. Một số pool mức phí 1% có lịch sử thưa nên thời gian hợp lệ có thể rất ngắn.

### Phần quan sát và phần được mô hình hóa

Giá và volume là quan sát lịch sử. Lượng thanh khoản nền được xấp xỉ từ TVL trễ và hệ số concentration, không phải active L của từng block. Phí protocol, gas và ma sát là giả định; backtest tính gas mở, đóng và mỗi lần recenter. Quote sang USD dùng chuỗi tham chiếu lịch sử khi có; USDT sang USD được giả định bằng 1, nên chưa mô hình hóa depeg USDT.

Biểu đồ và bảng trình bày lợi nhuận, chênh lệch HODL, phí, IL, gas, số lần điều chỉnh và mức sụt giảm. Có thể bật tắt chuỗi, chuyển USD hoặc phần trăm và xuất CSV. Xếp hạng là mô tả sau khi đã biết kết quả của giai đoạn đó, không phải bằng chứng chiến lược đứng đầu sẽ tiếp tục tốt hơn.

## 8 Đọc chỉ số và kết quả nghiên cứu

### Các chỉ số cần đọc cùng nhau

| Chỉ số | Ý nghĩa và cách hiểu |
| --- | --- |
| Lợi nhuận ròng LP | Tài sản LP sau phí và chi phí so với vốn ban đầu; có thể âm. |
| Vượt HODL | Chênh lệch LP sau các thành phần liên quan với giữ token, chuẩn hóa theo vốn; khác lợi nhuận ròng LP. |
| Q5 và CVaR5 | Trong kết quả mô phỏng, Q5 là mốc đuôi dưới khoảng 5% của chênh lệch LP với HODL; CVaR5 là trung bình các kết quả xấu nhất của đuôi này. Không phải khoảng tin cậy thống kê. |
| Trong khoảng và từng rời khoảng | Tỷ lệ ngày đủ điều kiện nhận phí khác với tỷ lệ đường có ít nhất một ngày ngoài biên. |
| Drawdown và Sharpe | Ở backtest, drawdown đo sụt giảm từ đỉnh đường tài sản; Sharpe được tính từ lợi suất ngày và quy đổi năm theo giả định của engine. |
| Quy năm và hiệu quả vốn | Lợi nhuận quy năm trên giao diện mô phỏng là ngoại suy tuyến tính, không phải APY cam kết. Hiệu quả vốn so lượng L với vị thế toàn dải trong cùng quy ước. |

### Nghiên cứu lưu trữ

Tab Dữ liệu và Phương pháp hiển thị báo cáo nghiên cứu cùng 25 file tải về như đường tài sản, bảng lợi nhuận tháng, phân rã phí, độ nhạy gas, hệ số hồi quy và chẩn đoán. Lần nghiên cứu lưu trữ hiện tại dùng 8 pool Ethereum ban đầu; 6 pool được thêm vào giao diện không tự được đưa vào kết quả hồi quy cũ.

Quy trình nghiên cứu dựng các cửa sổ thử quá khứ và bảng panel theo pool, độ rộng và policy. Hồi quy OLS với hiệu ứng cố định pool sử dụng sai số Driscoll Kraay HAC; mô hình hiệu ứng cặp riêng dùng để khảo sát fee tier vì fee tier bất biến trong cùng pool. Biến giải thích gồm biến động trễ, log volume, log độ rộng và policy dự kiến.

Hồi quy phân vị ở các mức 0,1, 0,5 và 0,9 dùng bootstrap theo khối thời gian; phép so sánh optimizer với fixed lấy mẫu theo các cửa sổ chung giữa pool để giữ sự ghép cặp. Pipeline còn kiểm tra tính dừng và các chẩn đoán như đa cộng tuyến. Những phương pháp này phục vụ mô tả quan hệ trong mẫu có điều kiện trên mô hình phí.

Các khoảng train, validation và test được khai báo trong cấu hình, nhưng lịch sử giá và volume pool hiện có chưa đủ để xác nhận thiết kế hiệu chỉnh 2022 đến 2024 và kiểm định ngoài mẫu 2025 đến 2026. Mẫu thời gian ít, vintage TVL chưa được xác minh và phí được mô hình hóa, nên các hệ số không chứng minh nhân quả hoặc hiệu quả đầu tư ngoài mẫu.

## 9 Kiến trúc lưu kết quả và vận hành

### Luồng xử lý một yêu cầu

Giao diện HTML, CSS và JavaScript nhận thao tác của người dùng rồi gửi yêu cầu đến FastAPI cùng máy chủ. Pydantic kiểm tra trường, kiểu, giá trị và ngân sách tính toán. Các mô đun dữ liệu chuẩn bị đầu vào; NumPy và mô đun định giá chạy kịch bản, tổng hợp chỉ số; kết quả được ghi an toàn vào tệp và trả về để vẽ SVG, bảng số và trạng thái.

Giới hạn chính gồm vốn từ 1 USD đến 100 triệu USD, thời gian từ 1 đến 365 ngày, từ 1 đến 5.000 đường và tích số đường với số ngày không vượt 1 triệu. Chỉ số đường mẫu phải nhỏ hơn N. Giao diện có thể giới hạn thanh trượt hẹp hơn phạm vi API để thao tác thuận tiện.

### Lưu và tái tạo kết quả

Mỗi lần chạy có run ID tạo từ cấu hình hiệu lực, dữ liệu, phiên bản và thông tin liên quan. Kết quả workbench được lưu trong outputs/workbench; so sánh quá khứ trong outputs/comparisons; snapshot thị trường trong outputs/market_snapshots. Cấu hình đang dùng và mã kết quả gần nhất được nhớ trong trình duyệt.

Cùng dữ liệu, tham số, seed và môi trường tính toán cho phép tạo lại kết quả. Khi dữ liệu hoặc phiên bản đã khác, stress và độ nhạy yêu cầu chạy mới thay vì âm thầm trộn với kết quả cũ. Liên kết chia sẻ chỉ mở được trên máy chủ có cùng run ID; việc sao chép liên kết không tự công bố máy chủ ra Internet.

Trang kết quả xuất PDF tóm tắt, PDF phương pháp và JSON gồm cấu hình, kết quả và provenance. Backtest xuất CSV; mục nghiên cứu tải các file được liệt kê. JSON xuất không chứa toàn bộ dữ liệu thô; cần giữ thư mục data nếu muốn kiểm tra raw, Parquet và source log.

### Cách chạy trên máy hiện tại

Mở thư mục C:\Users\ADMIN\Downloads\uniswap, chạy run.cmd rồi truy cập http://127.0.0.1:8000. Giao diện và API dùng chung máy chủ; tài liệu API ở đường dẫn /docs. Python thực hiện tính toán; Node chỉ cần khi sửa và build giao diện. Hướng dẫn cài thư viện và cập nhật dữ liệu chi tiết nằm trong README của dự án.

### Trải nghiệm và phạm vi sử dụng

Tab và biểu đồ có hiệu ứng ngắn; số liệu thật được hiển thị ngay và chỉ nhấn khi thay đổi. Hiệu ứng tắt theo lựa chọn Giảm chuyển động của thiết bị. Các yêu cầu cũ khi đổi lựa chọn được bỏ qua để không ghi đè kết quả mới hơn.

Dashboard chưa tái dựng từng swap, crossing trong ngày, fee growth của NFT, MEV, JIT hay tác động thị trường. Dữ liệu chụp không thay cho lịch sử thanh khoản toàn bộ; lịch sử tham chiếu dài không có nghĩa pool có cùng độ phủ. Các kết quả phù hợp cho học tập, nghiên cứu giả định và kiểm tra độ nhạy trong phạm vi đã mô tả.

Mã nguồn đối chiếu: frontend/app.js; src/models/price_models.py, v3.py, fees.py, policies.py, workbench.py; src/evaluation/backtest.py, comparison.py, research.py, econometrics.py; src/data/live.py, live_snapshot.py, news.py; data/coverage.json và các cấu hình trong config. Những mô đun này là cơ sở cho nội dung giải thích trong tài liệu.

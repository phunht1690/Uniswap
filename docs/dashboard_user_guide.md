# Hướng dẫn sử dụng RangeLab

RangeLab giúp bạn thử việc cung cấp thanh khoản trên Uniswap: chọn khoảng giá, so sánh với giữ token và kiểm tra các tình huống rủi ro. Các phép tính là mô phỏng theo dữ liệu và giả định được hiển thị; ứng dụng không gửi giao dịch hay sử dụng tiền trong ví.

Cập nhật hướng dẫn ngày **26/10/2026**. [Bản đối chiếu bài luận và dashboard](thesis_alignment_audit.md) giải thích quy tắc và bằng chứng của lần cập nhật này. Tài liệu Word `dashboard_giai_thich_chuc_nang_du_lieu_mo_hinh.docx` và bản đọc `dashboard_explained_vi.md` vẫn là bản **22/10/2026**, chưa mô tả các preset mới; đọc kèm bản đối chiếu. Bài luận Word gốc được giữ nguyên.

## Hiểu nhanh trước khi bắt đầu

| Thuật ngữ | Cách hiểu |
|---|---|
| **Pool thanh khoản** | Nơi giao dịch một cặp token. Cùng một cặp nhưng khác mức phí là các pool khác nhau. |
| **LP** | Cung cấp token cho pool để nhận một phần phí giao dịch. Với Uniswap v3, vị thế chỉ nhận phí khi giá ở trong khoảng giá đã chọn. |
| **HODL / giữ token** | Giữ nguyên lượng token ban đầu, dùng làm mốc so sánh với LP. |
| **IL** | Chênh lệch giữa giá trị token trong LP và giữ token, trước phí và chi phí. Muốn đánh giá kết quả cuối cùng, cần xem thêm phí nhận được, phí mạng và các chi phí khác. |
| **Mức biến động giá** | Mức dao động của giá, không phải mức giá chắc chắn sẽ tăng hoặc giảm. Con số được ghi “mỗi năm” đã được quy đổi theo năm. |
| **Mã tạo lại mô phỏng (seed)** | Mã dùng để tạo các đường giá giả lập. Giữ cùng mã, dữ liệu và cấu hình sẽ cho phép tạo lại kết quả. |

## Bắt đầu trong vài bước

1. Mở **Tổng quan**, tìm cặp token và mức phí bạn muốn xem. Kiểm tra mạng, đơn vị giá và ngày dữ liệu.
2. Chọn **Phân tích** để vào **Tìm khoảng giá LP**. Nhập vốn mô phỏng, số ngày và mức chấp nhận rủi ro. Bạn có thể giữ cấu hình ban đầu để làm quen.
3. Kiểm tra giả định về biến động giá, khối lượng giao dịch, phí mạng và cách điều chỉnh vị thế, rồi bấm chạy tối ưu hóa.
4. Đọc **Kết quả tối ưu hóa**: khoảng giá, lợi nhuận ròng và chênh lệch so với giữ token. Một đường giá mẫu chỉ minh họa một tình huống; các chỉ số trung bình được tính từ nhiều đường mô phỏng.
5. Mở **Kiểm tra rủi ro & dữ liệu** để thử tình huống khác. Dùng **Thử chiến lược trong quá khứ** nếu muốn so sánh trên khoảng dữ liệu đã quan sát.

Giới hạn “ra ngoài khoảng giá” đo tỷ lệ kịch bản có **ít nhất một ngày** giá nằm ngoài khoảng. Chỉ số này khác với tỷ lệ thời gian giá ở trong khoảng và không phải giới hạn số tiền có thể mất. Nếu chưa tìm được khoảng giá phù hợp, hãy xem lại giới hạn rủi ro và giả định trước khi chạy lại.

Khi đổi tab hoặc có kết quả mới, giao diện dùng chuyển động ngắn để bạn dễ theo dõi: đường biểu đồ được vẽ ra, cột mở từ mốc 0 và số liệu mới được nhấn nhẹ. Số liệu luôn hiển thị ngay giá trị thật; hiệu ứng không thay đổi phép tính. Việc kiểm tra API không làm nhấp nháy các giá trị giữ nguyên. Nếu thiết bị bật **Giảm chuyển động**, các hiệu ứng này tự tắt.

## Đọc phần kiểm tra rủi ro

Phần này dùng vị thế và dữ liệu của kết quả đã lưu. Chọn tình huống mẫu để chạy, hoặc chỉnh ba thanh trượt rồi bấm **Chạy kiểm tra rủi ro**:

| Thanh điều chỉnh | Ý nghĩa |
|---|---|
| **Giá cuối kỳ tăng/giảm (%)** | Ấn định giá cuối kỳ so với giá tham chiếu. Ví dụ, −30% nghĩa là giá cuối kỳ bằng 70% giá ban đầu; không có nghĩa giá giảm đều từng ngày. |
| **Mức dao động giá so với ban đầu** | Thay đổi độ dao động trên đường đi tới giá cuối kỳ. Ví dụ, 2× là gấp đôi mức biến động dùng làm mốc. |
| **Phí mạng so với ban đầu** | Nhân mức phí mạng đã đặt trong mô phỏng gốc. Nếu phí gốc bằng 0, tăng hệ số vẫn cho phí bằng 0. |

Biểu đồ **Kết quả tình huống vừa chạy** so sánh tài sản LP và giữ token sau khi tính tình huống bạn chọn. Xem cả số tiền và phần chênh lệch: thay đổi nhỏ có thể khó thấy qua chiều cao cột. Khi chỉnh thanh trượt mà chưa chạy, biểu đồ vẫn thuộc lần chạy trước; trạng thái cạnh biểu đồ cho biết điều này.

Một số trường hợp kết quả thay đổi ít hoặc giữ nguyên là hợp lý:

- Giữ nguyên mọi đầu vào và mã tạo lại thì chạy lại cho cùng kết quả.
- Khi giá cuối kỳ cố định, tăng dao động có thể thay đổi thời gian nhận phí và phí LP, còn giá trị giữ token cuối kỳ vẫn giữ nguyên.
- Phí mạng ảnh hưởng đến LP, không ảnh hưởng đến mốc giữ token không giao dịch. Chi phí còn phụ thuộc cách điều chỉnh vị thế và số lần giao dịch.

Mục mở rộng **So sánh 5 tình huống mẫu cố định** là bảng tham khảo; các tình huống đó giữ nguyên khi bạn chỉnh thanh trượt. Để xem phản hồi của đầu vào mới, đọc biểu đồ tình huống vừa chạy ở phía trên.

**Phân tích độ nhạy** thử nhiều mức biến động và tìm lại khoảng giá ở mỗi mức. Nó trả lời “kết quả nhạy với giả định này đến đâu”, khác với stress test giữ khoảng giá ban đầu làm mốc. Tab **Dữ liệu & Phương pháp** cho biết nguồn, khoảng dữ liệu, ngày thiếu và cách tính.

## Theo dõi tin tức liên quan

Mở **Tin tức & cộng đồng** từ menu hoặc từ màn hình **Kiểm tra rủi ro & dữ liệu**. Bạn có thể đọc tin khi chưa có mô phỏng. Pool ở mục này chỉ dùng để lọc tin, không thay đổi cấu hình hay kết quả đang xem. Dùng bộ lọc nguồn và token để thu hẹp nội dung.

Hai nguồn đang lấy được công khai là **Uniswap Labs Blog** và **diễn đàn quản trị Uniswap**. Diễn đàn chứa đề xuất và thảo luận của cộng đồng; một bài viết không có nghĩa thay đổi đó đã được thông qua. Bài về v4 hoặc hệ sinh thái Uniswap có thể chỉ là bối cảnh cho người dùng v3; đọc nhãn và mở bài gốc trước khi kết luận tin áp dụng cho pool.

Máy chủ kiểm tra blog/diễn đàn mỗi **5 phút**. Giao diện kiểm tra bộ nhớ đệm mỗi 30 giây khi mục tin đang mở. Ngày đăng của bài và lần lấy thành công được hiển thị riêng. Tin lấy trước vẫn có thể được giữ khi nguồn lỗi, kèm trạng thái. Danh sách tối đa 100 tiêu đề trong 90 ngày không bảo đảm bao phủ mọi bài đăng.

**Tình trạng kết nối 2 nguồn** cho biết lần kiểm tra, lần lấy thành công và lỗi nếu có. Bấm **Mở nguồn** để đọc bài trên trang gốc.

Nhãn **Token liên quan** nghĩa là bài nhắc tới một token trong cặp hoặc tên tương ứng; không xác nhận tác động giá. Chỉ có nhãn địa chỉ pool khi tìm thấy đúng địa chỉ. Tin tức không tự sửa đầu vào, chấm điểm cảm xúc hay thay đổi PnL của mô phỏng.

## Thử chiến lược trong quá khứ

Chọn **Bộ cấu hình** trước khi đặt pool và khoảng ngày. Màn hình mới khi chưa có cấu hình lưu mặc định **Tái lập quy tắc nghiên cứu**. Có năm nhóm LP, gồm optimizer, cùng mốc HODL; bạn có thể bật/tắt chuỗi, đổi USD/phần trăm và tải CSV.

| Quy tắc hoặc tham số | Tái lập quy tắc nghiên cứu | Biến thể hằng tuần của giao diện cũ |
| --- | --- | --- |
| Độ rộng fixed | w = 0,20 log | w = 0,15 log |
| Cửa sổ biến động | 30 ngày | 14 ngày |
| Khoảng động | Giữ độ rộng lúc mở; chỉ dời tâm sau khi giá ra ngoài khoảng | Giữ độ rộng lúc mở; xét dời tâm hằng tuần |
| Theo biến động | Giữ độ rộng và khoảng tính tại thời điểm mở | Cập nhật độ rộng và tâm hằng tuần từ biến động trễ |

Preset đặt vốn 50.000 USD, gas 15 USD mỗi đơn vị và seed 42. Bạn vẫn có thể đổi tham số; khi đó màn hình ghi cấu hình tùy chỉnh nếu không còn khớp một preset. Đổi bộ cấu hình chưa sửa kết quả đã tính: bấm chạy lại để áp dụng, và luôn đọc phần **Cấu hình của kết quả đang hiển thị**.

Kết quả comparison v1 đã lưu giữ quy tắc hằng tuần, không được đổi tên thành nghiên cứu sau khi cập nhật. Cấu hình cũ trong trình duyệt cũng được giữ; để chủ động áp dụng quy tắc mới, chọn lại preset nghiên cứu. Với người gọi API, `strategy_mode` phân biệt `research` và `weekly`; body cũ bỏ trường này vẫn dùng weekly cùng mặc định 0,15/14 để tương thích.

Khớp preset chỉ là khớp quy tắc và tham số. Để tái lập số trong bài, còn cần đúng pool, khoảng ngày thực tế, dữ liệu/hash và phiên bản archive. Không coi kết quả mới trên 14 pool là tự động tái lập nghiên cứu lưu trữ 8 pool.

Nếu có ngày thiếu, dùng khoảng liên tục được giao diện gợi ý. Một số pool có lịch sử ngắn; số ngày dùng để ước tính biến động trước ngày bắt đầu cũng được hiển thị. Giai đoạn ngắn cho ít bằng chứng hơn về hiệu quả chiến lược.

Giá và khối lượng giao dịch lấy từ dữ liệu quan sát, nhưng phí nhận được, thanh khoản nền và khớp lệnh vẫn được mô hình hóa theo ngày. Kết quả không tái dựng từng giao dịch hay lợi nhuận thực tế của một vị thế trên chuỗi. Chiến lược đứng đầu chỉ là tốt nhất trong **giai đoạn đã chọn**, không xác nhận hiệu quả tương lai hoặc kiểm định ngoài mẫu.

## Đọc bằng chứng nghiên cứu và cách tái lập

Tab **Dữ liệu & Phương pháp** có phần **Nghiên cứu lưu trữ và quy tắc đang chạy**. Các số được lấy từ file nghiên cứu cùng phiên bản sau khi kiểm tra hash, kèm research ID. Nếu thiếu tệp hoặc hash sai, giao diện báo không đọc được bằng chứng, không thay bằng số minh họa.

Trong bộ nghiên cứu đang đối chiếu, cả 72 tình huống gas hòa vốn có lợi ích tăng thêm trước gas và số đơn vị gas tăng thêm bằng 0. Không phát sinh dời khoảng nên **chưa đủ bằng chứng cho H4**; ngưỡng hòa vốn không xác định, không phải bằng 0. 40 kết quả toàn kỳ có gas 0,06% vốn và trượt giá 0. Chi phí này lấy trực tiếp trên từng hàng; phần dư khi trừ các trung vị độc lập không phải chi phí thực.

Hai ô optimizer trả lời hai câu hỏi khác nhau. Trung vị ΔR toàn kỳ theo pool của optimizer thấp hơn fixed; còn trung bình chênh lệch optimizer − fixed trên cửa sổ 30 ngày là **+1,48 điểm phần trăm**, CI thăm dò 95% **+0,94 đến +2,04**, dựa trên 88 cặp pool/cửa sổ và 11 cửa sổ thời gian. Đây là hai phép đo khác chân trời và cách tổng hợp; không có nghĩa optimizer tốt hơn ở mọi pool hoặc đã được xác nhận ngoài mẫu.

Phần **Tái lập đúng phiên bản và công thức** có ví dụ gọi `/api/v1/workbench/run` với `config` lồng bên trong. Khi đã có kết quả, gửi lại nguyên `config` hiệu lực của bản ghi ở `/api/v1/workbench/runs/{run_id}` và giữ đúng snapshot, dữ liệu, phiên bản, môi trường. `/simulate` là API legacy, không thay cho workbench, comparison hoặc toàn bộ nghiên cứu. Xem [ví dụ PowerShell trong README](../README.md#ví-dụ-tái-lập-một-lần-chạy-workbench).

Khi bật phòng hộ, tài sản LP còn cộng lãi/lỗ hedge. Với `IL_loss = HODL − inventory` là phần thiếu hụt theo quy ước dương, công thức là `ΔR = (phí − IL_loss − gas − ma sát + PnL phòng hộ) / vốn`. Không phòng hộ có thành phần này bằng 0. Không trừ thêm IL khỏi giá trị inventory vì sẽ tính hai lần. Phòng hộ rời rạc theo ngày chưa tính funding, lãi vay, ký quỹ hoặc thanh lý.

## Dữ liệu thị trường cập nhật và kết quả đã lưu

Dữ liệu thị trường được đọc từ nhà cung cấp công khai theo **chu kỳ hiển thị trên giao diện**. Đây là cập nhật định kỳ; không đảm bảo nhận được từng giao dịch, từng khối hay thay đổi ngay tức thì. Giá, khối lượng và tổng vốn có thể có thời điểm cập nhật khác nhau.

Luôn phân biệt **thời điểm dữ liệu tại nguồn** với **thời điểm ứng dụng vừa kiểm tra**. Vừa kiểm tra thành công không có nghĩa nhà cung cấp đã có số liệu mới. Khi báo lỗi kết nối, giới hạn truy cập hoặc dữ liệu cũ, hãy đọc mốc thời gian đi kèm trước khi sử dụng con số đang hiển thị. Tải lại trang cũng không bảo đảm nguồn đã cập nhật.

Các kết quả mô phỏng đã lưu gắn với cấu hình, phiên bản mô hình và bộ dữ liệu riêng. Giá thị trường mới không tự sửa các kết quả này. Muốn đánh giá lại, hãy kiểm tra ngày dữ liệu đầu vào và chạy một mô phỏng mới. Nếu hệ thống yêu cầu chạy lại do dữ liệu hoặc phiên bản đã thay đổi, hãy tạo kết quả mới trước khi kiểm tra rủi ro.

Bạn có thể tải PDF, JSON hoặc CSV ở màn hình tương ứng. Liên kết chia sẻ kết quả chỉ mở được trên máy chủ đang lưu kết quả đó. Biểu tượng **Thông tin** giải thích cách dùng ứng dụng; đây không phải tài khoản giao dịch.

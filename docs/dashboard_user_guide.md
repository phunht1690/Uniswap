# Hướng dẫn sử dụng RangeLab

RangeLab giúp bạn thử việc cung cấp thanh khoản trên Uniswap: chọn khoảng giá, so sánh với giữ token và kiểm tra các tình huống rủi ro. Các phép tính là mô phỏng theo dữ liệu và giả định được hiển thị; ứng dụng không gửi giao dịch hay sử dụng tiền trong ví.

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

Chọn pool, khoảng ngày, vốn và phí mạng, rồi chạy để so sánh các chiến lược trên cùng giai đoạn. Bạn có thể đổi giữa USD và tỷ lệ lợi nhuận, bật/tắt từng đường biểu đồ hoặc tải CSV để kiểm tra chi tiết.

Nếu có ngày thiếu, dùng khoảng liên tục được giao diện gợi ý. Một số pool có lịch sử ngắn; số ngày dùng để ước tính biến động trước ngày bắt đầu cũng được hiển thị. Giai đoạn ngắn cho ít bằng chứng hơn về hiệu quả chiến lược.

Giá và khối lượng giao dịch lấy từ dữ liệu quan sát, nhưng phí nhận được, thanh khoản nền và khớp lệnh vẫn được mô hình hóa theo ngày. Kết quả không tái dựng từng giao dịch hay lợi nhuận thực tế của một vị thế trên chuỗi. Chiến lược đứng đầu chỉ là tốt nhất trong **giai đoạn đã chọn**, không xác nhận hiệu quả tương lai hoặc kiểm định ngoài mẫu.

## Dữ liệu thị trường cập nhật và kết quả đã lưu

Dữ liệu thị trường được đọc từ nhà cung cấp công khai theo **chu kỳ hiển thị trên giao diện**. Đây là cập nhật định kỳ; không đảm bảo nhận được từng giao dịch, từng khối hay thay đổi ngay tức thì. Giá, khối lượng và tổng vốn có thể có thời điểm cập nhật khác nhau.

Luôn phân biệt **thời điểm dữ liệu tại nguồn** với **thời điểm ứng dụng vừa kiểm tra**. Vừa kiểm tra thành công không có nghĩa nhà cung cấp đã có số liệu mới. Khi báo lỗi kết nối, giới hạn truy cập hoặc dữ liệu cũ, hãy đọc mốc thời gian đi kèm trước khi sử dụng con số đang hiển thị. Tải lại trang cũng không bảo đảm nguồn đã cập nhật.

Các kết quả mô phỏng đã lưu gắn với cấu hình, phiên bản mô hình và bộ dữ liệu riêng. Giá thị trường mới không tự sửa các kết quả này. Muốn đánh giá lại, hãy kiểm tra ngày dữ liệu đầu vào và chạy một mô phỏng mới. Nếu hệ thống yêu cầu chạy lại do dữ liệu hoặc phiên bản đã thay đổi, hãy tạo kết quả mới trước khi kiểm tra rủi ro.

Bạn có thể tải PDF, JSON hoặc CSV ở màn hình tương ứng. Liên kết chia sẻ kết quả chỉ mở được trên máy chủ đang lưu kết quả đó. Biểu tượng **Thông tin** giải thích cách dùng ứng dụng; đây không phải tài khoản giao dịch.

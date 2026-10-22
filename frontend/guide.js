/* Static user guide for the application information dialog. */
(() => {
 'use strict';
 globalThis.RangeLabGuide = {
  html: `<section>
<h3>RangeLab dùng để làm gì?</h3>
<p>RangeLab giúp bạn thử cung cấp thanh khoản trên Uniswap: tìm khoảng giá, so sánh với giữ token và kiểm tra rủi ro. Ứng dụng không kết nối ví, dùng tiền thật hay gửi giao dịch. Kết quả là mô phỏng theo dữ liệu và giả định, không phải lợi nhuận được bảo đảm.</p>
<p><b>LP</b> là cung cấp token cho pool để nhận phí khi giá nằm trong khoảng đã chọn. <b>HODL</b> là giữ nguyên lượng token ban đầu để so sánh. <b>IL</b> là phần chênh lệch do giá trị token trong LP khác với giữ token, trước phí và chi phí.</p>
</section>
<section>
<h3>Năm màn hình chính</h3>
<ul>
<li><b>Tổng quan:</b> chọn cặp token, mức phí và xem dữ liệu thị trường.</li>
<li><b>Tìm khoảng giá LP:</b> đặt vốn, thời gian và mức chấp nhận rủi ro.</li>
<li><b>Kết quả tối ưu hóa:</b> đọc khoảng giá, phí, lợi nhuận ròng và chênh lệch với giữ token.</li>
<li><b>Thử chiến lược trong quá khứ:</b> so sánh chiến lược trên cùng khoảng ngày.</li>
<li><b>Kiểm tra rủi ro &amp; dữ liệu:</b> thử tình huống giá, độ nhạy và xem nguồn, phương pháp tính.</li>
</ul>
</section>
<section>
<h3>Bắt đầu trong bốn bước</h3>
<ol>
<li>Chọn pool và mức phí. Cùng cặp token nhưng khác phí là các pool khác nhau.</li>
<li>Nhập vốn và số ngày. Mặc định chọn <b>Dữ liệu thị trường mới</b>; bạn có thể chủ động chuyển sang dữ liệu nghiên cứu đã lưu.</li>
<li>Kiểm tra giả định rồi chạy. Hệ thống chụp và cố định giá, thanh khoản cùng thông tin pool trước khi tính, để kết quả dùng chung một bộ đầu vào.</li>
<li>So sánh LP với giữ token, sau đó thử rủi ro hoặc dữ liệu quá khứ. Một đường giá mẫu không đại diện cho mọi tình huống.</li>
</ol>
<p>Giới hạn ra ngoài khoảng giá là tỷ lệ kịch bản có ít nhất một ngày giá vượt biên; đây không phải giới hạn số tiền có thể mất.</p>
</section>
<section>
<h3>Dữ liệu mới có làm thay đổi kết quả cũ?</h3>
<p>Bảng thị trường và kết quả đã lưu là hai phần riêng. Cập nhật bảng không sửa kết quả cũ; kiểm tra rủi ro luôn dùng dữ liệu gốc của kết quả đó. Muốn đánh giá lại, hãy kiểm tra ngày đầu vào và chạy mô phỏng mới.</p>
<p>Mục tiêu cập nhật: giá và trạng thái pool qua RPC khoảng <b>30 giây</b>, tổng vốn và khối lượng giao dịch khoảng <b>5 phút</b>; giao diện đọc lại khoảng <b>30 giây</b>. Chu kỳ thực tế hiển thị trên giao diện. Nguồn công khai có thể chậm, giới hạn truy cập hoặc lỗi; không bảo đảm nhận từng giao dịch.</p>
<p>Phân biệt thời điểm dữ liệu tại nguồn với lần ứng dụng vừa kiểm tra. Khi báo dữ liệu cũ hoặc lỗi, đọc mốc thời gian đi kèm; tải lại trang không bảo đảm nguồn đã có số mới. Khối mới nhất còn tạm thời và có thể thay đổi trước khi được xác nhận chắc chắn.</p>
</section>
<section>
<h3>Cách đọc kiểm tra rủi ro</h3>
<p>Chọn tình huống mẫu hoặc chỉnh thanh trượt rồi bấm <b>Chạy kiểm tra rủi ro</b>. Giá cuối kỳ ấn định mức tăng/giảm so với ban đầu; mức dao động thay đổi đường đi tới giá đó; phí mạng nhân chi phí gốc.</p>
<p>Biểu đồ chính dùng tình huống vừa chạy. Chỉnh thanh trượt chưa cập nhật kết quả cho tới khi chạy lại. Năm tình huống mẫu cố định trong mục mở rộng chỉ là mốc tham khảo.</p>
<p>Khi giá cuối kỳ giữ nguyên, tăng dao động có thể đổi phí LP nhưng giữ token vẫn bằng nhau. Phí mạng không làm đổi mốc giữ token; phí gốc bằng 0 thì nhân thêm vẫn bằng 0. Thay đổi nhỏ khó thấy trên cột, hãy đọc số tiền. Cùng đầu vào và mã tạo lại sẽ cho cùng kết quả.</p>
<p>Phân tích độ nhạy tìm lại khoảng giá ở từng mức biến động; kiểm tra rủi ro dùng vị thế đã chọn làm mốc.</p>
</section>
<section>
<h3>Tin tức &amp; cộng đồng</h3>
<p>Mở từ menu hoặc tab trong phần rủi ro, không cần chạy mô phỏng. Chọn cặp và lọc nguồn/nội dung; lựa chọn này không sửa vị thế đã lưu. Bài gốc từ Uniswap Blog và diễn đàn quản trị giữ nguyên tiêu đề, ghi riêng thời gian đăng và lấy tin. Nhãn v4 giúp tránh nhầm với v3.</p>
<p>X, Reddit và CryptoPanic có kết nối API chính thức, cần khóa và quyền truy cập trên máy chủ. Bấm <b>Hướng dẫn lấy API</b> để đăng ký; chỉ coi là đã lấy tin khi nguồn báo thành công. Mặc định X kiểm tra mỗi 5 phút, Reddit/CryptoPanic mỗi phút, blog/diễn đàn mỗi 5 phút; trang đọc bộ nhớ đệm mỗi 30 giây. Gói API có thể làm dữ liệu trễ hơn. Tin không tham gia tính mô phỏng.</p>
</section>
<section>
<h3>Giới hạn cần nhớ</h3>
<p>Thử quá khứ dùng giá và khối lượng quan sát, nhưng phí, thanh khoản nền và khớp lệnh vẫn được mô hình hóa theo ngày. Dùng khoảng liên tục được gợi ý nếu thiếu ngày. Xếp hạng chỉ đúng cho giai đoạn đã chọn, không xác nhận hiệu quả tương lai.</p>
<p>Phòng hộ được điều chỉnh mỗi ngày, chưa tính phí vay, phí duy trì hay ký quỹ. Kết quả không tái dựng từng giao dịch thực tế. Bạn có thể tải PDF, JSON hoặc CSV ở màn hình tương ứng; nút <b>Thuật ngữ</b> giải thích thêm các chỉ số.</p>
</section>`
 };
 globalThis.RangeLabGuide.apiHtml = `<div class="dashboard-guide">
<h3>1. Đăng ký X API</h3>
<p>Vào <a class="news-external" href="https://developer.x.com/" target="_blank" rel="noopener noreferrer">X Developer Console</a>, tạo ứng dụng được cấp quyền đọc bài đăng, rồi lấy <b>Bearer Token</b> trong Keys and tokens. Đặt vào <code>X_BEARER_TOKEN</code>. X tính phí theo mức sử dụng; kiểm tra giá và đặt spending limit trong tài khoản trước khi bật. <a class="news-external" href="https://docs.x.com/x-api/getting-started/pricing" target="_blank" rel="noopener noreferrer">Giá và hạn mức X</a>.</p>
<h3>2. Xin quyền Reddit</h3>
<p>Đọc <a class="news-external" href="https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data" target="_blank" rel="noopener noreferrer">hướng dẫn truy cập Reddit</a> và đăng ký Data API cho đúng mục đích. Nghiên cứu học thuật cần Reddit for Researchers. Sau khi được chấp thuận, dùng OAuth token được cấp, hoặc client ID/secret của ứng dụng có quyền. Chỉ lấy tiêu đề và liên kết bài mới trong r/Uniswap.</p>
<p>Điền <code>REDDIT_CLIENT_ID</code>, <code>REDDIT_CLIENT_SECRET</code> và <code>REDDIT_USER_AGENT</code>; nếu được cấp refresh token thì thêm <code>REDDIT_REFRESH_TOKEN</code>. Có thể dùng <code>REDDIT_ACCESS_TOKEN</code> thay thế, nhưng token này cần được thay khi hết hạn. Không cần nhập mật khẩu Reddit.</p>
<h3>3. Lấy token CryptoPanic</h3>
<p>Đăng nhập <a class="news-external" href="https://cryptopanic.com/developers/api/" target="_blank" rel="noopener noreferrer">CryptoPanic API</a>, xác minh email và xem gói API được cấp. Điền <code>CRYPTOPANIC_API_TOKEN</code> và <code>CRYPTOPANIC_PLAN</code> đúng với tài khoản: developer, growth hoặc enterprise. Quyền, phí và độ trễ phụ thuộc gói; có tài khoản chưa đồng nghĩa đã có API thời gian thực.</p>
<h3>4. Đưa khóa vào máy chủ</h3>
<p>Mở tệp <code>.env</code> trong thư mục dự án, điền các trường tương ứng rồi khởi động lại máy chủ bằng <code>run.cmd</code>. Web tự đọc tệp này; biến môi trường có sẵn được ưu tiên. Không đưa khóa vào chat, mã frontend hoặc GitHub.</p>
<p>Mặc định X lấy tối đa 10 bài/lượt, kiểm tra mỗi 300 giây và giới hạn 100 lượt/ngày của phiên máy chủ; đây không phải hạn mức thanh toán và bộ đếm đặt lại khi máy chủ khởi động lại. Reddit và CryptoPanic kiểm tra mỗi 60 giây. Hệ thống lùi thời gian gọi khi bị giới hạn, không tự mua gói hoặc nạp tiền.</p>
<p>Mở <b>Tình trạng kết nối 5 nguồn</b> để xem lần gọi thành công, lỗi và thời điểm thử lại. Chưa có khóa thì chưa có dữ liệu thật từ nguồn đó; các nguồn khác vẫn hoạt động.</p>
</div>`;
})();

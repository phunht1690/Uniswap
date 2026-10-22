/* Static Vietnamese glossary for the dashboard terminology dialog. */
(() => {
 'use strict';
 globalThis.RangeLabGlossary = {
  html: `<div class="dashboard-glossary">
<h3>1. Token và dữ liệu của pool</h3>
<dl>
<dt>LP · cung cấp thanh khoản</dt>
<dd>Cung cấp token để nhận phí giao dịch khi giá nằm trong khoảng đã chọn.</dd>
<dt>Pool thanh khoản</dt>
<dd>Nơi giao dịch một cặp token. Khác mạng hoặc mức phí là các pool riêng.</dd>
<dt>Base / quote · token cơ sở / định giá</dt>
<dd>Giá là số quote cho một base. WETH/USDC giá 3.000 nghĩa là 1 WETH tương đương 3.000 USDC.</dd>
<dt>Fee tier · mức phí</dt>
<dd>Tỷ lệ phí giao dịch của pool; 0,30% tương đương 3 USD trên giao dịch 1.000 USD. LP chỉ nhận một phần phí theo thanh khoản hoạt động của mình; đây không phải lãi suất hay APY.</dd>
<dt>TVL và active-L</dt>
<dd>TVL là tổng giá trị vốn trong pool. Active-L là thanh khoản đang hoạt động tại mức giá hiện tại, dùng để phân bổ phí. Hai số này khác đơn vị và không thay thế trực tiếp cho nhau.</dd>
<dt>Volume · khối lượng giao dịch</dt>
<dd>Tổng giá trị giao dịch, như USD/24 giờ; không phải lợi nhuận hay tổng vốn.</dd>
</dl>
<h3>2. Khoảng giá và kết quả tài chính</h3>
<dl>
<dt>Range · khoảng giá</dt>
<dd>Biên dưới đến biên trên mà vị thế tạo phí. Ngoài khoảng, vị thế còn token nhưng không nhận phí theo mô hình.</dd>
<dt>Độ rộng log · half-width</dt>
<dd>Với giá đầu P và nửa rộng w, biên là P×exp(−w) và P×exp(w). Ví dụ P=100, w=0,1 cho khoảng 90,48–110,52; không phải ±10%.</dd>
<dt>Tick · bước giá</dt>
<dd>Mốc giá dùng để đặt biên vị thế; biên phải theo bước tick của pool. Giá giao dịch có thể nằm giữa các mốc tick. Tick làm tròn trên dashboard chỉ để tham khảo; mô phỏng dùng khoảng liên tục.</dd>
<dt>HODL 50:50 · giữ token</dt>
<dd>Ban đầu chia đều giá trị vốn cho hai token, rồi giữ nguyên số lượng. Không có nghĩa số token bằng nhau hoặc duy trì tỷ trọng 50:50 về sau.</dd>
<dt>Phí nhận được và lợi nhuận ròng</dt>
<dd>Phí là thu nhập giao dịch, chưa trừ chi phí; mô hình không tái đầu tư phí. Ròng là thay đổi tài sản so với vốn ban đầu, đã tính phí, chi phí và phòng hộ nếu có.</dd>
<dt>Impermanent Loss · IL và dấu âm/dương</dt>
<dd>IL = giá trị giữ token − giá trị token trong LP, trước phí và chi phí. Biểu đồ đóng góp hiển thị −IL. Ví dụ LP thiếu 50 USD thì IL=50, tác động=−50 USD. Khi điều chỉnh vị thế, chỉ số có thể đổi dấu; không mặc định khoản chênh lệch sẽ biến mất khi giá quay lại.</dd>
<dt>LP − HODL · chênh lệch với giữ token</dt>
<dd>Tài sản LP ròng trừ giữ token, chia vốn ban đầu. LP −5%, HODL −8% thì chênh lệch +3 điểm phần trăm; LP vẫn lỗ.</dd>
<dt>Gas, trượt giá và bps</dt>
<dd>Gas là phí mạng giả định mỗi đơn vị giao dịch. Trượt giá là chi phí điều chỉnh vị thế. 1 bps=0,01%; 10 bps=0,1%. Phí gas nhập ở đây không phải báo giá giao dịch trực tiếp.</dd>
<dt>Hệ số hiệu quả vốn</dt>
<dd>So sánh lượng thanh khoản tạo ra từ cùng số vốn trong khoảng đã chọn với vị thế toàn dải. Hệ số 20× không có nghĩa lợi nhuận sẽ gấp 20 lần.</dd>
<dt>Quy năm tuyến tính và APY</dt>
<dd>Dashboard quy năm bằng lợi nhuận ròng × 365 / số ngày. Đây là phép ngoại suy theo giả định, không phải APY lãi kép hay mức sinh lời được bảo đảm.</dd>
</dl>
<h3>3. Mô phỏng và chỉ số rủi ro</h3>
<dl>
<dt>Volatility · mức biến động quy năm</dt>
<dd>Độ lệch chuẩn lợi nhuận log ngày nhân căn 365. Mức 100%/năm không có nghĩa giá chắc chắn tăng hoặc giảm 100%.</dd>
<dt>GBM / bootstrap / GARCH</dt>
<dd>GBM dùng mức biến động giả định. Bootstrap lấy lại các đoạn lợi nhuận và khối lượng lịch sử. GARCH ước tính biến động thay đổi từ lịch sử. Cả ba đều là mô hình.</dd>
<dt>Monte Carlo và N</dt>
<dd>Tạo nhiều đường giá để so sánh kết quả; N là số đường. N=300 nghĩa là 300 kịch bản, không phải 300 ngày.</dd>
<dt>Seed · mã tạo lại</dt>
<dd>Cố định cách sinh ngẫu nhiên. Cùng seed, dữ liệu, cấu hình và phiên bản sẽ tạo lại cùng kết quả; không làm dự báo chắc chắn hơn.</dd>
<dt>Path index · đường giá hiển thị</dt>
<dd>Chọn một đường để minh họa, đánh số từ 0. Đường 0 là đường đầu tiên; kết quả trung bình vẫn dùng toàn bộ N đường.</dd>
<dt>Exit probability và active share</dt>
<dd>Exit probability là tỷ lệ kịch bản có ít nhất một ngày ngoài khoảng đang áp dụng, không phải xác suất mất tiền. Active share là tỷ lệ ngày trong khoảng, trung bình qua các đường. Hai chỉ số được tính khác nhau; 1−exit probability là tỷ lệ đường chưa từng ra ngoài khoảng. Chỉ quan sát hằng ngày, chưa đo lần vượt biên trong ngày.</dd>
<dt>Q5 và CVaR5</dt>
<dd>Trong mô phỏng, Q5 là ngưỡng khoảng 5% kết quả chênh lệch LP−HODL thấp nhất; CVaR5 là trung bình nhóm đó. Đây là chênh lệch cuối kỳ trên vốn, không phải lợi nhuận LP riêng. Q5 âm là kém hơn giữ token, chưa chắc LP lỗ tuyệt đối. Chỉ số Q5/CVaR theo ngày trong dữ liệu backtest, nếu có, đo thay đổi từng ngày.</dd>
<dt>Drawdown · mức sụt giảm từ đỉnh</dt>
<dd>Độ giảm tài sản so với đỉnh trước; Max DD là mức sâu nhất. Từ 120 xuống 90 tương đương −25%.</dd>
</dl>
<h3>4. Điều chỉnh vị thế và thử tình huống</h3>
<dl>
<dt>Recenter · đặt lại khoảng giá</dt>
<dd>Chuyển tâm khoảng tới giá mới, có gas và trượt giá. Quyết định cuối ngày áp dụng từ ngày sau; tuân thủ số lần và khoảng cách tối thiểu đã đặt.</dd>
<dt>Threshold · ngưỡng tỷ trọng</dt>
<dd>Điều chỉnh khi giá trị token base lệch khỏi 50% đến ngưỡng chọn. Ngưỡng 10 điểm % nghĩa là chạm 40% hoặc 60%, nếu đủ điều kiện điều chỉnh.</dd>
<dt>Hedge · phòng hộ hằng ngày</dt>
<dd>Dùng vị thế bán đối ứng để giảm nhạy cảm với giá, điều chỉnh theo ngày và giới hạn số lần. Tính gas, trượt giá khi mở/điều chỉnh/đóng; chưa tính phí vay, funding, ký quỹ hay giới hạn khả năng thanh toán.</dd>
<dt>Stress test và phân tích độ nhạy</dt>
<dd>Stress ấn định giá cuối kỳ, mô phỏng đường đi có điều kiện và bắt đầu từ khoảng giá cùng quy tắc đã lưu; không tìm lại khoảng theo cú sốc đã biết. Độ nhạy dùng GBM để thay mức biến động và tối ưu lại từng điểm, giữ khối lượng trung bình và seed.</dd>
</dl>
<h3>5. Dữ liệu quá khứ và thời điểm cập nhật</h3>
<dl>
<dt>Backtest · thử chiến lược trong quá khứ</dt>
<dd>Dùng giá, khối lượng quan sát nhưng phí và thanh khoản nền được mô hình hóa theo ngày. Không tái dựng từng giao dịch thực tế; xếp hạng chỉ thuộc giai đoạn đã chọn.</dd>
<dt>OOS · kiểm định ngoài mẫu</dt>
<dd>Đánh giá trên dữ liệu chưa dùng chọn tham số. Đứng đầu bảng quá khứ chưa chứng minh OOS; dữ liệu hiện có chưa xác nhận kiểm định ngoài mẫu.</dd>
<dt>Live và snapshot đã cố định</dt>
<dd>Live đọc thị trường định kỳ. Trước mô phỏng, giá, thanh khoản và thông tin pool được lưu cố định; cập nhật bảng live không sửa kết quả cũ. Stress dùng đúng dữ liệu gốc.</dd>
<dt>Thời điểm nguồn, lần kiểm tra và trạng thái</dt>
<dd>Thời điểm block khác lần ứng dụng lấy dữ liệu thành công. Khi nguồn lỗi, số gần nhất có thể cũ; đọc mốc thời gian và cảnh báo. Chu kỳ hiển thị không bảo đảm nhận từng giao dịch; block mới nhất còn tạm thời.</dd>
</dl>
</div>`
 };
})();

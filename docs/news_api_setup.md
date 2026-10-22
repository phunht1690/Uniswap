# Kết nối API tin tức X, Reddit và CryptoPanic

RangeLab đã có adapter đọc API chính thức cho cả ba nguồn. Bạn cần tự đăng ký quyền và lấy khóa của tài khoản mình; mã nguồn không có khóa dùng chung. Chưa có khóa thì dashboard báo thiếu cấu hình, không hiển thị tin giả. Các bước dưới đây được kiểm tra theo tài liệu công khai ngày 22/10/2026.

## X

1. Đăng nhập [Developer Console](https://developer.x.com/), hoàn thành đăng ký nhà phát triển và tạo ứng dụng được cấp quyền đọc.
2. Trong **Keys and tokens**, lấy **Bearer Token**, điền vào `X_BEARER_TOKEN` ở `.env`.
3. Kiểm tra quyền **Recent Search**, tín dụng và **spending limit** trong tài khoản. X tính phí theo mức sử dụng; không giả định tài khoản thông thường có quyền API miễn phí. RangeLab không tự mua tín dụng hoặc thay đổi gói.

Nguồn chính thức: [Recent Search](https://docs.x.com/x-api/posts/search/quickstart/recent-search), [giá và hạn mức](https://docs.x.com/x-api/getting-started/pricing).

RangeLab tìm bài chứa Uniswap/được trả bởi truy vấn tài khoản Uniswap, bỏ repost và reply, lấy một trang mỗi lượt. Sau lần thành công, dùng `since_id` để hỏi bài mới. Mặc định tối đa 10 bài/lượt, 300 giây/lượt và 100 lượt/ngày trong bộ nhớ của phiên máy chủ. Bộ đếm này đặt lại khi khởi động lại, không thay thế hạn mức chi tiêu tại X. Một trang có thể bỏ sót bài khi lưu lượng lớn; không cam kết đầy đủ hoặc cập nhật tức thì.

## Reddit

1. Đọc [Developer Platform & Accessing Reddit Data](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) và chọn đường đăng ký đúng mục đích. Trang chính thức liên kết tới [biểu mẫu xin Data API](https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164).
2. Nếu dùng dữ liệu cho nghiên cứu học thuật, đăng ký **Reddit for Researchers** theo liên kết trong hướng dẫn chính thức. Không coi app/token tự tạo là đã được phê duyệt cho mọi mục đích.
3. Khi được cấp quyền, dùng OAuth access token, hoặc client ID/secret của ứng dụng được duyệt; thêm refresh token nếu luồng cấp quyền có cung cấp. Điền User-Agent có định danh ứng dụng, ví dụ `windows:rangelab-news:1.0 (by /u/TEN_CUA_BAN)`.

Cấu hình lựa chọn A, token có sẵn:

```dotenv
REDDIT_ACCESS_TOKEN=
REDDIT_USER_AGENT=windows:rangelab-news:1.0 (by /u/TEN_CUA_BAN)
```

Lựa chọn B, thông tin ứng dụng được chấp thuận:

```dotenv
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_REFRESH_TOKEN=
REDDIT_USER_AGENT=windows:rangelab-news:1.0 (by /u/TEN_CUA_BAN)
```

Không cần mật khẩu Reddit. Với lựa chọn B, backend lấy/đổi OAuth token trong bộ nhớ; không có refresh token thì dùng application-only OAuth nếu tài khoản được phép. Token lựa chọn A hết hạn cần được thay thủ công. Tham khảo [OAuth của Reddit](https://github.com/reddit-archive/reddit/wiki/OAuth2) cùng chính sách hiện hành ở trên.

Backend chỉ đọc 25 bài mới từ **r/Uniswap**, mặc định mỗi 60 giây. Không đăng bài, bình luận, bỏ phiếu hoặc nhập nội dung vào mô hình mô phỏng. Danh sách Reddit được thay bằng lần lấy mới; không tạo kho lưu trữ Reddit trên đĩa.

## CryptoPanic

1. Đăng nhập [CryptoPanic API](https://cryptopanic.com/developers/api/), xác minh email nếu trang yêu cầu.
2. Xem [các gói API](https://cryptopanic.com/developers/api/plans), chọn quyền phù hợp và lấy token được cấp. Không giả định gói miễn phí có luồng tức thời; kiểm tra phí, hạn mức và độ trễ được ghi trong tài khoản.
3. Điền `CRYPTOPANIC_API_TOKEN` và `CRYPTOPANIC_PLAN` đúng với gói thực tế: `developer`, `growth` hoặc `enterprise`.

Adapter dùng endpoint chính thức `https://cryptopanic.com/api/{plan}/v2/posts/`, `auth_token`, public mode và bộ lọc UNI. Token chỉ được gửi từ backend đến CryptoPanic, không trả về trình duyệt. Mặc định kiểm tra mỗi 60 giây, một trang; dữ liệu có thể trễ theo gói. Nếu báo 403, kiểm tra plan, quyền và quota; backend không thử lách qua endpoint/gói khác.

## Điền cấu hình và chạy

Tệp dùng trên máy hiện tại: `C:\Users\ADMIN\Downloads\uniswap\.env`. Web tự đọc tệp này khi khởi động; biến môi trường đã có được ưu tiên. Chỉ dùng giá trị của chính bạn, không sao chép khóa từ người khác.

```dotenv
X_BEARER_TOKEN=
X_POLL_SECONDS=300
X_MAX_RESULTS=10
X_MAX_REQUESTS_PER_DAY=100

REDDIT_ACCESS_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_REFRESH_TOKEN=
REDDIT_USER_AGENT=
REDDIT_POLL_SECONDS=60

CRYPTOPANIC_API_TOKEN=
CRYPTOPANIC_PLAN=developer
CRYPTOPANIC_POLL_SECONDS=60
```

Điền xong thì dừng máy chủ cũ và chạy lại `run.cmd`. Mở **Tin tức & cộng đồng → Tình trạng kết nối 5 nguồn**. Phân biệt:

| Trạng thái | Ý nghĩa |
|---|---|
| Chưa có khóa API | Chưa đủ các trường cấu hình; không gọi API đó. |
| Đang chờ nguồn | Đã có cấu hình nhưng chưa có lần gọi thành công. |
| Đã lấy dữ liệu | API đã trả kết quả hợp lệ, có thể không có bài mới. |
| Cần kiểm tra khóa | Token sai hoặc hết hạn. |
| Chưa đủ quyền / hạn mức | Nhà cung cấp từ chối do quyền, gói hoặc tín dụng. |
| Chờ hạn mức API | Lùi lần gọi theo Retry-After/reset, không gọi dồn. |
| Tạm dừng theo giới hạn | Đã đạt số lượt X trong ngày của phiên máy chủ. |

Trang đọc cache mỗi 30 giây khi mục tin đang mở; bấm Kiểm tra lại cũng chỉ đọc cache. Máy chủ dùng lịch chung cho mọi người xem, không tạo thêm lượt API cho từng pool/người dùng. Blog/diễn đàn vẫn kiểm tra mỗi 5 phút.

Khóa được đọc ở backend và `.env` đã nằm trong `.gitignore`. Không gửi khóa vào chat, frontend, URL chia sẻ hay GitHub. Bài viết có ngày đăng riêng với lần kiểm tra nguồn; nội dung tin tức không tự thay đổi kết quả LP, PnL, stress hoặc backtest.

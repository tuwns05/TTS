# Hướng dẫn sử dụng GPHI-TTS

## 1. Khởi động và kích hoạt

Khi mở app lần đầu, quá trình nhận diện phần cứng và load model chạy nền. Nếu chưa có license hợp lệ, hai trang **Tạo giọng nói** và **Nhân bản giọng** bị khóa và app chuyển sang trang **Thanh toán**.

Để kích hoạt:

1. Mở **Thanh toán**.
2. Dán mã vào ô **Mã kích hoạt**.
3. Chọn **Kích hoạt**.
4. Kiểm tra tên khách hàng, gói, ngày thanh toán và ngày hết hạn.

License được xác minh offline bằng chữ ký Ed25519 và chỉ hợp lệ với MAC thiết bị ghi trong mã. App kiểm tra lại license trước mỗi tác vụ được bảo vệ. Nếu thời gian hệ thống bị lùi so với lần sử dụng trước, license sẽ tạm khóa cho đến khi ngày giờ hợp lệ.

## 2. Chọn thiết bị chạy model

Mở **Cài đặt**, chọn một chế độ rồi nhấn **Áp dụng**:

- **Tự động**: ưu tiên CUDA/PyTorch khi GPU phù hợp; fallback sang CPU/ONNX nếu khởi tạo GPU thất bại.
- **GPU**: bắt buộc dùng NVIDIA CUDA; nếu không khả dụng app báo lỗi và không âm thầm chuyển CPU.
- **CPU**: dùng ONNX, phù hợp với máy không có GPU NVIDIA.

Thẻ trạng thái hiển thị model, backend và thiết bị thực sự đang hoạt động. Việc đổi thiết bị sẽ unload và load lại model trong worker nền.

## 3. Tạo giọng nói

1. Mở **Tạo giọng nói**.
2. Nhập/dán văn bản hoặc chọn **Mở tệp** để nhập `TXT`, `SRT`, `DOCX`, `PDF`.
3. Chọn giọng dựng sẵn hoặc hồ sơ giọng clone.
4. Chọn phong cách **Tự nhiên**, **Tin tức** hoặc **Kể chuyện**.
5. Điều chỉnh tốc độ, cao độ và âm lượng nếu cần.
6. Chọn **Tạo giọng nói**.

Trong khi xử lý, có thể chọn **Dừng tác vụ**. Văn bản không có giới hạn 10.000 ký tự cũ, nhưng nội dung dài sẽ cần nhiều thời gian và bộ nhớ hơn.

### Nhập tài liệu

| Định dạng | Cách xử lý |
|---|---|
| TXT | Đọc UTF-8/UTF-8 BOM, UTF-16 hoặc CP1258. |
| SRT | Bỏ số thứ tự, timestamp và thẻ định dạng; giữ nội dung phụ đề. |
| DOCX | Đọc đoạn văn và nội dung bảng. |
| PDF | Trích xuất lớp văn bản; không OCR PDF scan/ảnh. |

PDF có mật khẩu, PDF chỉ chứa ảnh, tệp hỏng hoặc định dạng khác sẽ bị từ chối với thông báo thân thiện.

## 4. Nghe và xuất audio

Sau khi tổng hợp thành công:

- Nhấn nút phát để **Play/Pause** và nút dừng để trở về đầu.
- Bấm hoặc kéo trên waveform để tua.
- Chọn **Xuất WAV** hoặc **Xuất MP3**, sau đó chọn vị trí lưu.

Audio chỉ được giữ trong bộ nhớ cho đến khi tổng hợp bản mới hoặc đóng app. Tệp chỉ được ghi khi người dùng chủ động xuất.

## 5. Nhân bản giọng

1. Mở **Nhân bản giọng**.
2. Đặt tên hồ sơ, tối đa 80 ký tự.
3. Chọn mẫu `WAV`, `MP3`, `FLAC`, `M4A` hoặc `OGG`. Khả năng đọc từng codec phụ thuộc libsndfile trong bản đóng gói; WAV/FLAC là lựa chọn ổn định nhất.
4. Chọn **Tạo hồ sơ** và chờ VieNeu trích xuất đặc trưng giọng.

Mẫu cần có ít nhất 6 giây phần có tiếng; khuyến nghị 6–8 giây, rõ giọng và ít tạp âm. Nếu dài hơn 8 giây, VieNeu chỉ sử dụng 8 giây đầu. App cảnh báo khi tín hiệu bị clipping.

Quy trình enrollment chuyển audio sang mono, loại DC offset, chuẩn hóa peak và tạo tệp đặc trưng `.npz`. Tệp WAV tạm được xóa sau xử lý; hồ sơ chỉ lưu speaker embedding và reference codes trong thư mục dữ liệu cục bộ.

Tại danh sách hồ sơ có thể:

- chọn hồ sơ để dùng ở trang tạo giọng;
- nghe thử;
- đổi tên;
- xóa hồ sơ và artifact tương ứng.

## 6. Thanh toán

Trang **Thanh toán** nhận họ tên, email, gói và MAC thiết bị. Khi gửi, app POST JSON đến endpoint cấu hình với các trường:

```json
{
  "name": "Tên khách hàng",
  "email": "user@example.com",
  "plan": "yearly",
  "price": 1990000,
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

UI hiển thị các gói tháng, quý, 6 tháng, năm và trọn đời theo giá cấu hình. Tuy nhiên contract test hiện chỉ cho gửi gói tháng/năm và vẫn gửi giá tạm cố định `1.990.000 VNĐ`; các gói còn lại sẽ bị validation từ chối. Đây là giới hạn của tích hợp backend hiện tại, cần hoàn thiện trước phát hành thương mại. Việc gửi yêu cầu thanh toán cần kết nối đến server và không liên quan đến quá trình tổng hợp offline.

## 7. Dữ liệu cục bộ

Mặc định app dùng `%LOCALAPPDATA%\VietnameseTTSDesktop`:

- `data/license.json`: mã license và mốc thời gian kiểm tra gần nhất.
- `data/voice_profiles/profiles.json`: chỉ mục hồ sơ giọng.
- `data/voice_profiles/artifacts/*.npz`: đặc trưng giọng clone.
- `cache/`: cache runtime/xác minh model.
- `logs/vntts.log`: log xoay vòng 10 MB, giữ theo số ngày cấu hình.

Sao lưu toàn bộ `data/voice_profiles` nếu cần chuyển/khôi phục hồ sơ trên cùng môi trường. License gắn với thiết bị nên sao chép `license.json` sang máy khác không làm license hợp lệ.

## 8. Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Không tìm thấy CUDA | Cập nhật driver NVIDIA hoặc chọn CPU trong **Cài đặt**. |
| Chế độ tự động chuyển sang CPU | Xem trạng thái runtime; GPU có thể thiếu VRAM hoặc load PyTorch thất bại. |
| App báo thiếu/sai model | Cài lại artifact đầy đủ; không tách riêng EXE khỏi thư mục `GPHI-TTS`. |
| Không phát được audio | Kiểm tra thiết bị output mặc định và thử mở lại app. |
| PDF không có nội dung | Chạy OCR bằng công cụ khác rồi nhập lại PDF/TXT. |
| Mẫu giọng bị từ chối | Dùng file hợp lệ, có ít nhất 6 giây giọng nói rõ và tránh clipping. |
| License sai thiết bị | Yêu cầu mã được phát hành đúng MAC đang hiển thị trên trang Thanh toán. |
| Phát hiện thời gian không hợp lệ | Đồng bộ ngày giờ Windows, không xóa/sửa thủ công trạng thái license. |
| Không gửi được thanh toán | Kiểm tra endpoint, mạng và dịch vụ backend. |

Nếu cần gửi log cho hỗ trợ, chỉ gửi `vntts.log` sau khi tự kiểm tra nội dung. App không chủ động ghi toàn văn người dùng, nhưng log vẫn là dữ liệu chẩn đoán của máy.

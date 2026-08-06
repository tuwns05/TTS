# Hướng dẫn triển khai Production

Tài liệu này là runbook và tiêu chí phát hành cho bản production Windows. **Repository hiện chưa sẵn sàng phát hành production**: mới hoàn thành Giai đoạn 1, chưa tích hợp ba engine thật, playback, Model Manager, kiểm tra license hoặc công cụ đóng gói.

Không dùng `FakeTTSEngine`, source checkout hoặc virtual environment của developer làm bản phân phối cho người dùng cuối.

## 1. Điều kiện bắt buộc trước khi phát hành

Chỉ bắt đầu tạo bản production sau khi hoàn tất tối thiểu:

- Tích hợp và kiểm thử các adapter VieNeu-TTS v3-Turbo, VieNeu-TTS v2-Turbo và Kokoro-Vietnamese.
- Xác nhận capability runtime, lifecycle load/unload và fallback giữa các engine.
- Hoàn thiện nhập liệu MVP, DSP và playback Play/Pause/Stop.
- Hoàn thiện Model Manager, checksum và xác nhận người dùng trước khi tải/xóa model.
- Kiểm thử tổng hợp khi máy đã ngắt Internet.
- Kiểm tra license của code, dependency, model và voicepack cho quyền phân phối.
- Chọn và kiểm chứng một công cụ đóng gói: PyInstaller hoặc Nuitka.
- Xác định versioning, kênh phát hành, ký mã và quy trình rollback.

Cho đến khi các gate này đạt, mọi gói build chỉ được ghi là `development` hoặc `internal`, không phải production.

## 2. Môi trường build chuẩn

- Máy build Windows x64 sạch hoặc runner CI Windows cô lập.
- Python 3.11 đúng phiên bản đã khóa cho release.
- Dependency lock có phiên bản và hash; không build trực tiếp từ dependency range chưa khóa.
- Không dùng `.venv`, cache pip hoặc model từ máy developer làm đầu vào ngầm.
- Build từ commit/tag sạch, có version release rõ ràng.
- Model và native runtime được lấy từ nguồn đã duyệt, kèm checksum và license.

Trước build, phải ghi lại:

```text
Application version
Git commit/tag
Python version
Dependency lock/checksum
Qt/PySide6 version
Engine adapter và model version
Build tool và version
Windows SDK/runtime liên quan
```

## 3. Cấu hình production

Đặt môi trường production bằng biến môi trường hoặc cấu hình được đóng gói:

```powershell
$env:VNTTS_ENVIRONMENT = "production"
$env:VNTTS_LOG_LEVEL = "INFO"
```

Production phải tuân thủ:

- Không dùng đường dẫn tuyệt đối của máy build.
- Dữ liệu người dùng nằm dưới app-data theo nền tảng, không ghi cạnh executable trong `Program Files`.
- Model, cache, database, log và mẫu giọng có thư mục riêng.
- Không đóng gói mẫu giọng hoặc dữ liệu người dùng từ máy build.
- `FakeTTSEngine` không được đăng ký hoặc hiển thị trong release chính thức.
- Console log development bị tắt; file log vẫn xoay vòng và có retention giới hạn.
- Không bật traceback/diagnose chứa biến cục bộ trong log production.

Layout runtime dự kiến trên Windows:

```text
%LOCALAPPDATA%\VietnameseTTSDesktop\
├── models\                 # model do Model Manager quản lý
└── data\
    ├── voice_profiles\     # hồ sơ giọng theo engine
    ├── voice_samples\      # dữ liệu nhạy cảm, chỉ lưu cục bộ
    ├── cache\               # dữ liệu có thể tái tạo
    ├── logs\
    └── app.db
```

## 4. Dependency và model

### Dependency Python

- Tạo lock riêng cho CPU, VieNeu PyTorch/CUDA, VieNeu GGUF và Kokoro nếu các backend không thể cùng tồn tại an toàn.
- Pin version sau khi integration test; không tự động lấy bản mới nhất khi build release.
- Quét license và lỗ hổng dependency trước mỗi release.
- Không thêm framework web, dịch vụ cloud hoặc API TTS trực tuyến.

### Model

- Không tự động tải model khi chưa có xác nhận người dùng.
- Mỗi model cần metadata: engine ID, version, nguồn, license, kích thước và checksum.
- Tải vào tệp tạm, xác minh checksum rồi mới chuyển thành model khả dụng.
- Phát hiện file thiếu/hỏng trước khi load.
- Không coi cache hoặc tải dở là model hợp lệ.

## 5. Đóng gói ứng dụng

PyInstaller và Nuitka hiện chỉ là hai ứng viên. Chỉ viết/chạy lệnh build production sau khi Giai đoạn 8 chọn công cụ và thêm script được review vào repository.

Pipeline đóng gói phải thực hiện theo thứ tự:

1. Tạo môi trường build Python 3.11 sạch.
2. Cài dependency từ lock có hash.
3. Chạy unit, UI và integration test.
4. Build executable bằng script version-controlled.
5. Xác minh Qt plugin, native DLL và resource YAML/QSS được đóng gói.
6. Khởi động ứng dụng trên máy Windows sạch không có Python.
7. Kiểm thử tải/kiểm tra model theo luồng có xác nhận.
8. Ngắt Internet và chạy toàn bộ luồng tổng hợp/playback.
9. Ký executable/installer nếu phát hành công khai.
10. Tạo checksum cho artifact phát hành.

Không đưa ra lệnh PyInstaller/Nuitka cụ thể trong tài liệu này cho đến khi script chính thức tồn tại; tránh tạo một build tưởng là thành công nhưng thiếu DLL hoặc resource.

## 6. Ma trận kiểm thử phát hành

Tối thiểu phải kiểm tra:

| Nhóm | Tiêu chí |
|---|---|
| Startup | Mở ứng dụng không cần Python cài sẵn; không load model ngay khi startup. |
| Engine | Load/unload từng adapter, chuyển engine, lỗi thiếu model và fallback có giải thích. |
| Hardware | GPU/CUDA khả dụng, không CUDA, CPU-only, RAM/VRAM thấp và lựa chọn thủ công. |
| Offline | Sau khi model đã tải, chặn mạng vẫn tổng hợp và phát được. |
| Documents | TXT encoding, DOCX, PDF có lớp text, file lớn và cảnh báo PDF scan. |
| Audio | Speed/pitch/volume chỉ áp dụng một lần; Play/Pause/Stop và cancellation ổn định. |
| Voice Cloning | Chỉ bật theo capability; dữ liệu gắn engine; xóa cả profile và tệp. |
| Privacy | Không có text/audio/mẫu giọng trong log hoặc network traffic. |
| Storage | Thiếu dung lượng, checksum sai, tải dở, model hỏng và xóa model. |
| Upgrade | Nâng cấp không làm mất cấu hình, model hoặc hồ sơ giọng. |
| Uninstall | Không xóa dữ liệu người dùng nếu chưa hỏi rõ; có hướng dẫn xóa dữ liệu cục bộ. |

Mọi lỗi chặn startup, mất dữ liệu, upload ngoài ý muốn, crash khi không có GPU hoặc không hoạt động offline đều là release blocker.

## 7. Quyền riêng tư và bảo mật

- Không gửi văn bản, audio hoặc mẫu giọng lên máy chủ.
- Model Manager là thành phần duy nhất được phép truy cập mạng, chỉ khi người dùng yêu cầu.
- Log production không chứa payload người dùng, dữ liệu nhị phân, token hoặc đường dẫn nhạy cảm không cần thiết.
- Mẫu giọng và hồ sơ clone chỉ lưu cục bộ và có thao tác xóa rõ ràng.
- Không bật telemetry mặc định. Nếu sau này đề xuất telemetry, phải có thiết kế và sự đồng ý riêng của người dùng.
- Artifact phát hành phải có checksum; installer/executable nên được ký mã.

## 8. Phát hành

Mỗi release cần:

- Tag/version bất biến và release notes.
- Artifact, checksum và chữ ký nếu áp dụng.
- Danh sách engine/model tương thích.
- License/notice đi kèm.
- Yêu cầu hệ thống đã được kiểm chứng, không suy diễn từ một máy phát triển.
- Hướng dẫn tải model lần đầu và sử dụng offline.
- Hướng dẫn backup/xóa hồ sơ giọng.
- Danh sách giới hạn đã biết.

Không phát hành model nếu điều khoản nguồn không cho phép redistribution; trong trường hợp đó, Model Manager phải tải từ nguồn chính thức sau khi người dùng xác nhận.

## 9. Rollback và hỗ trợ

- Giữ artifact/checksum của bản ổn định trước đó.
- Không tự downgrade schema hoặc model nếu không có migration an toàn.
- Khi rollback executable, bảo toàn dữ liệu người dùng và cấu hình tương thích.
- Nếu release có lỗi bảo mật hoặc mất dữ liệu, dừng phân phối và công bố hướng xử lý rõ ràng.
- Log phục vụ hỗ trợ phải được người dùng chủ động cung cấp; không tự động upload.

## 10. Checklist phê duyệt production

- [ ] Working tree/tag sạch và version chính xác.
- [ ] Dependency/model license đã duyệt.
- [ ] Dependency lock và checksum đã lưu.
- [ ] Unit, UI và integration test đều pass.
- [ ] Build thành công trên môi trường Windows sạch.
- [ ] Cả GPU và CPU fallback đã kiểm tra.
- [ ] Offline test pass sau khi model được tải.
- [ ] Không có fake engine trong danh sách production.
- [ ] Không có payload nhạy cảm trong log.
- [ ] Không có network call ngoài Model Manager có xác nhận.
- [ ] Upgrade, rollback và uninstall đã kiểm tra.
- [ ] Artifact có checksum và release notes.

Chỉ khi toàn bộ mục bắt buộc đạt yêu cầu mới được gắn nhãn bản build là production.


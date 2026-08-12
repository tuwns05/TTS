# Đóng gói production Windows

## Phạm vi bản production hiện tại

Bản này chỉ đăng ký **VieNeu-TTS v3 Turbo** và đóng gói các chức năng đang có:

- tổng hợp giọng preset, phong cách đọc và voice cloning;
- nhập TXT/SRT/DOCX/PDF;
- phát, tạm dừng, dừng và tua audio;
- xuất WAV/MP3;
- lưu hồ sơ giọng trong `%LOCALAPPDATA%\VietnameseTTSDesktop`.

Không đăng ký, tải hoặc fallback sang VieNeu v2/Kokoro. Production luôn dùng
ONNX int8 trên CPU để chạy được trên Windows x64 không có GPU. Model được load
trên worker sau khi cửa sổ mở; UI hiển thị trạng thái kiểm tra/load model.

## Những thứ đã chuẩn bị

- PyInstaller `onedir` spec tại `packaging/vntts.spec`.
- Script build Windows tại `scripts/build_production.ps1`.
- Inno Setup script tùy chọn tại `packaging/windows/installer.iss`.
- Dependency đầu vào đã pin và lock đầy đủ SHA-256 tại
  `requirements/production.in` và `requirements/production.lock`.
- Script lấy ba snapshot model đã pin tại `scripts/prepare_vieneu_v3.py`.
- Bundle local có manifest, size và SHA-256 cho từng tệp.
- Runtime kiểm tra checksum trước khi load và kiểm tra `vieneu==3.2.4`.
- Hugging Face/Transformers bị ép offline, tắt telemetry và không có remote fallback.
- Frozen build tự chuyển sang môi trường `production` và đọc model từ `_internal`.
- Artifact portable ZIP được tạo kèm checksum SHA-256.

Model binary không commit vào Git. Máy build phải chạy script chuẩn bị model;
bundle hiện hành nằm tại `resources/models/vieneu-v3` và được PyInstaller đưa
vào artifact.

## Yêu cầu máy build

- Windows 10/11 x64 sạch.
- Python 3.11 x64 có lệnh `py -3.11`.
- Tối thiểu 15 GB trống để chứa wheel cache, venv, build và artifact.
- Internet chỉ cần khi tạo model bundle hoặc cài dependency lần đầu.
- Inno Setup 6 chỉ cần nếu muốn tạo file `setup.exe`.

Không build từ `.venv` phát triển. Script dùng `.venv-build` riêng.

## 1. Chuẩn bị model thật

Nếu máy đang có đủ snapshot trong Hugging Face cache:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --local-files-only
```

Nếu cache chưa có, cho phép script tải đúng revision đã pin:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py
```

Kiểm tra lại toàn bộ checksum:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --validate-only
```

Không copy thủ công model từ cache khác và không sửa `manifest.json`.

## 2. Chạy release gate

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
git status --short
```

Chỉ build từ commit/tag đã xác định. Ruff hiện có một số cảnh báo legacy ngoài
phạm vi production; không được bỏ qua lỗi mới trong các tệp production vừa sửa.

## 3. Build portable production

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_production.ps1 -RecreateEnvironment
```

Script sẽ:

1. tạo `.venv-build` bằng Python 3.11;
2. cài dependency từ lock bằng `--require-hashes`;
3. xác minh manifest/checksum model;
4. chạy PyInstaller ở chế độ `onedir`;
5. kiểm tra EXE và model manifest trong artifact;
6. tạo ZIP và file SHA-256 trong `release`.

Kết quả chính:

```text
dist/GPHI-TTS/GPHI-TTS.exe
release/GPHI-TTS-0.1.0-win-x64.zip
release/GPHI-TTS-0.1.0-win-x64.zip.sha256
```

Phải phân phối cả thư mục `GPHI-TTS`; không được lấy riêng file EXE.

## 4. Tạo installer tùy chọn

Cài Inno Setup 6 và bảo đảm `iscc.exe` có trong `PATH`, sau đó chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_production.ps1 `
  -BuildInstaller
```

Installer được tạo trong `release`. Ký số `setup.exe` và ZIP nếu phát hành công
khai; script hiện chưa chứa certificate/signing key.

## 5. Smoke test offline bắt buộc

Thực hiện trên Windows sạch, không cài Python và không có Hugging Face cache:

1. Tắt Wi-Fi/rút mạng trước khi mở ứng dụng.
2. Mở `GPHI-TTS.exe`; cửa sổ phải hiện ngay và báo đang kiểm tra/load model.
3. Chờ trạng thái `Sẵn sàng`; danh sách giọng preset phải xuất hiện.
4. Tổng hợp một câu; xác nhận audio 48 kHz phát được và xuất WAV/MP3 được.
5. Thử nhập ít nhất một TXT và một DOCX/PDF có text.
6. Nếu phát hành voice cloning, tạo hồ sơ từ audio mẫu rồi tổng hợp thử.
7. Dùng công cụ giám sát mạng để xác nhận tiến trình không gửi request.
8. Đóng/mở lại ứng dụng; dữ liệu người dùng vẫn nằm trong `%LOCALAPPDATA%`.

Crash, treo UI trong lúc load, thiếu giọng preset, request mạng hoặc không tổng
hợp được khi offline đều là release blocker.

## 6. Trước khi phát hành công khai

- Cập nhật version ở `pyproject.toml`, build script và Inno script cùng lúc.
- Hoàn tất license của chính ứng dụng và inventory license của toàn bộ wheel.
- Giữ `packaging/licenses/THIRD_PARTY_NOTICES.txt` trong artifact.
- Viết release notes, yêu cầu Windows x64 và dung lượng cài đặt thực tế.
- Lưu artifact phiên bản trước để rollback.
- Ký số artifact bằng certificate của đơn vị phát hành.

Model v3 và VieNeu SDK dùng Apache-2.0; model card yêu cầu giữ attribution cho
project/model package. MOSS và toàn bộ dependency vẫn cần được chủ phát hành
duyệt license riêng trước khi phân phối công khai.

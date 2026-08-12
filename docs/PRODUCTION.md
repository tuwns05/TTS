# Đóng gói production Windows

## Phạm vi bản production hiện tại

Bản này chỉ đăng ký **VieNeu-TTS v3 Turbo** và đóng gói các chức năng đang có:

- tổng hợp giọng preset, phong cách đọc và voice cloning;
- nhập TXT/SRT/DOCX/PDF;
- phát, tạm dừng, dừng và tua audio;
- xuất WAV/MP3;
- lưu hồ sơ giọng trong `%LOCALAPPDATA%\VietnameseTTSDesktop`.

Không đăng ký, tải hoặc fallback sang VieNeu v2/Kokoro. Một bundle VieNeu v3 Turbo
chứa cả đường chạy PyTorch/CUDA trên GPU và ONNX int8 trên CPU. Khi mở ứng dụng,
chế độ `Tự động` ưu tiên GPU NVIDIA tương thích có ít nhất 6 GB VRAM; nếu CUDA
không dùng được hoặc load GPU thất bại, ứng dụng tự chuyển sang ONNX/CPU. Model
được load trên worker sau khi cửa sổ mở nên UI không bị chặn.

Trang **Cài đặt** là nơi chọn model và chế độ `Tự động`, `GPU` hoặc `CPU`, sau đó
nhấn **Load model**. Chọn GPU rõ ràng trên máy không có CUDA sẽ báo lỗi thay vì
âm thầm dùng CPU. Trang **Tạo giọng nói** chỉ hiển thị model, backend và thiết bị
đang thực sự hoạt động; model không còn được chọn tại trang này.

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
- Frozen build tự chuyển sang môi trường `production`, đọc model từ `_internal`
  và mang theo PyTorch CUDA 12.8 lẫn ONNX Runtime CPU.
- Artifact portable ZIP được tạo kèm checksum SHA-256.

Model binary không commit vào Git. Máy build phải chạy script chuẩn bị model;
bundle hiện hành nằm tại `resources/models/vieneu-v3` và được PyInstaller đưa
vào artifact.

## Yêu cầu máy build

- Windows 10/11 x64 sạch.
- Python 3.11 x64 có lệnh `py -3.11`.
- Tối thiểu 25 GB trống để chứa CUDA wheel, venv, build và artifact.
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
4. xác minh bản PyTorch CUDA 12.8 được cài trong môi trường build;
5. chạy PyInstaller ở chế độ `onedir`;
6. kiểm tra EXE, model manifest và chạy tổng hợp thật bằng ONNX/CPU;
7. nếu máy build có CUDA, chạy thêm tổng hợp thật bằng PyTorch/GPU;
8. tạo ZIP và file SHA-256 trong `release`.

Kết quả chính:

```text
dist/GPHI-TTS/GPHI-TTS.exe
release/GPHI-TTS-0.1.0-win-x64.zip
release/GPHI-TTS-0.1.0-win-x64.zip.sha256
```

Phải phân phối cả thư mục `GPHI-TTS`; không được lấy riêng file EXE.

Nếu Windows Application Control của máy build chặn chạy EXE mới tạo tại bước
smoke-test, artifact trong `dist\GPHI-TTS` vẫn đã được PyInstaller tạo xong. Có
thể đóng gói tiếp artifact đó mà không build lại bằng:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_production.ps1 `
  -PackageExistingArtifact `
  -SkipArtifactSmokeTest
```

Hai tùy chọn này chỉ dùng khi log đã có dòng `Build complete!` và lỗi xảy ra tại
`Start-Process`. ZIP tạo theo cách này chưa được kiểm thử thực thi trên máy build,
vì vậy bắt buộc chạy mục smoke-test offline trên một máy Windows cho phép chạy EXE
trước khi phát hành. Không nên tắt hoặc tìm cách vượt qua chính sách bảo mật của máy.

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
3. Chờ trạng thái `Sẵn sàng`; trang chính phải ghi đúng `GPU · <tên GPU> · PyTorch`
   hoặc `CPU · ONNX` và danh sách giọng preset phải xuất hiện.
4. Vào **Cài đặt**, chọn CPU rồi **Load model**; quay lại trang chính và xác nhận
   runtime đổi thành CPU/ONNX. Trên máy có NVIDIA CUDA, thử tương tự với GPU.
5. Trên máy không có CUDA, chọn GPU và xác nhận có thông báo không tìm thấy GPU;
   sau đó chọn CPU và load được bình thường.
6. Tổng hợp một câu; xác nhận audio 48 kHz phát được và xuất WAV/MP3 được.
7. Thử nhập ít nhất một TXT và một DOCX/PDF có text.
8. Nếu phát hành voice cloning, tạo hồ sơ từ audio mẫu rồi tổng hợp thử.
9. Dùng công cụ giám sát mạng để xác nhận tiến trình không gửi request.
10. Đóng/mở lại ứng dụng; dữ liệu người dùng vẫn nằm trong `%LOCALAPPDATA%`.

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

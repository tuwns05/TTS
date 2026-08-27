# Đóng gói và phát hành GPHI-TTS trên Windows

## 1. Phạm vi artifact

Bản `0.1.0` đóng gói theo PyInstaller `onedir`, chỉ đăng ký VieNeu-TTS v3-Turbo và bao gồm:

- tổng hợp giọng dựng sẵn, 3 phong cách đọc và voice cloning;
- GPU/PyTorch CUDA 12.8 và CPU/ONNX trong cùng bundle;
- nhập TXT/SRT/DOCX/PDF;
- DSP tốc độ/cao độ/âm lượng;
- playback, seek, WAV/MP3 export;
- license offline, payment request, trang cài đặt/liên hệ;
- model VieNeu v3 đã pin và xác minh checksum.

VieNeu v2/Kokoro không được đăng ký, tải hoặc bundle. Không phát hành riêng `GPHI-TTS.exe`; phải phát hành cả thư mục `GPHI-TTS` hoặc installer.

## 2. Yêu cầu máy build

- Windows 10/11 x64 sạch.
- Python 3.11 x64 có lệnh `py -3.11`.
- Tối thiểu khoảng 25 GB trống cho wheel CUDA, model, venv và artifact.
- Internet khi cài dependency/chuẩn bị model lần đầu.
- Inno Setup 6 và `iscc.exe` trong `PATH` nếu cần installer.

Build dùng `.venv-build`, tách khỏi `.venv` development. Dependency production được khóa kèm SHA-256 tại `requirements/production.lock`.

## 3. Chuẩn bị model

Cài môi trường development/VieNeu trước, sau đó:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py
```

Nếu ba snapshot đã có đầy đủ trong Hugging Face cache:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --local-files-only
```

Xác minh lại bundle:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --validate-only
```

Kết quả phải có `resources/models/vieneu-v3/manifest.json` và `hub/`. Không copy thủ công snapshot hoặc sửa manifest sau khi tạo. Chi tiết tại [MODEL_DISTRIBUTION.md](MODEL_DISTRIBUTION.md).

## 4. Release gate trước build

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --validate-only
git status --short
```

Build từ commit/tag đã xác định. Worktree phải được xem xét để không vô tình phát hành thay đổi hoặc secret chưa commit.

Xuất inventory license từ đúng môi trường production đã cài dependency:

```powershell
.\.venv-build\Scripts\python.exe .\scripts\export_production_licenses.py
```

Giải quyết mọi cảnh báo thiếu license trước release.

## 5. Build portable

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_production.ps1 -RecreateEnvironment
```

Script thực hiện:

1. tạo lại `.venv-build` Python 3.11;
2. cài pip/version và dependency bằng `--require-hashes`;
3. cài project không kéo dependency ngoài lock;
4. xác nhận PyTorch CUDA 12.8;
5. xác minh model manifest/checksum;
6. chạy PyInstaller với `packaging/vntts.spec`;
7. kiểm tra EXE, manifest và `sea_g2p.bin`;
8. chạy tổng hợp thật WAV + MP3 bằng CPU/ONNX;
9. nếu máy có CUDA, chạy thêm smoke GPU/PyTorch;
10. tạo ZIP và SHA-256.

Artifact:

```text
dist/GPHI-TTS/GPHI-TTS.exe
release/GPHI-TTS-0.1.0-win-x64.zip
release/GPHI-TTS-0.1.0-win-x64.zip.sha256
```

Chỉ chạy `dist/GPHI-TTS/GPHI-TTS.exe` hoặc EXE nằm trong thư mục ZIP đã giải
nén đầy đủ. Không chạy `build/vntts/GPHI-TTS.exe` và không copy riêng EXE;
ứng dụng cần thư mục `_internal` nằm ngay bên cạnh. Phải đợi Windows giải nén
hoàn tất trước khi chạy EXE và nên giải nén vào một đường dẫn ngắn.

### Đóng gói lại artifact có sẵn

Chỉ dùng khi PyInstaller đã báo `Build complete!` nhưng Windows Application Control/antivirus chặn chạy smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_production.ps1 `
  -PackageExistingArtifact `
  -SkipArtifactSmokeTest
```

Artifact này chưa được xác minh thực thi trên máy build và bắt buộc smoke test thủ công trên máy Windows khác trước phát hành. Không dùng `-PackageExistingArtifact` cùng `-RecreateEnvironment`.

## 6. Build installer

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_production.ps1 `
  -BuildInstaller
```

Kết quả:

```text
release/GPHI-TTS-0.1.0-win-x64-setup.exe
```

Installer cài per-user (`PrivilegesRequired=lowest`) và có tùy chọn shortcut desktop. Ký số cả setup và ZIP trước khi phát hành công khai.

## 7. Smoke test offline bắt buộc

Thực hiện trên Windows sạch, không Python, không Hugging Face cache và ngắt mạng:

1. Kiểm tra SHA-256 của ZIP rồi giải nén toàn bộ.
2. Mở `GPHI-TTS.exe`; xác nhận chỉ có một instance và UI hiển thị bình thường.
3. Xác nhận license chưa có sẽ khóa trang tạo/clone và điều hướng sang Thanh toán.
4. Kích hoạt bằng license staging đúng MAC; đóng/mở lại và xác nhận trạng thái còn hợp lệ.
5. Chờ model sẵn sàng; runtime phải hiện `GPU · <tên> · PyTorch` hoặc `CPU · ONNX`.
6. Trong **Cài đặt**, ép CPU rồi tổng hợp; trên máy CUDA thử thêm GPU.
7. Trên máy không CUDA, ép GPU phải báo lỗi rõ ràng; chuyển CPU phải hoạt động lại.
8. Tổng hợp đủ 3 phong cách, thử speed/pitch/volume và hủy một tác vụ.
9. Play/pause/stop/seek, đổi output device nếu có, xuất WAV và MP3 rồi mở bằng player khác.
10. Nhập TXT, SRT, DOCX và PDF có text; PDF scan phải báo không có nội dung.
11. Tạo profile từ mẫu 6–8 giây, nghe thử, dùng để tổng hợp, đổi tên, khởi động lại và xóa.
12. Xác nhận profile/giọng không rò rỉ vào log.
13. Dùng công cụ giám sát mạng: pipeline TTS/model/license không tạo request.
14. Bật mạng và kiểm tra payment với backend staging; xác nhận payload/response/error state.
15. Kiểm tra **Liên hệ → Điều khoản & giấy phép** và thư mục `_internal/licenses`.

Crash, treo UI, checksum sai, model tải mạng, thiếu preset voice, export hỏng, license bypass hoặc mất dữ liệu profile là release blocker.

## 8. Checklist trước khi phát hành

### Bắt buộc thay cấu hình/test placeholder

- Thay `TEST_LICENSE_PUBLIC_KEY` bằng public key production; private key không được nằm trong source, build machine log hoặc artifact.
- Thay endpoint localhost bằng HTTPS production hoặc chủ động tắt payment trong build không có backend.
- Chốt contract backend: server phải tự xác định giá; không tin `price` do client gửi.
- Điền chính xác `manufacturer`, `address`, `phone`, `website`, `support_email`, `copyright`.
- Đồng bộ version ở `pyproject.toml`, `scripts/build_production.ps1` và `packaging/windows/installer.iss`.

### Pháp lý và supply chain

- Thêm license/EULA của chính ứng dụng.
- Chạy `export_production_licenses.py` trên đúng lock environment.
- Giữ `THIRD_PARTY_NOTICES.txt` và toàn bộ component licenses trong artifact.
- Hoàn tất nghĩa vụ LGPL/source offer cho Qt/PySide6, LAME/lameenc, libsndfile và thành phần tương ứng.
- Duyệt license/model card của VieNeu, MOSS tokenizer, voice assets và mọi wheel.
- Không phát hành khi `LGPL_SOURCE_OFFER_TEMPLATE.txt` còn placeholder.
- Lưu lock file, manifest model, SBOM/inventory, checksum và build log cùng release.

### Bảo mật và vận hành

- Dùng TLS và xác thực server cho payment; kiểm tra rate limit, timeout và xử lý PII.
- Không log payment payload, license payload, text hoặc dữ liệu giọng.
- Ký Authenticode cho EXE/setup/installer và bảo vệ signing key.
- Quét malware, dependency vulnerability và secret trước phát hành.
- Test cài mới, nâng cấp, gỡ cài đặt và rollback.
- Lưu artifact phiên bản trước và release notes.
- Xác nhận dung lượng cài đặt và yêu cầu driver thực tế trên trang tải.

## 9. Cấu trúc artifact

```text
GPHI-TTS/
├── GPHI-TTS.exe
└── _internal/
    ├── resources/models/vieneu-v3/
    │   ├── manifest.json
    │   └── hub/
    ├── licenses/
    ├── sea_g2p/sea_g2p.bin
    └── ... runtime DLL/PYD ...
```

Model bundle là read-only. Dữ liệu người dùng, cache và log luôn ghi dưới `%LOCALAPPDATA%\VietnameseTTSDesktop`, không ghi vào thư mục cài đặt.

## 10. Rollback và hỗ trợ

- Mỗi release giữ ZIP/setup, SHA-256, tag, manifest model và release notes.
- Khi rollback, không xóa app-data; profile/license tương thích cần được kiểm tra trước downgrade.
- Thu log chẩn đoán tại `logs/vntts.log`, nhưng yêu cầu người dùng xem lại trước khi gửi.
- Nếu model bundle hỏng, phân phối lại toàn bộ artifact đã ký; không hướng dẫn tải/copy từng file model ngoài luồng kiểm soát.

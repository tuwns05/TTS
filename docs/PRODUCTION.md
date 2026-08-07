# Hướng dẫn Production

> Repository chưa sẵn sàng production: Giai đoạn 2 mới hoàn thành ở mức adapter và unit test, chưa bundle/test model thật. Không phân phối `FakeTTSEngine`, source checkout hoặc `.venv` cho người dùng cuối.

## 1. Release gate

Trước khi đóng gói phải hoàn tất:

- Integration test ba adapter với model/runtime đã pin; lifecycle, load failure và fallback đã test trên máy sạch.
- TXT/DOCX/PDF có text, chunking, DSP và Play/Pause/Stop.
- Model Manager cho v2/Kokoro: xác nhận tải, tiến độ/hủy, checksum, phát hiện hỏng và xóa.
- Bundle v3 cùng codec/runtime/license để first-run offline.
- Kiểm tra license code, dependency, model và voicepack.
- Chọn và kiểm chứng PyInstaller hoặc Nuitka.
- Unit, UI, integration và offline test đều pass.

Build chưa đạt các mục trên chỉ được gắn nhãn `development/internal`.

## 2. Môi trường build

- Windows x64 sạch hoặc CI runner cô lập.
- Python 3.11 đúng version release.
- Build từ commit/tag sạch.
- Dependency lock có version và hash.
- Model/runtime lấy từ revision đã pin, không lấy từ cache developer.

Ghi lại trong build metadata:

```text
App/Git version
Python, Qt/PySide6 version
Dependency lock checksum
Engine/model revision
Build tool/version
```

## 3. Cấu hình production

```powershell
$env:VNTTS_ENVIRONMENT = "production"
$env:VNTTS_LOG_LEVEL = "INFO"
```

- Không hard-code đường dẫn máy build.
- Dữ liệu ghi được nằm trong `%LOCALAPPDATA%\VietnameseTTSDesktop`.
- V3 bundled nằm trong vùng read-only của installer; v2/Kokoro nằm trong app-data.
- Chọn `vieneu-v3` mặc định và load local bằng worker.
- Không đăng ký `FakeTTSEngine`.
- Không bật console log, `diagnose` hoặc traceback chứa dữ liệu nhạy cảm.
- Không bundle model cache, log, text, audio hoặc mẫu giọng của developer.

Chi tiết model: [MODEL_DISTRIBUTION.md](MODEL_DISTRIBUTION.md).

## 4. Pipeline build/release

1. Tạo môi trường Python 3.11 sạch.
2. Cài dependency từ lock có hash.
3. Chuẩn bị snapshot v3, codec/runtime và manifest/checksum.
4. Chạy unit, UI và integration test.
5. Build bằng script version-controlled.
6. Xác minh Qt plugin, native DLL, YAML/QSS, model và license.
7. Cài trên Windows sạch không có Python/Hugging Face cache.
8. Chặn mạng; xác nhận v3 load và tổng hợp ngay lần đầu.
9. Xác nhận v2/Kokoro không tự tải và chỉ tải sau consent.
10. Ký artifact nếu phát hành công khai; tạo checksum và release notes.

Chưa cung cấp lệnh PyInstaller/Nuitka cho đến khi repository có script build đã được kiểm chứng.

## 5. Kiểm thử phát hành

| Nhóm | Điều kiện |
|---|---|
| Startup | Không cần Python/Internet; v3 load nền, UI responsive. |
| Engine | Load/unload/chuyển engine; fallback có lý do; không crash khi thiếu GPU. |
| Offline | Không network khi startup/load/synthesize v3. |
| Optional models | v2/Kokoro chỉ tải sau consent; checksum và tải dở được xử lý. |
| Documents | TXT encoding, DOCX, PDF text, file lớn, cảnh báo PDF scan. |
| Audio | Effects chỉ áp dụng một lần; Play/Pause/Stop/cancel ổn định. |
| Cloning | Chỉ bật theo capability; profile gắn engine và xóa được. |
| Privacy | Không payload trong log/network; không telemetry mặc định. |
| Upgrade | Không mất model, cấu hình hoặc hồ sơ giọng. |
| Uninstall | Không xóa dữ liệu người dùng nếu chưa xác nhận. |

Crash startup, mất dữ liệu, network ngoài consent hoặc không chạy offline là release blocker.

## 6. Artifact và vận hành

Mỗi release cần:

- Version/tag, release notes, artifact checksum và chữ ký nếu áp dụng.
- Danh sách engine/model tương thích và yêu cầu hệ thống đã kiểm chứng.
- License/third-party notices.
- Hướng dẫn v3 offline, tải v2/Kokoro và xóa dữ liệu/voice profile.
- Artifact ổn định trước đó để rollback.

Rollback executable phải bảo toàn dữ liệu người dùng và chỉ thực hiện migration có đường quay lại an toàn. Log hỗ trợ chỉ được upload khi người dùng chủ động cung cấp.

## 7. Checklist production

- [ ] Commit/tag và version chính xác.
- [ ] Dependency/model license đã duyệt.
- [ ] Dependency lock, model revision và checksum đã lưu.
- [ ] Unit/UI/integration test pass.
- [ ] Build/cài đặt trên Windows sạch thành công.
- [ ] First-run v3 offline pass, không có Hugging Face cache.
- [ ] GPU failure có v3 CPU fallback nếu bản build công bố hỗ trợ.
- [ ] V2/Kokoro không tự tải.
- [ ] Không có fake engine hoặc payload nhạy cảm.
- [ ] Upgrade/rollback/uninstall đã kiểm tra.
- [ ] Artifact có checksum, notices và release notes.

Chỉ gắn nhãn production khi toàn bộ mục bắt buộc đạt yêu cầu.

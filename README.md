# Ứng dụng TTS Desktop Offline Tiếng Việt

Ứng dụng desktop chuyển văn bản tiếng Việt thành giọng nói và phát âm thanh trực tiếp trên máy người dùng. Sau khi model cần thiết đã được tải về, quá trình tổng hợp hằng ngày được thiết kế để hoạt động offline, không gửi văn bản, mẫu giọng hoặc âm thanh lên máy chủ.

## Trạng thái dự án

> **Giai đoạn 1 — Khung ứng dụng MVP đã hoàn thành.** Ứng dụng hiện chạy được bằng fake engine để kiểm tra cấu hình, kiến trúc, worker nền và giao diện PySide6. Chưa tích hợp SDK TTS thật hoặc playback thật.

Ứng dụng được phát triển và kiểm thử trước hết trên một máy Windows x64 có Intel Core 5 210H, RAM 16 GB và NVIDIA GeForce RTX 4050 Laptop GPU 6 GB. Đây là cấu hình mục tiêu ban đầu, không phải yêu cầu tối thiểu cố định; khả năng của từng engine vẫn phải được kiểm tra trong quá trình tích hợp thực tế.

## Phạm vi chức năng

Đã có trong Giai đoạn 1:

- Package Python theo bốn nhóm Presentation, Application, Domain và Infrastructure.
- Cửa sổ PySide6 nhập văn bản, chọn fake engine/giọng và thu thập speed, pitch, volume.
- `BaseTTSEngine`, `EngineRegistry`, `EngineFactory` và fake engine tạo audio NumPy.
- Phát hiện phần cứng cục bộ; PyTorch là dependency tùy chọn.
- Khuyến nghị engine theo policy YAML, không khóa lựa chọn người dùng.
- Worker `QThreadPool`/`QRunnable`, trạng thái UI, cancellation hợp tác và lỗi thân thiện.
- Cấu hình, đường dẫn dữ liệu theo nền tảng, Loguru và bộ unit/UI test.

Phạm vi sản phẩm theo các giai đoạn tiếp theo:

- Chuyển văn bản tiếng Việt thành giọng nói.
- Chọn giọng theo engine đang sử dụng.
- Điều chỉnh tốc độ đọc từ `0.5x` đến `2.0x`, cao độ từ `-12` đến `+12` semitone và âm lượng.
- Phát âm thanh trực tiếp với Play, Pause và Stop.
- Chạy tổng hợp, nhập tài liệu lớn và DSP trong worker nền để không khóa giao diện.
- Voice Cloning chỉ trên engine xác nhận có capability tương ứng tại runtime.
- Phát hiện phần cứng, khuyến nghị engine kèm lý do và cho phép người dùng chọn lại thủ công.
- Quản lý model cục bộ; chỉ tải model sau khi người dùng xác nhận.

Không thuộc phạm vi MVP hiện tại:

- Xuất tệp WAV hoặc MP3. Thư mục cache chỉ phục vụ dữ liệu tạm nội bộ, không phải chức năng xuất file.
- OCR cho PDF scan/PDF chỉ chứa hình ảnh.
- Streaming nâng cao; phát từng chunk ngay khi hoàn thành là hướng tối ưu sau MVP.

## Đầu vào văn bản

- Văn bản được gõ trực tiếp.
- Tệp `.txt`, có xử lý encoding.
- Tệp `.docx`, dự kiến đọc bằng `python-docx`.
- Tệp `.pdf` có lớp văn bản, dự kiến đọc bằng PyMuPDF.

Bản đầu chỉ hỗ trợ PDF có lớp văn bản. PDF scan hoặc PDF chỉ chứa hình ảnh chưa được hỗ trợ vì chưa có OCR. Văn bản dài phải được chia chunk theo giới hạn của từng engine, ưu tiên ranh giới đoạn rồi đến câu và không làm mất dấu câu.

## Đầu ra âm thanh

Đầu ra MVP là âm thanh được tổng hợp, xử lý speed/pitch/volume rồi đưa trực tiếp vào `PlaybackService` để Play/Pause/Stop. Việc xuất WAV/MP3 chưa thuộc phạm vi MVP.

## Engine và phân tầng phần cứng

Ứng dụng vẫn được thiết kế để thích nghi với nhiều cấu hình, dù quá trình phát triển hiện chỉ dùng một máy mục tiêu. Các ngưỡng CPU, RAM và VRAM nằm trong policy cấu hình, không hard-code trong UI và có thể hiệu chỉnh từ kết quả tích hợp thực tế.

| Phân tầng dự kiến | Engine | Ghi chú | Voice Cloning |
|---|---|---|---|
| Máy có GPU tương thích hoặc CPU khá | `VieNeu-TTS v3-Turbo` | Ưu tiên backend PyTorch/GPU; chỉ chọn sau khi preflight tài nguyên thành công | Capability được xác định khi tích hợp adapter/runtime |
| Máy tầm trung | `VieNeu-TTS v2-Turbo` | Có thể dùng backend GGUF nếu phù hợp | Capability được xác định khi tích hợp adapter/runtime |
| Máy yếu, chỉ CPU | `Kokoro-Vietnamese` | Dùng voicepack dựng sẵn | Không hỗ trợ zero-shot Voice Cloning |

Trên máy mục tiêu, thứ tự thử mặc định là v3-Turbo trên RTX 4050 → v2-Turbo/GGUF → Kokoro-Vietnamese. Mỗi bước phải kiểm tra model, backend, bộ nhớ khả dụng và kết quả load; lỗi load sẽ kích hoạt gợi ý fallback thay vì làm ứng dụng dừng. Ứng dụng chỉ khuyến nghị, không tự ép đổi engine; người dùng luôn có thể chọn thủ công.

## Hoạt động offline

- Internet chỉ cần khi người dùng yêu cầu tải model lần đầu hoặc chủ động kiểm tra cập nhật model.
- `Model Manager` là thành phần duy nhất được phép truy cập mạng cho các tác vụ model và phải xin xác nhận trước khi tải.
- Sau khi model hợp lệ đã có trên máy, nhập văn bản, tổng hợp, DSP, phát âm thanh và quản lý hồ sơ giọng phải hoạt động khi ngắt Internet.
- Mỗi adapter phải được kiểm thử offline trong giai đoạn tích hợp để phát hiện network call ngầm khi load hoặc tổng hợp.

## Quyền riêng tư của Voice Cloning

- Mẫu giọng, metadata và dữ liệu clone chỉ được lưu cục bộ.
- Hồ sơ giọng gắn với `engine_id`; không giả định dùng chéo giữa các engine.
- Không upload mẫu giọng và không ghi nội dung văn bản hoặc dữ liệu mẫu nhạy cảm vào log.
- Người dùng có thể xóa hồ sơ cùng tệp liên quan.
- UI khóa toàn bộ chức năng cloning khi capability runtime không hỗ trợ; không có fake/fallback cloning cho Kokoro-Vietnamese.
- Định dạng, thời lượng mẫu tối thiểu/tối đa và backend cần thiết cho từng engine VieNeu phải được xác minh khi tích hợp adapter.

## Công nghệ dự kiến

| Hạng mục | Công nghệ dự kiến |
|---|---|
| Ngôn ngữ và GUI | Python 3.11, PySide6 (Qt6) |
| TTS | VieNeu-TTS v3-Turbo, VieNeu-TTS v2-Turbo, Kokoro-Vietnamese |
| DSP và playback | NumPy, SoundFile, librosa, pydub, sounddevice |
| Đọc tài liệu | python-docx, PyMuPDF, thư viện chuẩn Python |
| Lưu trữ cục bộ | SQLite, SQLAlchemy, YAML |
| Phát hiện phần cứng | PyTorch, psutil, py-cpuinfo |
| Kiểm thử và logging | pytest, pytest-qt, loguru |
| Đóng gói Windows | Đánh giá PyInstaller và Nuitka trong giai đoạn kiểm thử/phát hành; chưa chốt lựa chọn |

## Cài đặt cho người dùng cuối

Chưa có bản phát hành hoặc bộ cài. Người dùng cuối chưa cần chạy lệnh Python; hướng dẫn cài đặt sẽ được công bố sau khi engine, license và phương án đóng gói được xác nhận trong quá trình tích hợp/phát hành.

Không nên xem các lệnh phát triển bên dưới là quy trình cài sản phẩm hoàn chỉnh.

## Thiết lập môi trường phát triển

Sử dụng Python 3.11; phiên bản Python ngoài khoảng `>=3.11,<3.12` không được hỗ trợ trong giai đoạn hiện tại.

1. Tạo môi trường ảo Python 3.11:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```

2. Cài package và dependency nền tảng:

   ```powershell
   python -m pip install -r requirements/base.txt
   ```

3. Cài dependency kiểm thử:

   ```powershell
   python -m pip install -r requirements/dev.txt
   ```

4. Chạy test:

   ```powershell
   python -m pytest
   ```

5. Chạy ứng dụng:

   ```powershell
   python -m vntts
   # hoặc: python -m vntts.main
   ```

Chưa có lệnh tải model vì Giai đoạn 1 không tích hợp model thật hoặc Model Manager.

## Tài liệu triển khai

- [Development](docs/DEVELOPMENT.md): thiết lập Python 3.11, chạy ứng dụng/test, cấu hình đường dẫn, logging và xử lý sự cố cho developer.
- [Production](docs/PRODUCTION.md): release gate, cấu hình production, dependency/model, đóng gói, kiểm thử, bảo mật và rollback. Repository hiện chưa đủ điều kiện phát hành production.

## Cấu trúc dự án

Các thư mục chính đã triển khai trong Giai đoạn 1:

```text
vietnamese-tts-desktop/
├── requirements/          # dependency nền tảng và kiểm thử
├── src/vntts/             # mã nguồn package ứng dụng
│   ├── presentation/      # PySide6, ViewModel và Qt worker
│   ├── application/       # service và use case điều phối
│   ├── domain/            # contract và model nghiệp vụ thuần Python
│   ├── infrastructure/    # fake engine và detector phần cứng
│   ├── config/            # cấu hình và policy có thể thay đổi
│   └── utils/             # tiện ích kỹ thuật dùng chung, không chứa nghiệp vụ
├── tests/                 # unit test và UI test
└── docs/                  # tài liệu kiến trúc
```

Giải thích đầy đủ cho **từng thư mục** và cây đích chi tiết nằm trong [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#11-cấu-trúc-thư-mục-đích).

## Roadmap

- [x] **Giai đoạn 1 — Khung ứng dụng MVP:** PySide6, cấu hình, logging, exception, worker nền, fake engine và giao diện cơ sở.
- [ ] **Giai đoạn 2 — Engine Adapter Layer:** ba adapter, capability, registry, factory và lifecycle engine.
- [ ] **Giai đoạn 3 — Nhập liệu đa nguồn:** TXT, DOCX, PDF có text, normalization và chunking.
- [ ] **Giai đoạn 4 — Audio và điều khiển giọng:** speed, pitch, volume, sample rate và ghép audio.
- [ ] **Giai đoạn 5 — Playback:** Play, Pause, Stop, cancellation và queue cơ bản.
- [ ] **Giai đoạn 6 — Voice Cloning:** tạo, lưu, sử dụng và xóa hồ sơ giọng trên engine tương thích.
- [ ] **Giai đoạn 7 — Hardware và Model Manager:** phát hiện phần cứng, khuyến nghị, tải, kiểm tra và xóa model.
- [ ] **Giai đoạn 8 — Kiểm thử và phát hành:** kiểm thử tích hợp, đóng gói Windows, kiểm tra offline và tạo bộ cài.

## Giới hạn đã biết

- Chưa tích hợp hoặc xác nhận ba engine TTS thật; `FakeTTSEngine` chỉ phục vụ development/testing.
- VieNeu-TTS v3-Turbo trên CPU và Voice Cloning của các backend VieNeu chưa được xác nhận; chỉ bật theo capability runtime sau khi adapter được tích hợp.
- Kokoro-Vietnamese không hỗ trợ zero-shot Voice Cloning.
- Chỉ hỗ trợ PDF có lớp văn bản; chưa có OCR cho PDF scan.
- Kích thước chunk mặc định được cấu hình theo engine và cần hiệu chỉnh qua kiểm thử tích hợp.
- Đầu ra MVP chỉ phát trực tiếp; không xuất WAV/MP3.
- Streaming nâng cao không phải điều kiện hoàn thành MVP đầu tiên.
- PyInstaller và Nuitka mới là hai lựa chọn cần đánh giá, chưa chốt công nghệ đóng gói.

## License

TBD — chưa quyết định. License của từng dependency và model phải được kiểm tra trước khi phân phối.

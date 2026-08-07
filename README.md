# Ứng dụng TTS Desktop Offline Tiếng Việt

Ứng dụng desktop chuyển văn bản tiếng Việt thành giọng nói và phát âm thanh trực tiếp trên máy người dùng. Sau khi model cần thiết đã được tải về, quá trình tổng hợp hằng ngày được thiết kế để hoạt động offline, không gửi văn bản, mẫu giọng hoặc âm thanh lên máy chủ.

## Trạng thái dự án

> **Giai đoạn 2 — Engine Adapter Layer đã hoàn thành ở mức mã nguồn và unit test.** Ứng dụng có adapter local-only cho VieNeu v3, VieNeu v2 và Kokoro, registry/factory/capability/lifecycle; chưa bundle trọng số model, chưa chạy integration test với model thật và chưa có playback.

Ứng dụng được phát triển và kiểm thử trước hết trên một máy Windows x64 có Intel Core 5 210H, RAM 16 GB và NVIDIA GeForce RTX 4050 Laptop GPU 6 GB. Đây là cấu hình mục tiêu ban đầu, không phải yêu cầu tối thiểu cố định; khả năng của từng engine vẫn phải được kiểm tra trong quá trình tích hợp thực tế.

## Phạm vi chức năng

Đã có đến Giai đoạn 2:

- Package Python theo bốn nhóm Presentation, Application, Domain và Infrastructure.
- Cửa sổ PySide6 nhập văn bản, chọn engine/giọng và thu thập speed, pitch, volume.
- `BaseTTSEngine`, `EngineRegistry`, `EngineFactory`, `EngineLifecycleManager` và fake engine.
- Adapter VieNeu v3/v2 dùng `Vieneu(mode="standard")` với backbone/codec local; adapter Kokoro truyền đủ model/config/voicepack local.
- Chỉ giữ một model active; chuyển engine sẽ unload model trước để kiểm soát RAM/VRAM.
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
- `VieNeu-TTS v3-Turbo` được đóng cùng bản production để chạy offline ngay lần mở đầu; v2/Kokoro chỉ tải khi người dùng xác nhận.

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
| Máy có GPU tương thích hoặc CPU khá | `VieNeu-TTS v3-Turbo` | Adapter hỗ trợ CPU/CUDA, preset voice, reference audio local, 48 kHz | Có ở adapter; UI/profile hoàn thiện tại Giai đoạn 6 |
| Máy tầm trung | `VieNeu-TTS v2-Turbo` | Adapter GGUF/CPU, preset voice, local-only, 24 kHz | Không mở trong adapter hiện tại |
| Máy yếu, chỉ CPU | `Kokoro-Vietnamese` | Dùng voicepack dựng sẵn | Không hỗ trợ zero-shot Voice Cloning |

Trên máy mục tiêu, thứ tự thử mặc định là v3-Turbo trên RTX 4050 → v2-Turbo/GGUF → Kokoro-Vietnamese. Mỗi bước phải kiểm tra model, backend, bộ nhớ khả dụng và kết quả load; lỗi load sẽ kích hoạt gợi ý fallback thay vì làm ứng dụng dừng. Ứng dụng chỉ khuyến nghị, không tự ép đổi engine; người dùng luôn có thể chọn thủ công.

## Hoạt động offline

- Bản production phải chứa sẵn `VieNeu-TTS v3-Turbo`; người dùng không cần Internet để chạy engine mặc định ngay lần mở đầu.
- Khi startup, v3 được chọn mặc định và load từ local path trong worker nền; không được fallback sang repo ID hoặc tự tải từ Hugging Face.
- Internet chỉ cần khi người dùng chủ động tải/cập nhật `VieNeu-TTS v2-Turbo` hoặc `Kokoro-Vietnamese`.
- `Model Manager` là thành phần duy nhất được phép truy cập mạng và phải xin xác nhận trước khi tải model tùy chọn.
- Nhập văn bản, tổng hợp bằng v3, DSP, phát âm thanh và quản lý hồ sơ giọng phải hoạt động khi ngắt Internet.
- Unit test xác nhận adapter chỉ truyền local path; integration test chặn mạng với SDK/model thật vẫn là release gate.

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

   Khi cần chạy adapter thật, chỉ cài nhóm tương ứng (không cài chung vào runtime nền tảng):

   ```powershell
   python -m pip install -r requirements/vieneu.txt
   # hoặc
   python -m pip install -r requirements/kokoro.txt
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

Model Manager chưa được triển khai nên chưa có lệnh tải tự động. Developer đặt asset đã tải hợp lệ theo layout trong `docs/MODEL_DISTRIBUTION.md`; adapter không tự fallback sang Internet.

## Tài liệu triển khai

- [Development](docs/DEVELOPMENT.md): thiết lập Python 3.11, chạy ứng dụng/test, cấu hình đường dẫn, logging và xử lý sự cố cho developer.
- [Production](docs/PRODUCTION.md): release gate, cấu hình production, dependency/model, đóng gói, kiểm thử, bảo mật và rollback. Repository hiện chưa đủ điều kiện phát hành production.
- [Phân phối model](docs/MODEL_DISTRIBUTION.md): bundle v3 cho first-run offline và chỉ tải v2/Kokoro theo yêu cầu.

## Cấu trúc dự án

Các thư mục chính đã triển khai đến Giai đoạn 2:

```text
vietnamese-tts-desktop/
├── requirements/          # dependency nền tảng, kiểm thử và SDK engine tùy chọn
├── src/vntts/             # mã nguồn package ứng dụng
│   ├── ui/                # cửa sổ, ViewModel và widget PySide6
│   ├── services/          # workflow tổng hợp và dịch vụ phần cứng
│   ├── engines/           # contract, registry/factory/lifecycle và adapter TTS
│   ├── db/                # model dữ liệu thuần Python
│   ├── config/            # settings và default.yaml
│   └── utils/             # logging, exception và Qt worker dùng chung
├── tests/                 # unit test và UI test
└── docs/                  # tài liệu kiến trúc
```

Giải thích đầy đủ cho **từng thư mục** và cây đích chi tiết nằm trong [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#8-cấu-trúc-thư-mục).

## Roadmap

- [x] **Giai đoạn 1 — Khung ứng dụng MVP:** PySide6, cấu hình, logging, exception, worker nền, fake engine và giao diện cơ sở.
- [x] **Giai đoạn 2 — Engine Adapter Layer:** ba adapter local-only, capability, registry, factory và lifecycle engine; integration model thật còn là release gate.
- [ ] **Giai đoạn 3 — Nhập liệu đa nguồn:** TXT, DOCX, PDF có text, normalization và chunking.
- [ ] **Giai đoạn 4 — Audio và điều khiển giọng:** speed, pitch, volume, sample rate và ghép audio.
- [ ] **Giai đoạn 5 — Playback:** Play, Pause, Stop, cancellation và queue cơ bản.
- [ ] **Giai đoạn 6 — Voice Cloning:** tạo, lưu, sử dụng và xóa hồ sơ giọng trên engine tương thích.
- [ ] **Giai đoạn 7 — Hardware và Model Manager:** phát hiện phần cứng; tải, kiểm tra và xóa model tùy chọn v2/Kokoro.
- [ ] **Giai đoạn 8 — Kiểm thử và phát hành:** bundle v3, kiểm thử first-run offline, đóng gói Windows và tạo bộ cài.

## Giới hạn đã biết

- Chưa có trọng số model trong repository và chưa integration-test ba adapter với SDK/model thật; `FakeTTSEngine` vẫn là mặc định development.
- Capability hiện phản ánh đúng API mà adapter Giai đoạn 2 cung cấp: v3 nhận reference audio local; v2/Kokoro không cloning; cả ba chưa bật native speed/pitch hoặc streaming. SDK có tính năng ngoài contract không đồng nghĩa UI được phép bật.
- Kokoro-Vietnamese không hỗ trợ zero-shot Voice Cloning.
- Chỉ hỗ trợ PDF có lớp văn bản; chưa có OCR cho PDF scan.
- Kích thước chunk mặc định được cấu hình theo engine và cần hiệu chỉnh qua kiểm thử tích hợp.
- Đầu ra MVP chỉ phát trực tiếp; không xuất WAV/MP3.
- Streaming nâng cao không phải điều kiện hoàn thành MVP đầu tiên.
- PyInstaller và Nuitka mới là hai lựa chọn cần đánh giá, chưa chốt công nghệ đóng gói.

## License

TBD — chưa quyết định. License của từng dependency và model phải được kiểm tra trước khi phân phối.

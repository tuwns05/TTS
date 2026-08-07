# Ứng dụng TTS Desktop Offline Tiếng Việt

Ứng dụng desktop chuyển văn bản tiếng Việt thành giọng nói trên máy người dùng. Văn bản, waveform và mẫu giọng được xử lý cục bộ; ứng dụng không gửi nội dung người dùng lên máy chủ trong quá trình tổng hợp offline.

## Chức năng chính

- Nhập văn bản tiếng Việt và chọn engine/giọng đọc.
- Chạy tác vụ tổng hợp trong worker nền để không khóa giao diện Qt.
- Giữ waveform vừa tổng hợp và hỗ trợ Play/Pause/Stop bằng Qt Multimedia.
- Giao diện tự chuyển giữa bố cục rộng, compact và dọc; có thanh cuộn khi cửa sổ nhỏ.
- Hỗ trợ adapter local cho VieNeu-TTS v3-Turbo, VieNeu-TTS v2-Turbo và Kokoro-Vietnamese.
- Chỉ giữ một model active; khi chuyển engine, model trước được unload để kiểm soát RAM/VRAM.
- Phát hiện CPU, RAM và CUDA GPU để đưa ra khuyến nghị engine có giải thích.
- Cấu hình đường dẫn model, dữ liệu, cache, log và engine mặc định bằng YAML hoặc biến môi trường.
- Giữ model, log và dữ liệu ứng dụng trong vùng lưu trữ cục bộ.

## Engine

| Engine | Phân phối | Thiết bị | Ghi chú |
|---|---|---|---|
| `VieNeu-TTS v3-Turbo` | Đóng cùng bản production | CPU hoặc CUDA GPU | Engine mặc định production, model local, 48 kHz. |
| `VieNeu-TTS v2-Turbo` | Model tùy chọn | CPU | Dùng backbone/codec local, 24 kHz. |
| `Kokoro-Vietnamese` | Model tùy chọn | CPU | Dùng model, config và voicepack local. |

Khuyến nghị phần cứng không tự động ép đổi engine. Người dùng vẫn có thể chọn một engine khác trong số các engine đã được cài đặt và đăng ký thành công.

## Hoạt động offline

- Development luôn dùng VieNeu-TTS v3-Turbo. Nếu chưa có model tại `resources/models/vieneu-v3`, SDK dùng Hugging Face cache và tải model chính thức ở lần chạy đầu.
- Bản production phải chứa sẵn VieNeu-TTS v3-Turbo để sử dụng ngay lần mở đầu mà không cần Internet.
- Ở production, v3 chỉ được đọc từ local path; adapter không fallback sang repository ID hoặc tự tải model khi startup.
- V2 và Kokoro là model tùy chọn, được lưu trong app-data sau khi người dùng chủ động cài đặt.
- Ứng dụng không tự tải model khi khởi động hoặc khi khuyến nghị phần cứng thay đổi.
- Mẫu giọng, văn bản và audio không được ghi đầy đủ vào log.

Layout bản production:

```text
VietnameseTTSDesktop/
├── vntts.exe
├── resources/
│   └── models/
│       └── vieneu-v3/
│           ├── manifest.json
│           ├── backbone/
│           ├── codec/
│           ├── voices/
│           └── runtime-assets/
└── licenses/
```

Chi tiết về model, manifest, checksum và license nằm trong [MODEL_DISTRIBUTION.md](docs/MODEL_DISTRIBUTION.md).

## Yêu cầu phát triển

- Windows 10/11 x64.
- Python `3.11.x`.
- PowerShell và Git.
- PyTorch/runtime CPU hoặc CUDA tương thích khi chạy engine thật.

## Thiết lập môi trường

Từ thư mục gốc của repository:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
python -m pip install -r requirements/dev.txt
```

Cài SDK cho engine cần sử dụng:

```powershell
# VieNeu v3/v2
python -m pip install -r requirements/vieneu.txt

# Hoặc Kokoro-Vietnamese
python -m pip install -r requirements/kokoro.txt
```

## Chuẩn bị model local

VieNeu v3 dùng trong source/internal build:

```text
resources/
└── models/
    └── vieneu-v3/
        ├── update/
        ├── onnx_int8/
        └── moss-tokenizer/
```

Model tùy chọn trên Windows:

```text
%LOCALAPPDATA%\VietnameseTTSDesktop\models\
├── vieneu-v2\
│   ├── backbone\
│   └── codec\
└── kokoro-vi\
    ├── kokoro_vi.pth
    ├── config.json
    └── voicepacks\*.pt
```

## Chạy ứng dụng

Chạy ở chế độ development:

```powershell
python -m vntts
```

Kiểm tra v3 với cấu hình production và model local:

```powershell
$env:VNTTS_ENVIRONMENT = "production"
$env:VNTTS_BUNDLED_MODELS_DIR = (Resolve-Path ".\resources\models").Path
python -m vntts
```

Chạy kiểm thử:

```powershell
python -m pytest
```

## Cấu trúc dự án

```text
TTS/
├── docs/                 # kiến trúc, development, production và phân phối model
├── requirements/         # dependency nền tảng, test và SDK engine tùy chọn
├── src/vntts/
│   ├── config/           # YAML settings và chuẩn hóa đường dẫn
│   ├── db/               # model dữ liệu thuần Python
│   ├── engines/          # contract, registry/factory/lifecycle và adapter TTS
│   ├── services/         # workflow tổng hợp và dịch vụ phần cứng
│   ├── ui/               # cửa sổ, ViewModel, widget và tài nguyên Qt
│   ├── utils/            # exception, logging và worker dùng chung
│   ├── __main__.py       # hỗ trợ python -m vntts
│   └── main.py           # composition root của ứng dụng
├── tests/                # unit test và UI test
├── pyproject.toml
└── README.md
```

Giải thích đầy đủ từng thư mục và file nằm trong [ARCHITECTURE.md](docs/ARCHITECTURE.md#8-cấu-trúc-thư-mục).

## Tài liệu

- [Development](docs/DEVELOPMENT.md): cài dependency, chạy ứng dụng/test, cấu hình và xử lý lỗi.
- [Production](docs/PRODUCTION.md): đóng gói, release gate, kiểm thử offline và vận hành.
- [Model Distribution](docs/MODEL_DISTRIBUTION.md): layout v3 bundled và model tùy chọn.
- [Architecture](docs/ARCHITECTURE.md): trách nhiệm từng package/file và quy tắc dependency.

## License

License của mã ứng dụng chưa được công bố. Bản phân phối phải kèm license và attribution của từng SDK, model, codec, voicepack và dependency liên quan.

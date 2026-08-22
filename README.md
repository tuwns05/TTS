# GPHI-TTS

GPHI-TTS là ứng dụng desktop chuyển văn bản tiếng Việt thành giọng nói, ưu tiên xử lý cục bộ và hoạt động offline trên Windows. Bản production hiện tại sử dụng **VieNeu-TTS v3-Turbo**, chạy bằng **PyTorch/CUDA trên GPU NVIDIA** hoặc **ONNX trên CPU**.

> Trạng thái dự án: ứng dụng đã hoàn thiện luồng chính gồm kích hoạt bản quyền, tổng hợp giọng, nhập tài liệu, điều chỉnh âm thanh, phát/xuất audio, nhân bản giọng và đóng gói Windows. Trước khi phát hành công khai vẫn cần hoàn tất các mục trong [checklist release](docs/PRODUCTION.md#8-checklist-trước-khi-phát-hành).

## Tính năng

- Tổng hợp văn bản tiếng Việt với giọng dựng sẵn của VieNeu v3.
- Ba phong cách đọc: **Tự nhiên**, **Tin tức** và **Kể chuyện**.
- Điều chỉnh tốc độ `0.5x–2.0x`, cao độ `-12–+12` semitone và âm lượng.
- Nhập nội dung từ `TXT`, `SRT`, `DOCX` và PDF có lớp văn bản.
- Phát, tạm dừng, dừng, tua trên waveform và xuất `WAV`/`MP3`.
- Tạo hồ sơ giọng clone từ mẫu `WAV`, `MP3`, `FLAC`, `M4A` hoặc `OGG` (khả năng giải mã phụ thuộc libsndfile); lưu đặc trưng giọng cục bộ, không giữ bản audio tạm đã xử lý.
- Đổi tên, xóa và nghe thử hồ sơ giọng đã tạo.
- Tự phát hiện CPU, RAM và CUDA GPU; tự fallback từ GPU sang CPU khi chế độ tự động không khởi tạo được GPU.
- Chọn thủ công `Tự động`, `GPU` hoặc `CPU` trong trang **Cài đặt**.
- Xác minh license Ed25519 offline, gắn với MAC thiết bị và kiểm tra hết hạn/đảo ngược đồng hồ.
- Giao diện responsive, tác vụ nặng chạy bằng worker nền và có thể hủy.

## Phạm vi runtime

| Thành phần | Trạng thái | Thiết bị/backend | Ghi chú |
|---|---|---|---|
| VieNeu-TTS v3-Turbo | Được đăng ký trong app | CUDA/PyTorch hoặc CPU/ONNX | Engine duy nhất của bản production, audio 48 kHz. |
| VieNeu-TTS v2-Turbo | Có adapter và unit test | CPU | Chưa đăng ký trong composition root, không xuất hiện trên UI. |
| Kokoro-Vietnamese | Có adapter và unit test | CPU | Chưa đăng ký trong composition root, không xuất hiện trên UI. |

Ứng dụng chỉ giữ một engine được load tại một thời điểm để kiểm soát RAM/VRAM. Ở chế độ `Tự động`, GPU chỉ được ưu tiên khi CUDA khả dụng và đạt ngưỡng VRAM cấu hình; nếu load GPU thất bại, VieNeu v3 tự chuyển sang ONNX/CPU.

## Quyền riêng tư và kết nối mạng

- Tổng hợp, xử lý waveform, phát/xuất audio, tạo hồ sơ giọng và xác minh license diễn ra trên máy người dùng.
- Production ép Hugging Face chạy offline và chỉ đọc model đã bundle; không tự tải model khi khởi động.
- Log không ghi toàn bộ văn bản hoặc mẫu giọng của người dùng.
- Trang **Thanh toán** có thể gửi tên, email, gói, giá và MAC đến endpoint được cấu hình. Đây là luồng mạng tách biệt với TTS. `PaymentService` dùng mock không mạng khi endpoint trong YAML là chuỗi rỗng.

## Yêu cầu

### Người dùng bản đóng gói

- Windows 10/11 x64.
- CPU x64; khuyến nghị tối thiểu 8 GB RAM.
- GPU NVIDIA/CUDA là tùy chọn; chế độ CPU/ONNX luôn là đường fallback.
- Mã kích hoạt hợp lệ để dùng trang **Tạo giọng nói** và **Nhân bản giọng**.

### Môi trường phát triển

- Windows 10/11 x64.
- Python `3.11.x`, PowerShell và Git.
- Internet ở lần đầu nếu chưa có model trong `resources/models/vieneu-v3` hoặc Hugging Face cache.

## Cài đặt môi trường phát triển

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/dev.txt
python -m pip install -r requirements/vieneu.txt
```

Nếu dùng CUDA, cài bản PyTorch phù hợp với driver/runtime mục tiêu trước khi cài VieNeu. Quy trình build production hiện khóa PyTorch CUDA 12.8 trong `requirements/production.lock`.

## Chạy ứng dụng

```powershell
python -m vntts
```

Hoặc sau khi package đã được cài editable:

```powershell
vntts
```

Trong development, nếu không có model local, SDK dùng repository chính thức và Hugging Face cache. Muốn chạy bằng model local:

```text
resources/models/vieneu-v3/
├── update/
├── onnx_int8/
└── moss-tokenizer/
```

Hoặc trỏ thư mục cha bằng biến môi trường:

```powershell
$env:VNTTS_BUNDLED_MODELS_DIR = "D:\models"
python -m vntts
```

Khi đó model phải nằm tại `D:\models\vieneu-v3`.

## Kiểm thử

```powershell
python -m pytest
python -m ruff check src tests scripts
```

Chạy Qt test trong môi trường headless:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest
```

Unit/UI test sử dụng stub và mock, không tải model thật. Build production có thêm smoke test tổng hợp thật bằng executable đã đóng gói.

## Cấu hình

Cấu hình mặc định nằm tại `src/vntts/config/default.yaml`. Các biến môi trường được hỗ trợ:

| Biến | Ý nghĩa |
|---|---|
| `VNTTS_APP_DATA_DIR` | Ghi đè thư mục gốc dữ liệu người dùng; chủ yếu dùng cho test/dev. |
| `VNTTS_BUNDLED_MODELS_DIR` | Thư mục cha chứa `vieneu-v3`. |
| `VNTTS_MODELS_DIR` | Thư mục model tùy chọn. |
| `VNTTS_DATA_DIR` | Hồ sơ giọng và trạng thái license. |
| `VNTTS_CACHE_DIR` | Cache runtime và cache xác minh model. |
| `VNTTS_LOGS_DIR` | Thư mục log. |
| `VNTTS_ENVIRONMENT` | `development` hoặc `production`. |
| `VNTTS_DEFAULT_ENGINE` | Engine mặc định; app hiện đăng ký `vieneu-v3`. |
| `VNTTS_PAYMENT_API_ENDPOINT` | Ghi đè endpoint nhận yêu cầu thanh toán bằng một URL không rỗng. |
| `VNTTS_LOG_LEVEL` | Mức log, ví dụ `INFO` hoặc `DEBUG`. |

Mặc định dữ liệu ghi được nằm tại:

```text
%LOCALAPPDATA%\VietnameseTTSDesktop\
├── data\
│   ├── license.json
│   └── voice_profiles\
├── cache\
├── logs\
└── models\
```

## Cấu trúc repository

```text
TTS/
├── docs/                  # hướng dẫn người dùng, kiến trúc, dev và release
├── packaging/             # PyInstaller, Inno Setup và thông báo license
├── requirements/          # dependency dev, engine và production lock
├── resources/             # tài nguyên đóng gói; model binary bị git-ignore
├── scripts/               # chuẩn bị model, license và build production
├── src/vntts/
│   ├── config/            # cấu hình và theme
│   ├── db/                # dataclass dùng chung
│   ├── engines/           # contract, registry, lifecycle và adapter TTS
│   ├── services/          # synthesis, audio, tài liệu, license, thanh toán
│   ├── ui/                # cửa sổ và các trang PySide6
│   └── utils/             # worker, logging, machine info và exception
└── tests/                 # unit test và UI test
```

## Tài liệu

- [Hướng dẫn sử dụng](docs/USER_GUIDE.md)
- [Hướng dẫn phát triển](docs/DEVELOPMENT.md)
- [Kiến trúc hệ thống](docs/ARCHITECTURE.md)
- [Đóng gói và phát hành](docs/PRODUCTION.md)
- [Phân phối model VieNeu v3](docs/MODEL_DISTRIBUTION.md)

## License

License của mã ứng dụng chưa được công bố trong repository. Bản phân phối phải kèm EULA/license của ứng dụng, `THIRD_PARTY_NOTICES.txt`, license của các dependency/model và nghĩa vụ LGPL tương ứng. Xem checklist chi tiết trong [tài liệu production](docs/PRODUCTION.md).

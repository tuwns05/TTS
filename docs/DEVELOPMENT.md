# Hướng dẫn Development

Giai đoạn 2 vẫn dùng `FakeTTSEngine` mặc định trong development, đồng thời có adapter thật được đăng ký khi SDK và asset local đầy đủ. Chạy fake không cần model, CUDA, audio device hoặc Internet; cài dependency/chuẩn bị model thật cần Internet ở bước riêng.

## 1. Yêu cầu và cài đặt

- Windows 10/11 x64.
- Python `3.11.x` (`pyproject.toml` khóa `>=3.11,<3.12`).
- PowerShell và Git.

Từ thư mục gốc:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
python -m pip install -r requirements/dev.txt
```

Nếu không kích hoạt được virtualenv, dùng trực tiếp `.\.venv\Scripts\python.exe` thay cho `python`.

## 2. Chạy ứng dụng và test

```powershell
python -m vntts
# hoặc
python -m vntts.main
```

Kết quả hiện tại:

- Cửa sổ mở với `Fake TTS Engine` và ba giọng giả.
- Tổng hợp tạo audio NumPy trong worker, không khóa UI.
- Speed/pitch/volume chỉ được thu thập; DSP chưa chạy.
- Play/Pause/Stop bị khóa vì chưa có playback.
- Nếu asset và SDK tương ứng đã có, engine thật xuất hiện trong selector và được load trong worker.
- Chuyển engine sẽ unload model trước đó; ứng dụng chỉ giữ một model active.

Chạy test:

```powershell
python -m pytest
python -m pytest tests/unit
python -m pytest tests/ui
```

Trong CI/headless:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest
```

## 3. Cấu hình và dữ liệu

Cấu hình mặc định: `src/vntts/config/default.yaml`.

App-data mặc định trên Windows:

```text
%LOCALAPPDATA%\VietnameseTTSDesktop\
├── models\
└── data\
    ├── cache\
    └── logs\
```

Biến môi trường:

| Biến | Tác dụng |
|---|---|
| `VNTTS_APP_DATA_DIR` | Đổi app-data root. |
| `VNTTS_BUNDLED_MODELS_DIR` | Đổi vùng read-only chứa v3 bundled. |
| `VNTTS_MODELS_DIR` | Đổi nơi lưu model tùy chọn. |
| `VNTTS_DATA_DIR` | Đổi data directory. |
| `VNTTS_CACHE_DIR` | Đổi cache directory. |
| `VNTTS_LOGS_DIR` | Đổi logs directory. |
| `VNTTS_ENVIRONMENT` | `development` hoặc `production`. |
| `VNTTS_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`... |
| `VNTTS_DEFAULT_ENGINE` | Ghi đè engine mặc định để integration test. |

Không commit `.venv`, model, cache, log hoặc dữ liệu người dùng.

## 4. Quy tắc phát triển

```text
UI → Services → Engines/DB
Engines → DB
```

- `ui/` chứa PySide6 và chỉ điều phối tương tác giao diện.
- `services/` chứa workflow nghiệp vụ, không import widget Qt.
- Adapter mới nằm trong `engines/` và triển khai `BaseTTSEngine` từ `engines/base.py`.
- Registry, factory và lifecycle nằm chung trong `engines/factory.py`.
- Model dữ liệu thuần Python nằm trong `db/models.py`.
- Qt worker dùng chung nằm trong `utils/worker.py`; worker không chứa nghiệp vụ.
- Registry giữ provider; không load model ở lúc liệt kê engine.
- Không đưa nghiệp vụ vào `MainWindow`/`MainViewModel`.
- Không log toàn bộ text, audio, waveform hoặc mẫu giọng.
- Thay đổi contract/cấu trúc phải cập nhật Architecture và test.

## 5. Kiểm tra trước commit

1. `python -m pytest` pass.
2. `python -m vntts` mở được cửa sổ.
3. Không có model/log/cache/dữ liệu cá nhân trong Git.
4. Không có SDK hoặc dependency ngoài phạm vi.
5. UI không hiển thị traceback.

## 6. Lỗi thường gặp

### Sai Python

```powershell
python --version
python -c "import sys; print(sys.executable)"
```

Phải trỏ tới Python 3.11 trong `.venv`.

### Không import được `vntts`

```powershell
python -m pip install -r requirements/base.txt
```

### UI test lỗi trong headless

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/ui
```

### Chạy adapter thật

VieNeu và Kokoro là dependency tùy chọn, không nằm trong `base.txt`:

```powershell
python -m pip install -r requirements/vieneu.txt
# hoặc
python -m pip install -r requirements/kokoro.txt
```

Đặt model theo layout:

```text
resources/models/vieneu-v3/{backbone,codec}/
%LOCALAPPDATA%/VietnameseTTSDesktop/models/vieneu-v2/{backbone,codec}/
%LOCALAPPDATA%/VietnameseTTSDesktop/models/kokoro-vi/
├── kokoro_vi.pth
├── config.json
└── voicepacks/*.pt
```

Adapter không tải model. Nếu thiếu SDK/file, engine tùy chọn không được đăng ký; riêng production vẫn đăng ký v3 để hiển thị lỗi bundle/Repair rõ ràng.

### Không phát hiện CUDA

PyTorch vẫn là dependency tùy chọn theo engine. Khi thiếu PyTorch/CUDA, detector trả `cuda_available=False` và development bằng fake engine vẫn chạy. Không thêm một bản Torch CUDA cố định vào requirements nền tảng; developer cài bản phù hợp với runtime/máy đích.

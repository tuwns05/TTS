# Hướng dẫn triển khai môi trường Development

Tài liệu này hướng dẫn lập trình viên thiết lập, chạy và kiểm thử khung ứng dụng TTS trên máy phát triển. Trạng thái hiện tại là Giai đoạn 1: chỉ có `FakeTTSEngine`; chưa cần model TTS, CUDA, kết nối mạng khi chạy ứng dụng hoặc thiết bị âm thanh.

## 1. Yêu cầu

- Windows 10/11 x64 là môi trường phát triển ưu tiên.
- Python `3.11.x`. `pyproject.toml` hiện khóa `>=3.11,<3.12`.
- Git và PowerShell.
- Kết nối Internet chỉ cần khi cài package từ Python Package Index.

Kiểm tra Python 3.11:

```powershell
py -3.11 --version
```

Nếu lệnh không tồn tại, cài Python 3.11 x64 trước khi tiếp tục. Không dùng Python 3.12 trở lên cho môi trường hiện tại.

## 2. Tạo môi trường phát triển

Chạy từ thư mục gốc repository:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
python -m pip install -r requirements/dev.txt
```

`requirements/base.txt` cài package ở chế độ editable và các dependency Giai đoạn 1. `requirements/dev.txt` bổ sung pytest và pytest-qt; không cài VieNeu, Kokoro hoặc PyTorch CUDA.

Nếu PowerShell chặn script kích hoạt, có thể chạy Python trong môi trường ảo trực tiếp:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m vntts
```

Không thay đổi execution policy toàn máy nếu không thật sự cần.

## 3. Chạy ứng dụng

Với môi trường ảo đã kích hoạt:

```powershell
python -m vntts
```

Entry point tương đương:

```powershell
python -m vntts.main
```

Kết quả mong đợi:

- Cửa sổ `Vietnamese TTS Desktop` mở bình thường.
- Combo engine chỉ hiển thị `Fake TTS Engine` ở Giai đoạn 1.
- Sau khi fake engine load trong worker, combo giọng có ba giọng giả.
- Tổng hợp trả audio NumPy giả mà không khóa UI.
- Play/Pause/Stop bị khóa vì playback chưa triển khai.

## 4. Chạy kiểm thử

Chạy toàn bộ test:

```powershell
python -m pytest
```

Chạy theo nhóm:

```powershell
python -m pytest tests/unit
python -m pytest tests/ui
```

Chạy một file hoặc một test:

```powershell
python -m pytest tests/unit/test_fake_engine.py
python -m pytest tests/ui/test_main_window.py::test_ui_stays_responsive_during_fake_synthesis
```

Trong môi trường CI/headless, đặt Qt platform thành `offscreen`:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest
```

Test UI phải dùng `pytest-qt`; không dùng `sleep` dài để chờ signal hoặc worker.

## 5. Cấu hình và dữ liệu cục bộ

Cấu hình mặc định nằm tại `src/vntts/config/default_config.yaml`. `settings.py` đọc YAML, validate và chuẩn hóa đường dẫn.

Mặc định trên Windows, dữ liệu được tạo dưới:

```text
%LOCALAPPDATA%\VietnameseTTSDesktop\
├── models\
└── data\
    ├── cache\
    └── logs\
```

Có thể override cho development hoặc test:

| Biến môi trường | Tác dụng |
|---|---|
| `VNTTS_APP_DATA_DIR` | Đổi thư mục gốc của toàn bộ dữ liệu ứng dụng. |
| `VNTTS_MODELS_DIR` | Đổi riêng nơi lưu model. |
| `VNTTS_DATA_DIR` | Đổi riêng thư mục dữ liệu. |
| `VNTTS_CACHE_DIR` | Đổi riêng cache. |
| `VNTTS_LOGS_DIR` | Đổi riêng thư mục log. |
| `VNTTS_ENVIRONMENT` | Đặt môi trường, ví dụ `development` hoặc `production`. |
| `VNTTS_LOG_LEVEL` | Override mức log, ví dụ `DEBUG`, `INFO`, `WARNING`. |

Ví dụ tạo dữ liệu tạm ngay trong workspace:

```powershell
$env:VNTTS_APP_DATA_DIR = (Join-Path (Get-Location) ".local-data")
$env:VNTTS_LOG_LEVEL = "DEBUG"
python -m vntts
```

Không commit `.local-data`, model, log, cache hoặc mẫu giọng.

## 6. Logging và quyền riêng tư

- Development ghi log ra console và file `data/logs/vntts.log` trong app-data root.
- Không log toàn bộ văn bản người dùng, audio, waveform, mẫu giọng hoặc dữ liệu nhị phân.
- Khi cần chẩn đoán, chỉ log metadata như engine ID, số ký tự, thời gian xử lý và loại lỗi.
- UI chỉ hiển thị thông báo thân thiện; traceback kỹ thuật chỉ nằm trong log.

## 7. Quy tắc khi phát triển

Giữ đúng hướng dependency:

```text
Presentation → Application → Domain
Infrastructure → Domain
```

- Domain không import PySide6 hoặc SDK engine.
- Application không import widget, Presentation, Infrastructure hoặc Config.
- Worker dùng Qt chỉ nằm trong `presentation/workers/`.
- Adapter SDK mới nằm trong `infrastructure/engines/` và triển khai `BaseTTSEngine`.
- Đăng ký adapter bằng provider trong `EngineRegistry`; không load model lúc startup.
- Không đưa xử lý audio, phần cứng hoặc SDK vào `MainWindow`/`MainViewModel`.
- Mọi thay đổi phải có test phù hợp và không thêm dependency ngoài phạm vi.

## 8. Quy trình kiểm tra trước khi commit

1. Chạy toàn bộ test bằng Python 3.11.
2. Xác nhận `python -m vntts` mở cửa sổ.
3. Kiểm tra không có model, log, cache, `.venv` hoặc dữ liệu cá nhân trong thay đổi Git.
4. Kiểm tra không import SDK/model thật ngoài adapter tương ứng.
5. Kiểm tra text/audio/mẫu giọng không xuất hiện trong log.
6. Cập nhật README/Architecture nếu contract, cấu trúc hoặc quy trình thay đổi.

## 9. Xử lý sự cố

### Python báo không tương thích

Xác nhận interpreter đang dùng:

```powershell
python --version
python -c "import sys; print(sys.executable)"
```

Nếu không phải Python 3.11 trong `.venv`, xóa môi trường ảo cũ theo cách an toàn rồi tạo lại bằng `py -3.11 -m venv .venv`.

### Không import được `vntts`

Chạy lại từ thư mục gốc:

```powershell
python -m pip install -r requirements/base.txt
```

Không thêm thủ công đường dẫn tuyệt đối của máy vào `PYTHONPATH` hoặc source code.

### Test Qt không chạy trong headless/CI

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/ui
```

### Không phát hiện CUDA/GPU

Trong Giai đoạn 1, PyTorch không phải dependency bắt buộc. Khi PyTorch không có hoặc CUDA không khả dụng, detector phải trả `cuda_available=False` và ứng dụng vẫn chạy. Việc cài backend CUDA thuộc Giai đoạn 2, không tự thêm Torch CUDA vào requirements nền tảng.


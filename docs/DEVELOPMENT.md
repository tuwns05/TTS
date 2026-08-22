# Hướng dẫn phát triển GPHI-TTS

## 1. Môi trường hỗ trợ

- Windows 10/11 x64.
- Python `>=3.11,<3.12`.
- PowerShell và Git.
- Driver NVIDIA/CUDA tương thích nếu phát triển đường chạy GPU.

Ứng dụng thực tế chỉ đăng ký `vieneu-v3`. VieNeu v2 và Kokoro có adapter/test để mở rộng sau, nhưng không được composition root khởi tạo.

## 2. Cài đặt

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/dev.txt
python -m pip install -r requirements/vieneu.txt
```

`requirements/dev.txt` kéo `requirements/base.txt`, còn `base.txt` cài project editable và dependency trung lập với engine. `requirements/vieneu.txt` thêm VieNeu cùng dependency runtime.

Nếu dùng NVIDIA, cài PyTorch phù hợp trước VieNeu. Ví dụ môi trường cùng dòng CUDA 12.8 với production lock:

```powershell
python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements/vieneu.txt
```

Không cài `hf-gradio`. Nếu môi trường cũ đã có gói này:

```powershell
python -m pip uninstall -y hf-gradio
python -m pip check
```

## 3. Model development

Khi `resources/models/vieneu-v3` là thư mục model development, app truyền đường dẫn local cho VieNeu. Layout:

```text
resources/models/vieneu-v3/
├── update/
├── onnx_int8/
└── moss-tokenizer/
```

Nếu thư mục local không tồn tại, development cho phép SDK dùng:

- `pnnbao-ump/VieNeu-TTS-v3-Turbo`;
- `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`;
- Hugging Face cache hiện có hoặc tải phần còn thiếu.

Có thể đổi thư mục cha:

```powershell
$env:VNTTS_BUNDLED_MODELS_DIR = "D:\models"
python -m vntts
```

Nếu `vieneu-v3` chứa `manifest.json`, app coi đây là production-style bundle, xác minh checksum và ép Hugging Face offline.

## 4. Chạy và debug

```powershell
python -m vntts
```

Composition root thực hiện:

1. đọc và chuẩn hóa cấu hình;
2. cấu hình log;
3. đăng ký lazy provider cho VieNeu v3;
4. tạo lifecycle, use case, store và các trang UI;
5. hiển thị cửa sổ;
6. nhận diện phần cứng và load model qua worker sau khi event loop bắt đầu.

Các tác vụ load model, tổng hợp, nhập tài liệu, enrollment và thanh toán đều chạy ngoài UI thread. Khi đóng cửa sổ, app hủy worker, dừng playback và unload engine.

### Chạy như production từ source

```powershell
$env:VNTTS_ENVIRONMENT = "production"
$env:VNTTS_BUNDLED_MODELS_DIR = (Resolve-Path ".\resources\models").Path
python -m vntts
```

Chế độ này yêu cầu bundle có `manifest.json`; không fallback ra Internet.

## 5. Cấu hình

File mặc định: `src/vntts/config/default.yaml`.

| Biến môi trường | Áp dụng cho |
|---|---|
| `VNTTS_APP_DATA_DIR` | Root của mọi đường dẫn ghi được tương đối. |
| `VNTTS_BUNDLED_MODELS_DIR` | Model read-only đi cùng app. |
| `VNTTS_MODELS_DIR` | Model tùy chọn. |
| `VNTTS_DATA_DIR` | License và voice profile. |
| `VNTTS_CACHE_DIR` | Cache runtime/model validation. |
| `VNTTS_LOGS_DIR` | Log. |
| `VNTTS_ENVIRONMENT` | `development`/`production`. |
| `VNTTS_DEFAULT_ENGINE` | Engine mặc định. |
| `VNTTS_PAYMENT_API_ENDPOINT` | Ghi đè URL POST bằng giá trị không rỗng. |
| `VNTTS_LOG_LEVEL` | Mức Loguru. |

Đường dẫn tương đối cho `data`, `cache`, `logs`, `models` được resolve dưới app-data. `bundled_models_dir` được resolve dưới repository ở source hoặc `_MEIPASS` trong frozen build.

Không commit model, cache, log, dữ liệu người dùng, `.venv`, `.venv-build`, `build`, `dist` hoặc `release`.

## 6. Kiểm thử và lint

```powershell
python -m pytest
python -m ruff check src tests scripts
```

Headless Qt:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest
```

Các nhóm test chính:

- engine registry/factory/lifecycle và adapter VieNeu/Kokoro;
- CPU/GPU selection, fallback, bundle checksum và cancellation;
- DSP tốc độ/cao độ/volume;
- nhập TXT/SRT/DOCX/PDF;
- playback, seek, WAV/MP3 và thay đổi thiết bị audio;
- voice enrollment/profile;
- license, payment, settings và logging;
- UI responsive, license gate và các workflow chính.

Test dùng stub/mock và thư mục tạm, không cần model thật. Smoke test model thật thuộc quy trình production.

## 7. Quy ước khi thay đổi

- UI không import trực tiếp SDK TTS.
- SDK object không đi qua biên adapter.
- Nghiệp vụ mới đặt trong service/use case và inject vào UI.
- Tác vụ có I/O hoặc tính toán đáng kể phải chạy qua `TaskWorker`.
- Exception kỹ thuật được chuyển thành `AppError`/thông báo thân thiện trước UI.
- Không log toàn văn, waveform, license payload đã giải mã hoặc mẫu giọng.
- Engine mới phải khai báo metadata/capability mà không cần load model.
- Chỉ một engine được active; mọi đường thoát phải giải phóng runtime.
- Thêm dependency production phải cập nhật lock hash và inventory license.

## 8. Thanh toán và license trong development

Endpoint mặc định hiện là local test server:

```text
http://127.0.0.1:8000/payment/request
```

Muốn test UI không gọi mạng, đặt `payment.api_endpoint: ""` trong YAML được load. Do environment override hiện dùng phép `or`, biến môi trường rỗng không thể bật mock:

```yaml
payment:
  api_endpoint: ""
```

UI đang hiển thị năm gói nhưng `_validated_payment_request()` chỉ chấp nhận `monthly` và `yearly`; `PaymentRequest` còn gửi `LOCAL_TEST_PRICE_VND = 1_990_000` thay vì giá được chọn. Phải đồng bộ UI/validation/payload và chuyển quyền quyết định giá sang server trước release.

`LicenseService` hiện dùng public key có tên `TEST_LICENSE_PUBLIC_KEY`. Đây là release blocker: trước production thật phải thay bằng public key phát hành, giữ private key hoàn toàn ngoài repository/app và cập nhật test fixture tương ứng.

## 9. Xử lý lỗi thường gặp

| Lỗi | Kiểm tra |
|---|---|
| `No module named vntts` | Kích hoạt `.venv`, chạy lại `pip install -r requirements/dev.txt`. |
| `No module named vieneu` | Chạy `pip install -r requirements/vieneu.txt`. |
| Không thấy CUDA | `python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"`. |
| Load lần đầu rất lâu | Kiểm tra mạng, dung lượng đĩa và Hugging Face cache. |
| Production cố tải mạng | Bundle/path sai; kiểm tra `manifest.json` và biến môi trường. |
| Qt test lỗi display | Đặt `QT_QPA_PLATFORM=offscreen`. |
| Không đọc DOCX/PDF | Chạy `python -m pip check`, xác nhận `python-docx` và `pypdf`. |
| MP3 export lỗi | Xác nhận `lameenc` đã được cài/đóng gói. |

Xem thêm [kiến trúc](ARCHITECTURE.md), [model bundle](MODEL_DISTRIBUTION.md) và [quy trình release](PRODUCTION.md).

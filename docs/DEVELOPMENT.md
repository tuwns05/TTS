# Hướng dẫn Development

Ứng dụng development chỉ đăng ký VieNeu-TTS v3-Turbo làm engine bắt buộc. Không có engine mô phỏng trong mã nguồn. Khi chưa có model local, VieNeu SDK sử dụng Hugging Face cache và tải model chính thức ở lần chạy đầu; các lần sau có thể dùng cache hiện có.

## 1. Cài đặt

Yêu cầu Windows 10/11 x64, Python `3.11.x`, PowerShell và Git.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/dev.txt
python -m pip install -r requirements/vieneu.txt
```

Nếu dùng NVIDIA CUDA, cài bản PyTorch phù hợp trước khi cài VieNeu, ví dụ cho CUDA 12.8:

```powershell
python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
```

Không cài `hf-gradio`; nếu môi trường cũ có gói này thì gỡ bằng `python -m pip uninstall -y hf-gradio`.

## 2. Chạy ứng dụng

```powershell
python -m vntts
```

Luồng development:

1. Registry đăng ký `vieneu-v3` và chọn nó làm mặc định.
2. Nếu `resources/models/vieneu-v3` tồn tại, SDK nạp model từ thư mục đó.
3. Nếu không có model local, SDK dùng repository `pnnbao-ump/VieNeu-TTS-v3-Turbo`; model đã tải được lấy từ Hugging Face cache, model thiếu sẽ được tải qua Internet.
4. Thiết bị `auto` chọn CUDA khi PyTorch nhận GPU, nếu không sẽ dùng CPU backend của VieNeu.
5. Model được load và tổng hợp trong worker để không khóa giao diện.
6. Waveform mới nhất được chuyển thành WAV PCM trong bộ nhớ để Play/Pause/Stop; buffer cũ được giải phóng khi tổng hợp lại hoặc đóng ứng dụng.

Cache mặc định nằm tại `%USERPROFILE%\.cache\huggingface\hub`. Có thể chạy hoàn toàn local trong development bằng cách đặt model vào:

```text
resources/models/vieneu-v3/
```

hoặc trỏ tới thư mục model bằng:

```powershell
$env:VNTTS_BUNDLED_MODELS_DIR = "D:\models"
python -m vntts
```

Trong đó model phải nằm tại `D:\models\vieneu-v3`.

## 3. Chạy test

```powershell
python -m pytest
```

Test dùng `StubTTSEngine` nằm riêng trong `tests/stubs.py`, do đó unit/UI test không tải model thật. Trong CI/headless:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest
```

## 4. Cấu hình và dữ liệu

Cấu hình mặc định: `src/vntts/config/default.yaml`.

| Biến | Tác dụng |
|---|---|
| `VNTTS_BUNDLED_MODELS_DIR` | Thư mục cha chứa `vieneu-v3`. |
| `VNTTS_MODELS_DIR` | Nơi lưu model tùy chọn. |
| `VNTTS_ENVIRONMENT` | `development` hoặc `production`. |
| `VNTTS_DEFAULT_ENGINE` | Engine mặc định; cấu hình chuẩn là `vieneu-v3`. |
| `VNTTS_LOG_LEVEL` | Mức log. |

Không commit `.venv`, model, cache, log hoặc dữ liệu người dùng.

## 5. Xử lý lỗi nhanh

- Không import được `vntts`: chạy `python -m pip install -r requirements/base.txt`.
- Không import được `vieneu`: chạy `python -m pip install -r requirements/vieneu.txt`.
- Không thấy CUDA: kiểm tra `python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"`.
- Lỗi dependency: chạy `python -m pip check`, gỡ `hf-gradio` nếu còn trong môi trường cũ.
- Lần đầu đứng lâu ở bước load: kiểm tra Internet và dung lượng đĩa vì SDK đang tải model/tokenizer.

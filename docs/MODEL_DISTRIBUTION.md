# Bundle model VieNeu v3 Turbo

Bản production hiện tại chỉ dùng VieNeu-TTS v3 Turbo. Không bundle hoặc tải
VieNeu v2/Kokoro.

## Snapshot đã pin

| Repository | Revision | Mục đích |
|---|---|---|
| `pnnbao-ump/VieNeu-TTS-v3-Turbo` | `75ff82a72f54d55ed389e1eeb12041d3c4bac7d4` | Backbone PyTorch, ONNX int8, speaker encoder, denoiser |
| `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` | `6aa02b01e445cc585582cf0ba480bc3ea6c8dd68` | Tokenizer/codec PyTorch |
| `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae` | Codec ONNX CPU |

SDK được pin ở `vieneu==3.2.4`. Production ép backend `onnx`/CPU.

## Layout

```text
resources/models/vieneu-v3/
├── manifest.json
└── hub/
    ├── models--pnnbao-ump--VieNeu-TTS-v3-Turbo/
    ├── models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano/
    └── models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX/
```

Đây là Hugging Face cache tối giản, chỉ chứa các tệp cần cho runtime. Runtime
đặt `HF_HUB_CACHE` vào thư mục này và bật `HF_HUB_OFFLINE=1`, do đó SDK vẫn dùng
API chính thức nhưng không thể tải hoặc fallback ra mạng.

`manifest.json` ghi revision, kích thước và SHA-256 từng tệp. Checksum được kiểm
tra trên worker trước khi model load. Bundle sai hoặc thiếu tệp sẽ báo lỗi thay
vì tự tải lại.

## Tạo và xác minh

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --validate-only
```

Model binary bị ignore khỏi Git. Pipeline build phải tái tạo từ revision đã pin
hoặc nhận bundle đã được xác minh qua kênh artifact nội bộ.

# Phân phối model VieNeu-TTS v3-Turbo

## 1. Phạm vi

Production chỉ bundle `vieneu-v3`. Cùng một bundle phục vụ:

- PyTorch/CUDA trên GPU NVIDIA;
- ONNX int8 trên CPU;
- preset voices;
- speaker encoder/denoiser cho voice cloning.

VieNeu v2 và Kokoro không nằm trong artifact production hiện tại.

## 2. Snapshot và SDK đã pin

| Repository | Revision | Mục đích |
|---|---|---|
| `pnnbao-ump/VieNeu-TTS-v3-Turbo` | `75ff82a72f54d55ed389e1eeb12041d3c4bac7d4` | Backbone PyTorch, ONNX int8, speaker encoder, denoiser và voice assets. |
| `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` | `6aa02b01e445cc585582cf0ba480bc3ea6c8dd68` | Tokenizer/codec PyTorch. |
| `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae` | Codec ONNX cho CPU. |

SDK được pin tại `vieneu==3.2.4`. Runtime từ bundle từ chối load nếu version SDK không khớp `manifest.json`.

## 3. Layout bundle

```text
resources/models/vieneu-v3/
├── manifest.json
└── hub/
    ├── models--pnnbao-ump--VieNeu-TTS-v3-Turbo/
    ├── models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano/
    └── models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX/
```

`hub/` là Hugging Face cache tối giản do script tạo từ đúng revision. Không đổi tên thư mục hoặc chỉnh symlink/snapshot thủ công.

`manifest.json` có:

- schema và engine ID;
- version VieNeu SDK;
- repo ID và revision;
- danh sách file tương đối;
- kích thước và SHA-256 từng file.

## 4. Tạo bundle

Từ môi trường đã cài `requirements/vieneu.txt`:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py
```

Chỉ dùng cache local, không tải:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --local-files-only
```

Chọn destination khác:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py `
  --destination D:\bundles\vieneu-v3
```

Model binary bị `.gitignore`; truyền bundle qua artifact store nội bộ có checksum/quyền truy cập phù hợp, không commit vào Git.

## 5. Xác minh

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_vieneu_v3.py --validate-only
```

Runtime gọi cùng validator trước khi load. Validator kiểm tra schema, engine, SDK, path an toàn, size và hash. Metadata file hợp lệ được cache trong thư mục cache app để lần sau không băm lại file lớn; cache bị vô hiệu khi manifest, size hoặc mtime thay đổi.

Thiếu file, sai hash, path vượt bundle hoặc SDK lệch version đều phải fail closed. Production không tự sửa hoặc tải lại model.

## 6. Chế độ offline

Sau khi xác minh, runtime trỏ `HF_HUB_CACHE` vào `hub/` và thiết lập chế độ Hugging Face/Transformers offline, tắt telemetry. SDK tiếp tục dùng repo ID chính thức nhưng chỉ resolve snapshot local.

Phân biệt hai layout:

| Layout | Dấu hiệu | Hành vi |
|---|---|---|
| Development local | Không có `manifest.json`; có model folders trực tiếp | Truyền local path; development vẫn có thể fallback repo/cache nếu thiếu. |
| Production bundle | Có `manifest.json` và `hub/` | Xác minh checksum, khóa version, ép offline, không fallback mạng. |

## 7. Đưa vào artifact

`packaging/vntts.spec` copy toàn bộ `resources/models/vieneu-v3` vào:

```text
dist/GPHI-TTS/_internal/resources/models/vieneu-v3/
```

Build script kiểm tra manifest trong output rồi chạy synthesis thật CPU/ONNX; nếu máy build có CUDA thì chạy thêm GPU/PyTorch. Chỉ phát hành cả thư mục onedir/ZIP hoặc installer.

## 8. Cập nhật model

Khi nâng revision hoặc VieNeu SDK:

1. duyệt model card/license và thay đổi upstream;
2. cập nhật revision/SDK trong `prepare_vieneu_v3.py` và production lock;
3. tạo mới bundle, không chỉnh manifest cũ;
4. chạy unit test bundle/adapter;
5. chạy smoke CPU và GPU nếu có;
6. đo dung lượng, thời gian load, chất lượng preset/clone và regression;
7. cập nhật notices, docs, version và release notes;
8. lưu manifest/checksum cùng artifact release.

Không trộn file từ nhiều revision trong cùng bundle.

## 9. License và provenance

Manifest kỹ thuật không thay thế nghĩa vụ license. Release owner phải lưu và phân phối attribution/license phù hợp cho:

- VieNeu model và SDK;
- MOSS Audio Tokenizer PyTorch/ONNX;
- voice assets;
- PyTorch, ONNX Runtime, Hugging Face và dependency đi kèm.

Xem [checklist production](PRODUCTION.md#8-checklist-trước-khi-phát-hành).

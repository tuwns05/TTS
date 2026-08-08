# Phân phối model

## 1. Chính sách

| Engine | Phân phối | Startup production |
|---|---|---|
| `vieneu-v3` | Bundled bắt buộc | Chọn mặc định, load local trong worker, không Internet. |
| `vieneu-v2` | Tải tùy chọn | Chỉ tải qua Model Manager sau consent. |
| `kokoro-vi` | Tải tùy chọn | Chỉ tải qua Model Manager sau consent. |

SDK VieNeu mặc định có thể tải model từ Hugging Face, nhưng hỗ trợ local path. Adapter production phải truyền local path và không fallback sang repo ID.

Nguồn chính thức:

- [VieNeu SDK](https://docs.vieneu.io/docs/sdk/overview/)
- [Local/custom models](https://docs.vieneu.io/docs/advanced/custom-models/)
- [VieNeu-TTS v3-Turbo](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo)

## 2. Layout và manifest

```text
installer/
├── vntts.exe
├── resources/models/vieneu-v3/
│   ├── manifest.json
│   ├── update/
│   ├── onnx_int8/
│   ├── moss-tokenizer/
│   ├── voices/
│   └── runtime-assets/
└── licenses/
    ├── VieNeu-TTS-v3-Turbo-LICENSE.txt
    └── THIRD_PARTY_NOTICES.txt

%LOCALAPPDATA%\VietnameseTTSDesktop\models\
├── vieneu-v2\
│   ├── backbone\
│   └── codec\
└── kokoro-vi\
    ├── kokoro_vi.pth
    ├── config.json
    └── voicepacks\*.pt
```

Bundled v3 là read-only và không được Model Manager xóa. Model tùy chọn nằm trong app-data dưới cùng một model root, mỗi engine có thư mục con riêng (`vieneu-v2/`, `kokoro-vi/`). Khi tải model mới, Model Manager phải tạo/cập nhật thư mục con đó trong root hiện có, không tạo thư mục lẻ ở ngoài root.

Manifest v3 tối thiểu:

```json
{
  "schema_version": 1,
  "engine_id": "vieneu-v3",
  "model_version": "<pinned-version>",
  "source_revision": "<commit-sha>",
  "license": "Apache-2.0",
  "components": ["update", "onnx_int8", "moss-tokenizer", "voices", "runtime-assets"],
  "files": [{"path": "<relative>", "size": 0, "sha256": "<sha256>"}]
}
```

- Pin commit SHA, không build từ `main`.
- Path phải relative và nằm trong model root.
- Startup kiểm tra manifest/file bắt buộc; build/Repair kiểm tra checksum đầy đủ.
- Thiếu/hỏng v3 → báo Repair, không tự tải.
- Adapter hiện kiểm tra SDK/path bắt buộc; kiểm tra manifest/checksum đầy đủ thuộc Model Manager và release pipeline.

## 3. Startup offline

```text
Resolve bundled v3
→ Validate manifest
→ Đăng ký VieNeuV3Engine(local_path)
→ Chọn v3 mặc định
→ Load GPU hoặc CPU backend trong worker
→ Sẵn sàng tổng hợp offline
```

Yêu cầu:

- Không gọi Hugging Face/API/remote mode khi startup, load hoặc synthesize v3.
- Không block UI thread.
- GPU lỗi → thử v3 CPU nếu backend CPU được bundle.
- V3 lỗi hoàn toàn → chỉ dùng v2/Kokoro nếu đã cài; nếu chưa, hỏi người dùng trước khi tải.
- First-run test phải chạy trên Windows sạch, chặn network và không có Hugging Face cache.

Để hỗ trợ cả GPU và CPU, installer phải chứa đủ asset/runtime cho hai backend đã công bố. Repository v3 hiện khoảng 1,68 GB; artifact cuối còn có codec, PyTorch/CUDA hoặc ONNX, Qt và ứng dụng nên phải đo từ build thật.

## 4. Tải model tùy chọn

```text
Người dùng chọn v2/Kokoro
→ Hiển thị version/nguồn/license/kích thước
→ Người dùng xác nhận
→ Tải vào staging
→ Hỗ trợ hủy
→ Kiểm tra SHA-256
→ Atomic move vào model root
→ Đánh dấu installed
```

Không được tự tải ở startup, khi recommendation thay đổi hoặc khi fallback. Không coi tải dở là model hợp lệ. Request tải model không chứa text/audio/mẫu giọng.

## 5. Build và license

Máy build cần Internet; máy người dùng không cần Internet cho v3.

1. Tải đúng snapshot v3 vào staging sạch.
2. Chuẩn bị backbone, codec, voices và runtime theo backend hỗ trợ.
3. Tạo manifest/checksum và bundle license/notices.
4. Smoke test local path với network bị chặn.
5. Đóng gói và cài thử trên Windows sạch.

Không lấy model từ cache developer. Model v3 công bố Apache-2.0 nhưng release phải giữ attribution cho project/model package và kiểm tra riêng license của codec, tokenizer/phonemizer, runtime và dependency.

## 6. Điều kiện hoàn thành

- [ ] Installer chứa đầy đủ v3, manifest và license.
- [ ] V3 load local và được chọn mặc định.
- [ ] First-run offline pass; không có network request.
- [ ] UI không treo khi load.
- [ ] GPU/CPU fallback đúng phạm vi build.
- [ ] V2/Kokoro chỉ tải sau consent, có checksum và atomic install.

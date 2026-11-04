# Kiểm kê giấy phép mã nguồn mở của SI-TTS

Ngày kiểm tra: 30/10/2026. Phạm vi: `requirements/production.lock`, `.venv` khớp đủ 105/105 phiên bản, ba repository model được pin trong `scripts/prepare_vieneu_v3.py`, và cấu hình đóng gói. Đây là kiểm kê từ metadata và tệp của wheel đã cài, chưa phải chứng nhận tuân thủ của file cài đặt cuối cùng.

## Kết quả chính

- 105/105 gói trong lock có đúng phiên bản trong `.venv`.
- 100/105 wheel có ít nhất một tệp tên LICENSE, LICENCE, COPYING, COPYRIGHT hoặc NOTICE; 5 wheel không có tệp như vậy: `flatbuffers`, `gradio-client`, `loguru`, `perth`, `tokenizers`.
- Công cụ `scripts/export_production_licenses.py` chỉ liệt kê 24 gói, bỏ qua 81 gói trong lock. Chưa có `packaging/licenses/components/` hay `PYTHON_PACKAGES.csv` trong repository.
- `scripts/build_production.ps1` không gọi công cụ xuất license. `packaging/vntts.spec` chỉ đóng gói thư mục license đang có.
- `groovy` và `safehttpx` khai báo MIT trong classifier, nhưng tệp LICENSE trong wheel là Apache-2.0. Cần xác minh từ đúng nguồn và phiên bản trước khi công bố nhãn.
- `llvmlite` không khai báo license trong metadata; wheel có LICENSE kiểu BSD và LICENSE.thirdparty cho LLVM Apache-2.0 với LLVM Exceptions.
- Mã ứng dụng chưa có giấy phép hoặc EULA riêng trong repository. Bộ model production chưa hiện diện cục bộ để đối chiếu tệp theo revision và nội dung artifact cuối cùng.

## Các nhóm giấy phép đã thấy

- Nhóm cho phép tái phân phối theo điều kiện thông báo: MIT và biến thể, BSD-2-Clause/3-Clause, Apache-2.0, ISC, PSF, Zlib, 0BSD, CC0. Một số wheel chứa nhiều license cho mã bên thứ ba.
- Nhóm copyleft hoặc đa giấy phép: Qt/PySide6 dùng lựa chọn LGPL-3.0/GPL/commercial; `lameenc` LGPL-3.0-or-later; `soxr` LGPL-2.1-or-later; `libsndfile` đi kèm `soundfile` LGPL-2.1; `certifi`, `orjson`, `tqdm` có MPL-2.0 trong metadata; PyInstaller có GPL với bootloader exception.
- Ba repository model được pin (VieNeu v3 Turbo, MOSS Nano, MOSS Nano ONNX) được ghi Apache-2.0 trong `THIRD_PARTY_NOTICES.txt`. Model card công khai hiện cũng ghi Apache-2.0; chưa xác thực lại trực tiếp tệp ở ba commit đã pin vì bundle chưa có trong workspace.
- `Kokoro-Vietnamese` nằm trong `requirements/kokoro.txt` ở nhánh Git `main`, nhưng không được đăng ký hoặc đóng gói trong production hiện tại. Nếu mở tính năng này, phải pin commit và kiểm kê riêng model và dependency.

## Thành phần ngoài bộ production đã khóa

- Công cụ kiểm thử cài trong `.venv`: `pytest==9.2.0` và `pytest-qt==4.5.0`, đều ghi MIT trong metadata. Chúng không nằm trong `production.lock` và không phải thành phần runtime dự kiến.
- Tích hợp tùy chọn `Kokoro-Vietnamese` dùng Git `main` chưa pin. Repository mã và model card hiện ghi Apache-2.0, nhưng không thể xác nhận phiên bản cụ thể hoặc các phụ thuộc phát sinh từ một nhánh luôn thay đổi. [Mã nguồn](https://github.com/iamdinhthuan/Kokoro-Vietnamese/blob/main/LICENSE) · [Model card](https://huggingface.co/contextboxai/Kokoro-Vietnamese).
- `packaging/windows/installer.iss` dùng Inno Setup làm công cụ tạo installer. Phiên bản đang dùng chưa được khóa trong repo. [Trang chính thức](https://jrsoftware.org/isinfo.php) nêu điều khoản phân phối riêng và đề nghị người dùng thương mại mua license; cần đối chiếu bản cài Inno Setup thực tế trước khi phát hành.
- Python 3.11 được dùng để build và sẽ có runtime trong bản PyInstaller; cần kiểm tra thông báo PSF và các thư viện bên thứ ba theo artifact thực tế. `tmp/vc_redist.x64.exe` không phải mã nguồn mở và không được `packaging/vntts.spec` đưa trực tiếp vào bản phân phối.

## Việc cần hoàn tất trước khi phát hành

1. Xuất license của **toàn bộ 105 gói** từ môi trường production đúng lock, lưu bản kê và tệp gốc của wheel; xử lý năm wheel thiếu tệp bằng license upstream đúng phiên bản.
2. Đối chiếu kết quả với `dist/SI-TTS/_internal` sau PyInstaller, gồm thư viện DLL/PYD, tài nguyên Qt, runtime CUDA, model và thông báo đi kèm. Danh sách lock không chứng minh chính xác nội dung artifact.
3. Xác minh license theo ba revision model đã pin, gồm voice assets; lưu attribution và license theo yêu cầu của từng nguồn.
4. Hoàn tất nghĩa vụ LGPL cho Qt/PySide6, LAME, libsoxr, libsndfile: thông báo, tệp license, nguồn tương ứng hoặc phương án hợp lệ và khả năng thay thế thư viện theo cách đóng gói thực tế.
5. Giải quyết xung đột metadata và tệp của `groovy` và `safehttpx`; kiểm tra các license hỗn hợp như `numpy`, `scipy`, `orjson`, `regex`, `pyinstaller-hooks-contrib` và các binary runtime.
6. Bổ sung license hoặc EULA cho mã ứng dụng và kiểm tra thông báo của bên thứ ba trong installer phát hành. Ghi nhận phiên bản cùng điều khoản Inno Setup đã dùng.

## Danh mục 105 gói

Cột “Giấy phép” lấy từ `License-Expression`, sau đó `License`, sau đó classifier của wheel. Các giá trị mơ hồ hoặc nhiều license giữ nguyên để xem xét; đây không phải xác nhận pháp lý. Cột cuối đếm tệp liên quan đến giấy phép trong wheel đã cài.

| Gói | Phiên bản khóa | Giấy phép theo metadata hoặc tệp | Tệp liên quan |
|---|---:|---|---:|
| altgraph | 0.17.5 | MIT | 1 |
| annotated-doc | 0.0.5 | MIT | 1 |
| annotated-types | 0.8.0 | MIT | 1 |
| anyio | 4.14.2 | MIT | 1 |
| audioread | 3.1.0 | MIT | 1 |
| brotli | 1.2.0 | MIT | 1 |
| certifi | 2026.7.22 | MPL-2.0 | 1 |
| cffi | 2.1.1 | MIT-0 | 1 |
| charset-normalizer | 3.4.9 | MIT | 1 |
| click | 8.4.2 | BSD-3-Clause | 1 |
| colorama | 0.4.6 | OSI Approved :: BSD License | 1 |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause | 3 |
| decorator | 5.3.1 | BSD-2-Clause | 1 |
| fastapi | 0.141.1 | MIT | 1 |
| filelock | 3.32.2 | MIT | 1 |
| flatbuffers | 25.12.19 | Apache 2.0 | 0 |
| fsspec | 2026.7.0 | BSD-3-Clause | 1 |
| gradio | 6.17.3 | Apache-2.0 | 8 |
| gradio-client | 2.5.0 | Apache-2.0 | 0 |
| groovy | 0.1.2 | MIT (metadata) / Apache-2.0 (tệp LICENSE) — xung đột | 1 |
| h11 | 0.16.0 | MIT | 1 |
| hf-gradio | 0.4.1 | MIT | 1 |
| httpcore | 1.0.9 | BSD-3-Clause | 1 |
| httpx | 0.28.1 | BSD-3-Clause | 1 |
| huggingface-hub | 0.36.2 | Apache | 1 |
| idna | 3.18 | BSD-3-Clause | 1 |
| jinja2 | 3.1.6 | OSI Approved :: BSD License | 1 |
| joblib | 1.5.3 | BSD-3-Clause | 1 |
| lameenc | 1.8.4 | LGPL-3.0-or-later | 1 |
| lazy-loader | 0.5 | BSD-3-Clause | 1 |
| librosa | 0.11.0 | ISC | 1 |
| llvmlite | 0.48.0 | BSD-style; LLVM: Apache-2.0 WITH LLVM-exception | 2 |
| loguru | 0.7.3 | OSI Approved :: MIT License | 0 |
| lxml | 6.1.1 | BSD-3-Clause | 2 |
| markdown-it-py | 4.2.0 | OSI Approved :: MIT License | 2 |
| markupsafe | 3.0.3 | BSD-3-Clause | 1 |
| mdurl | 0.1.2 | OSI Approved :: MIT License | 1 |
| mpmath | 1.3.0 | BSD | 1 |
| msgpack | 1.2.1 | Apache-2.0 | 1 |
| narwhals | 2.24.0 | MIT | 1 |
| networkx | 3.6.1 | BSD-3-Clause | 1 |
| numba | 0.66.0 | BSD | 2 |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 20 |
| onnxruntime | 1.28.0 | MIT License | 2 |
| orjson | 3.11.9 | MPL-2.0 AND (Apache-2.0 OR MIT) | 3 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | 7 |
| pandas | 3.0.5 | OSI Approved :: BSD License | 1 |
| pefile | 2024.8.26 | MIT | 1 |
| perth | 1.0.0 | MIT | 0 |
| pillow | 12.3.0 | MIT-CMU | 1 |
| platformdirs | 4.11.2 | MIT | 1 |
| pooch | 1.9.0 | BSD-3-Clause | 2 |
| protobuf | 7.35.1 | 3-Clause BSD License | 1 |
| psutil | 7.2.2 | BSD-3-Clause | 1 |
| py-cpuinfo | 9.0.0 | MIT | 1 |
| pycparser | 3.0 | BSD-3-Clause | 1 |
| pydantic | 2.13.4 | MIT | 1 |
| pydantic-core | 2.46.4 | MIT | 1 |
| pydub | 0.25.1 | MIT | 1 |
| pygments | 2.20.0 | BSD-2-Clause | 2 |
| pyinstaller | 6.21.0 | OSI Approved :: GNU General Public License v2 (GPLv2) | 1 |
| pyinstaller-hooks-contrib | 2026.6 | OSI Approved :: Apache Software License; OSI Approved :: GNU General Public License v2 (GPLv2) | 1 |
| pypdf | 6.15.0 | BSD-3-Clause | 1 |
| pyside6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | 1 |
| pyside6-addons | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | 1 |
| pyside6-essentials | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | 1 |
| python-dateutil | 2.9.0.post0 | Apache-2.0 OR BSD-3-Clause (dual license) | 1 |
| python-docx | 1.2.0 | MIT | 1 |
| python-multipart | 0.0.32 | Apache-2.0 | 1 |
| pytz | 2026.3.post1 | MIT | 1 |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause | 1 |
| pyyaml | 6.0.3 | MIT | 1 |
| regex | 2026.7.19 | Apache-2.0 AND CNRI-Python | 1 |
| requests | 2.34.2 | Apache-2.0 | 2 |
| rich | 15.0.0 | MIT | 1 |
| safehttpx | 0.1.7 | MIT (metadata) / Apache-2.0 (tệp LICENSE) — xung đột | 1 |
| safetensors | 0.8.0 | OSI Approved :: Apache Software License | 1 |
| scikit-learn | 1.9.0 | BSD-3-Clause | 4 |
| scipy | 1.17.1 | OSI Approved :: BSD License | 5 |
| sea-g2p | 0.8.4 | OSI Approved :: Apache Software License | 1 |
| semantic-version | 2.10.0 | BSD | 1 |
| shellingham | 1.5.4 | ISC License | 1 |
| shiboken6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | 1 |
| six | 1.17.0 | MIT | 1 |
| soundfile | 0.14.0 | BSD 3-Clause License | 3 |
| soxr | 1.1.0 | LGPL-2.1-or-later | 4 |
| starlette | 1.6.0 | BSD-3-Clause | 1 |
| sympy | 1.14.0 | BSD | 3 |
| threadpoolctl | 3.6.0 | BSD-3-Clause | 1 |
| tokenizers | 0.22.2 | OSI Approved :: Apache Software License | 0 |
| tomlkit | 0.14.0 | MIT | 1 |
| torch | 2.8.0+cu128 | BSD-3-Clause | 2 |
| torchaudio | 2.8.0+cu128 | BSD-2-Clause (tệp LICENSE) | 1 |
| tqdm | 4.70.0 | MPL-2.0 AND MIT | 1 |
| transformers | 4.57.6 | Apache 2.0 License | 1 |
| typer | 0.27.1 | MIT | 2 |
| typing-extensions | 4.16.0 | PSF-2.0 | 1 |
| typing-inspection | 0.4.3 | MIT | 1 |
| tzdata | 2026.3 | Apache-2.0 | 2 |
| urllib3 | 2.7.0 | MIT | 1 |
| uvicorn | 0.52.1 | BSD-3-Clause | 1 |
| vieneu | 3.2.4 | OSI Approved :: Apache Software License | 1 |
| wheel | 0.47.0 | MIT | 1 |
| win32-setctime | 1.2.0 | MIT license | 1 |
| setuptools | 80.9.0 | MIT | 28 |

## Nguồn kiểm tra

- `requirements/production.lock`, metadata và tệp trong `.venv/Lib/site-packages`.
- `packaging/licenses/THIRD_PARTY_NOTICES.txt`, `packaging/licenses/README_PRODUCTION.txt`, `packaging/vntts.spec`, `scripts/build_production.ps1`, `scripts/export_production_licenses.py`.
- [Model card VieNeu v3 Turbo](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo), [MOSS Nano](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano), [MOSS Nano ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX), [tài liệu Qt](https://doc.qt.io/qt-6/licensing.html), [tài liệu PyInstaller](https://pyinstaller.org/en/stable/license.html).

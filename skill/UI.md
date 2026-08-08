---
name: vong-tts-interface-design
description: Thiết kế và dựng mockup giao diện desktop cho ứng dụng đọc văn bản tiếng Việt offline "Vọng / Vietnamese TTS Studio" (màn Soạn văn bản, Thư viện giọng, Nhân bản giọng, Cài đặt, và mọi màn hình khác của app). LUÔN dùng skill này khi người dùng yêu cầu thiết kế, làm lại, chỉnh sửa, hoặc góp ý giao diện/UI/UX cho ứng dụng TTS này — kể cả khi họ chỉ nói "làm lại giao diện", "thiết kế màn hình X", "sửa cái UI này giúp mình", hay gửi ảnh chụp màn hình app thật để xin cải tiến — không chỉ khi họ nói rõ "dùng design system". Cung cấp sẵn bảng màu, font chữ, thư viện thành phần (title bar, card, slider, nút, thanh tiến trình phát âm thanh, trạng thái disable...) và nguyên tắc thiết kế đã chốt, để mọi mockup mới đều nhất quán với các mockup trước đó của dự án thay vì bịa lại từ đầu mỗi lần.
---

# Thiết kế giao diện — Vọng / Vietnamese TTS Studio

## Bối cảnh dự án

Đây là ứng dụng desktop **offline** chuyển văn bản tiếng Việt thành giọng nói (PySide6 + Python), có nhập văn bản đa nguồn (gõ trực tiếp / Word / PDF / txt), tuỳ chỉnh tốc độ - cao độ - âm lượng, phát trực tiếp, và nhân bản giọng nói (Voice Cloning). Ứng dụng chạy trên 3 tầng phần cứng khác nhau (GPU, CPU tầm trung, CPU yếu) với 3 model TTS tương ứng. Tên gọi trong sản phẩm có thể là "Vọng" hoặc "Vietnamese TTS Studio" tuỳ ngữ cảnh người dùng đang dùng — không tự ý đổi tên hiển thị nếu người dùng đã cho biết app thật của họ đang dùng tên nào (ví dụ qua ảnh chụp màn hình), chỉ dùng "Vọng" khi họ chưa có tên cụ thể.

## Khi nào dùng skill này

- Người dùng xin thiết kế/làm mockup một màn hình mới của app này.
- Người dùng gửi ảnh chụp màn hình thật của app và xin cải tiến/làm lại giao diện.
- Người dùng xin góp ý UI/UX cho một phần cụ thể (nút, slider, bảng điều khiển...).
- Bất kỳ yêu cầu nào liên quan đến hình ảnh/bố cục/trải nghiệm của app TTS này, kể cả khi câu chữ không nhắc đến "design system" hay tên skill.

Nếu người dùng gửi ảnh chụp màn hình thật: **giữ đúng nội dung, nhãn, các trường dữ liệu thật đã có** trong ảnh, chỉ thiết kế lại phần trình bày/tương tác — đừng bịa ra tính năng hay nhãn mới không có trong ảnh trừ khi được yêu cầu.

## Quy trình làm việc

1. **Xác định đúng phạm vi.** Đang thiết kế màn hình nào? Có ảnh chụp thật cần bám theo không? Có vấn đề cụ thể nào người dùng đã chỉ ra cần sửa không (đọc kỹ trước khi vẽ lại)?
2. **Áp dụng design token & nguyên tắc** ở mục dưới. Với các thành phần lặp lại (title bar, slider, nút, thanh tiến trình phát...), xem `references/components.md` để lấy đúng cấu trúc HTML/CSS đã chuẩn hoá thay vì tự nghĩ ra biến thể mới — điều này giữ mọi mockup của dự án nhất quán với nhau.
3. **Dựng thành 1 file HTML độc lập** (xem mục "Định dạng bàn giao"). Có thể copy nguyên khối `:root` và các class dùng chung từ `assets/design-tokens.css` làm nền, rồi thêm CSS riêng cho bố cục của màn hình đang thiết kế.
4. **Rà lại theo checklist** ở cuối file trước khi lưu và gửi cho người dùng.

## Nguyên tắc thiết kế cốt lõi

Đây là những quyết định đã được thống nhất qua nhiều vòng thiết kế thật với người dùng — không phải sở thích cá nhân, mà là kết quả của việc sửa lỗi thực tế đã xảy ra. Hiểu **lý do** phía sau mỗi nguyên tắc để áp dụng đúng tinh thần khi gặp tình huống mới, không chỉ máy móc làm theo.

**Tránh 3 khuôn mẫu thiết kế AI mặc định:** kem + cam đất kiểu tạp chí, đen tuyền + một màu neon duy nhất, hoặc dashboard SaaS trắng-viền-mảnh chung chung. Ứng dụng này đọc giọng nói tiếng Việt — bản sắc thị giác nên gợi được điều đó, không phải trông như bất kỳ landing page AI nào khác.

**Bảng màu graphite tối + đúng 2 màu nhấn**, không hơn: hổ phách ấm (`--amber`) cho hành động chính/gắn với "giọng nói", xanh ngọc lạnh (`--teal`) cho dữ liệu/waveform/trạng thái. Thêm màu thứ 3 làm loãng hệ thống, trừ `--danger` dùng riêng cho hành động phá huỷ (xoá, đóng).

**Font đã chọn vì hỗ trợ tiếng Việt tốt và có cá tính:** Fraunces (tiêu đề, ấm áp kiểu editorial) + Inter (giao diện, dễ đọc) + IBM Plex Mono (số liệu, bộ đếm ký tự, nhãn kỹ thuật, timestamp). Giữ nguyên bộ 3 này cho mọi màn hình, không đổi font tuỳ hứng.

**Khung app phải trông như app desktop thật:** title bar phẳng riêng (không để lọt gradient/màu thừa ở mép), có nút thu nhỏ/phóng to/đóng. Đây là app Windows chạy offline, không phải trang web.

**Chỉ 1 cấp phân tách trực quan.** Đừng lồng card trong card (viền chồng viền gây rối mắt) — nếu cần nhóm nhiều mục trong cùng 1 khối, dùng đường kẻ ngang mảnh (divider) để chia section, không dùng thêm viền/bóng cho từng nhóm con.

**Trạng thái "disabled" phải disabled thật.** Từng có lỗi: nút phát/dừng trông như bấm được dù chưa có audio để phát. Luôn gắn thuộc tính `disabled` thật trên phần tử tương tác được, kèm giảm độ mờ và `cursor: not-allowed` — không chỉ giảm màu cho "có vẻ" mờ.

**Phân biệt rõ nút chính và nút phụ**, và tránh nút "Hủy" đứng mồ côi cạnh nút hành động chính khi không có tác vụ nào đang chạy để huỷ. Nếu cần một hành động phụ, đặt tên đúng việc nó làm (VD: "Xóa nội dung" thay vì "Hủy" chung chung).

**Điều khiển phát âm thanh dùng nút tròn icon**, nút Play chính to hơn và tô màu hổ phách nổi bật, Pause/Stop nhỏ hơn màu trung tính. Với tiến trình phát, **ưu tiên 1 thanh tiến trình (scrubber) dạng `input[type=range]`** thay vì hiển thị nhiều thanh waveform — waveform nhiều thanh chỉ dùng khi người dùng yêu cầu rõ ràng muốn xem dạng sóng.

**Giá trị mặc định của slider phải đúng về mặt kỹ thuật.** Từng có lỗi: cao độ (pitch) mặc định lại nằm ở vị trí max thay vì vị trí trung tính (0 semitone). Với mọi tham số có điểm trung tính (pitch, volume tính theo dB đối xứng...), giá trị mặc định và vị trí thumb phải khớp đúng điểm giữa toán học của thang đo, không áng chừng.

**Badge/trạng thái đặt cạnh control mà nó phản ánh.** Đừng để trạng thái "Engine sẵn sàng" trôi nổi ở khu vực không liên quan — đặt ngay cạnh bộ chọn engine.

**Copy tiếng Việt ngắn gọn, hành động rõ ràng, trung thực về giới hạn kỹ thuật thật.** Ví dụ: nếu một model không hỗ trợ Voice Cloning, nói thẳng điều đó ngay trong UI (banner/ghi chú nhỏ) thay vì giấu đi khiến người dùng tự mò ra bằng cách thử và thất bại.

**Tôn trọng khả năng tiếp cận cơ bản:** `:focus-visible` rõ ràng cho điều hướng bàn phím, tôn trọng `prefers-reduced-motion` để tắt animation khi người dùng yêu cầu giảm chuyển động.

## Design token nhanh

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--ink` | `#12151A` | Nền gốc |
| `--ink-soft` | `#171B22` | Title bar, nền input |
| `--panel` | `#1C212B` | Card, panel |
| `--panel-raised` | `#252B36` | Phần tử nổi lên (nút phụ, hover) |
| `--border` / `--border-soft` | `#2C3340` / `#232936` | Viền |
| `--bone` / `--bone-dim` | `#ECE7DC` / `#B9B4A8` | Chữ chính / chữ phụ |
| `--slate` / `--slate-dim` | `#8891A0` / `#5B6270` | Nhãn mờ, placeholder, disabled |
| `--amber` / `--amber-soft` | `#E3A857` / tương ứng 14% alpha | Hành động chính, "giọng nói" |
| `--teal` / `--teal-soft` | `#5FC9C0` / tương ứng 14% alpha | Dữ liệu, waveform, trạng thái sẵn sàng |
| `--danger` | `#E17B6B` | Hành động phá huỷ |
| Font | Fraunces / Inter / IBM Plex Mono | Tiêu đề / giao diện / số liệu |
| Bo góc | `--r-sm 6px` / `--r-md 10px` / `--r-lg 18px` | Nút, ô nhập / card nhỏ / card lớn |

Bộ token đầy đủ kèm class dùng chung (nút, slider, card, dock phát...) nằm sẵn trong `assets/design-tokens.css` — copy khối `<style>` này làm nền rồi thêm CSS riêng cho bố cục màn hình mới, thay vì gõ lại từ đầu.

## Thư viện thành phần

Xem `references/components.md` để lấy cấu trúc HTML/CSS đã chuẩn hoá cho: title bar, sidebar rail (điều hướng nhiều màn hình), card văn bản có toolbar mở file, panel chia section bằng divider, hàng slider, chip chọn giọng, card chọn model, dropzone tải mẫu giọng, pill trạng thái, dock phát với thanh tiến trình, và các biến thể nút (primary/ghost/link/icon).

## Định dạng bàn giao

- Một file `.html` độc lập: CSS trong `<style>`, JS trong `<script>`, đều nằm chung 1 file — không tách file rời.
- Nạp font qua thẻ `<link>` tới Google Fonts (Fraunces, Inter, IBM Plex Mono) — cả 3 đều có hỗ trợ tiếng Việt.
- Icon vẽ bằng SVG inline, không phụ thuộc thư viện icon ngoài.
- Nếu mockup có trạng thái thay đổi được (VD: bấm "Tạo giọng nói" thì thanh tiến trình mở khoá), **làm tương tác thật bằng JS** thay vì chỉ mô tả bằng lời — người xem cảm nhận được hành vi thật, không chỉ ảnh tĩnh.
- Lưu file vào `/mnt/user-data/outputs/` và trình bày bằng công cụ present_files.

## Checklist trước khi giao

- [ ] Đúng 2 màu nhấn (hổ phách + xanh ngọc), không có màu thứ 3 lạc vào ngoài `--danger`
- [ ] Không còn card lồng trong card ở bất kỳ đâu
- [ ] Mọi phần tử "chưa dùng được" đều có thuộc tính `disabled` thật, không chỉ mờ màu
- [ ] Vị trí thumb của mọi slider khớp đúng giá trị mặc định về mặt toán học
- [ ] Nút chính (primary) dễ phân biệt hơn hẳn nút phụ/ghost trong cùng màn hình
- [ ] Không có nút "Hủy"/"Cancel" đứng cạnh nút chính mà không rõ đang huỷ tác vụ nào
- [ ] Nếu bám theo ảnh chụp thật: nội dung/nhãn khớp đúng những gì đã có trong ảnh
- [ ] Copy tiếng Việt tự nhiên, không như dịch máy, phản ánh đúng giới hạn kỹ thuật thật của tính năng
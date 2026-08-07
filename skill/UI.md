# Clean — Design skill

Hệ thống thiết kế tối giản, ưu tiên khoảng trắng, dùng cho giao diện ứng dụng năng suất / công cụ (ví dụ: app desktop). Khi tạo UI, luôn tuân theo các quy tắc dưới đây.

## Nguyên tắc chung
- Ưu tiên sự rõ ràng hơn trang trí. Không thêm màu, viền, hiệu ứng nếu không phục vụ mục đích chức năng.
- Không dùng gradient, đổ bóng nặng, hiệu ứng neon/glow.
- Mỗi khoảng cách, lề, padding phải là bội số của 8px (lưới 8pt).
- Màu sắc dùng để truyền tải thông tin (trạng thái, hành động), không phải để trang trí.

## Bảng màu

| Vai trò | Mã màu | Dùng cho |
|---|---|---|
| Primary | `#3B82F6` | Hành động chính, link, trạng thái active |
| Secondary | `#8B5CF6` | Điểm nhấn phụ, hành động thứ cấp |
| Success | `#16A34A` | Xác nhận, trạng thái hợp lệ |
| Warning | `#D97706` | Cảnh báo, cần chú ý |
| Danger | `#DC2626` | Lỗi, hành động xoá/nguy hiểm |
| Surface | `#FFFFFF` | Nền chính (light mode) |
| Text | `#111827` | Chữ nội dung chính |

Với dark mode: nền tối `#14161B`–`#20242C`, chữ sáng `#F3F4F6`, giữ nguyên hai màu accent primary/secondary nhưng có thể tăng sáng nhẹ (`#60A5FA`, `#A78BFA`) để đủ tương phản.

## Typography
- Font nội dung: Roboto (hoặc font sans-serif tương đương hệ thống)
- Font tiêu đề: Poppins
- Font monospace / số liệu: Inconsolata (hoặc font mono hệ thống)
- Thang cỡ chữ: 12 / 14 / 16 / 20 / 24 / 32px
- Chỉ dùng 2 độ đậm: 400 (regular) và 500 (medium). Tránh 600/700 vì trông quá nặng trên nền trắng tối giản.

## Spacing
- Lưới cơ sở: 8px. Mọi margin/padding/gap là bội số của 8 (8, 16, 24, 32...).
- Dùng khoảng trắng để phân tách các khối nội dung thay vì viền/đường kẻ khi có thể.

## Component
- Bo góc: 8px cho control (nút, input), 12px cho card.
- Viền mảnh 0.5–1px, màu xám nhạt, không dùng đổ bóng trừ focus ring.
- Trạng thái bắt buộc cho mọi control tương tác: default, hover, focus-visible, active, disabled, loading, error.
- Trang/màn hình trống (empty state) phải có tiêu đề rõ ràng + một hành động chính, không dùng minh hoạ trang trí thừa.

## Accessibility
- Đạt chuẩn WCAG 2.2 AA tối thiểu.
- Điều hướng đầy đủ bằng bàn phím, focus state hiển thị rõ trên mọi phần tử tương tác.
- Ưu tiên HTML ngữ nghĩa (semantic) trước khi dùng ARIA.
- Tôn trọng `prefers-reduced-motion` — không có animation chỉ mang tính trang trí.
- Kích thước vùng chạm tối thiểu 44x44px cho thao tác chạm/click.
- Khi có xung đột giữa thẩm mỹ và khả năng tiếp cận, accessibility luôn được ưu tiên.

## Ghi chú riêng cho ứng dụng TTS desktop
- Waveform / thanh trực quan âm thanh: dùng màu Primary (`#3B82F6`) trên nền accent nhạt, không dùng nhiều màu cùng lúc.
- Danh sách giọng đọc (voice library): mỗi mục là một hàng/thẻ nhỏ 8pt-grid, avatar tròn dùng Secondary làm nền.
- Thanh trượt tốc độ / cao độ: luôn hiển thị giá trị số hiện tại cạnh thanh trượt, làm tròn hợp lý (ví dụ 1 chữ số thập phân cho tốc độ).
- Nút "Tạo giọng nói" là hành động chính duy nhất trên mỗi màn hình — dùng màu Primary, các nút còn lại (xuất file, tải mẫu giọng...) dùng kiểu outline/secondary.
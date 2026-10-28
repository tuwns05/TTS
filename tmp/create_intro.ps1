$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$source = 'C:\Users\tuant\AppData\Roaming\WordCraft\Templates\GioiThieuSI_TTS.docx'
$destination = 'C:\work_space\TTS\docs\GioiThieuSI_TTS_A4.docx'
Copy-Item -LiteralPath $source -Destination $destination

function Paragraph([string]$text, [int]$size = 24, [bool]$bold = $false, [string]$align = 'both', [int]$after = 100) {
    $safe = [System.Security.SecurityElement]::Escape($text)
    $weight = if ($bold) { '<w:b/>' } else { '' }
    return "<w:p><w:pPr><w:spacing w:after=`"$after`" w:line=`"300`" w:lineRule=`"auto`"/><w:jc w:val=`"$align`"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii=`"Times New Roman`" w:hAnsi=`"Times New Roman`" w:cs=`"Times New Roman`"/>$weight<w:sz w:val=`"$size`"/><w:szCs w:val=`"$size`"/></w:rPr><w:t xml:space=`"preserve`">$safe</w:t></w:r></w:p>"
}

$body = Paragraph 'PHẦN MỀM CHUYỂN ĐỔI VĂN BẢN THÀNH GIỌNG NÓI' 27 $true 'center' 20
$body += Paragraph 'SI-TTS' 32 $true 'center' 140
$body += Paragraph 'SI-TTS là ứng dụng chuyển văn bản tiếng Việt thành giọng nói trên máy tính Windows, hỗ trợ tạo nội dung âm thanh cho bài giảng, video, bản tin và tài liệu thuyết minh. Người dùng có thể nhập nội dung, chọn giọng đọc, nghe thử và xuất tệp âm thanh trong cùng một giao diện.'
$body += '<w:tbl><w:tblPr><w:tblW w:w="9638" w:type="dxa"/><w:tblBorders><w:top w:val="single" w:sz="6" w:color="A6A6A6"/><w:left w:val="single" w:sz="6" w:color="A6A6A6"/><w:bottom w:val="single" w:sz="6" w:color="A6A6A6"/><w:right w:val="single" w:sz="6" w:color="A6A6A6"/></w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w="9638"/></w:tblGrid><w:tr><w:trPr><w:trHeight w:val="3402" w:hRule="exact"/><w:cantSplit/></w:trPr><w:tc><w:tcPr><w:tcW w:w="9638" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
$body += Paragraph '[CHÈN HÌNH GIAO DIỆN SI-TTS TẠI ĐÂY]' 22 $false 'center' 0
$body += '</w:tc></w:tr></w:tbl>'
$body += Paragraph '' 8 $false 'left' 0
$body += Paragraph 'TÍNH NĂNG NỔI BẬT' 25 $true 'left' 70
$body += Paragraph '• Đọc tiếng Việt với các phong cách Tự nhiên, Tin tức và Kể chuyện; điều chỉnh tốc độ, cao độ và âm lượng theo nhu cầu.'
$body += Paragraph '• Nhập nội dung từ tệp TXT, SRT, Word (DOCX) và PDF có lớp văn bản, giúp giảm thao tác nhập lại tài liệu.'
$body += Paragraph '• Nghe thử, tạm dừng và tua trên dạng sóng; xuất âm thanh định dạng WAV hoặc MP3 để sử dụng trong các sản phẩm nội dung.'
$body += Paragraph '• Tạo và quản lý hồ sơ giọng cá nhân từ mẫu âm thanh, phục vụ nhu cầu nhân bản giọng nói.'
$body += Paragraph '• Xử lý giọng nói ngay trên máy, hoạt động offline sau khi cài đầy đủ mô hình; hỗ trợ CPU và tăng tốc bằng GPU NVIDIA tương thích.'
$body += Paragraph 'ỨNG DỤNG THỰC TẾ' 25 $true 'left' 70
$body += Paragraph 'SI-TTS phù hợp với giáo viên, người sáng tạo nội dung và đơn vị cần chuyển tài liệu thành âm thanh. Phần mềm giúp giảm thời gian thu âm, thuận tiện cập nhật lời đọc khi nội dung thay đổi và chủ động xử lý dữ liệu trên máy tính.'
$body += Paragraph 'SI-TTS – Từ văn bản đến giọng nói, thuận tiện trên máy tính của bạn.' 24 $true 'center' 0
$xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + $body + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1021" w:right="1134" w:bottom="1021" w:left="1134" w:header="480" w:footer="480"/></w:sectPr></w:body></w:document>'
[xml]$validated = $xml
$archive = [System.IO.Compression.ZipFile]::Open($destination, [System.IO.Compression.ZipArchiveMode]::Update)
try {
    $archive.GetEntry('word/document.xml').Delete()
    $entry = $archive.CreateEntry('word/document.xml')
    $writer = [System.IO.StreamWriter]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false))
    $writer.Write($xml)
    $writer.Dispose()
} finally { $archive.Dispose() }
Get-Item -LiteralPath $destination | Select-Object FullName,Length

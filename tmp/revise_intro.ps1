$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$introPath = 'C:\work_space\TTS\docs\GioiThieuSI_TTS_A4.docx'
$replacements = @(
    '• Tạo giọng đọc tiếng Việt: Lựa chọn phong cách Tự nhiên, Tin tức hoặc Kể chuyện; tùy chỉnh tốc độ, cao độ và âm lượng phù hợp với nội dung.',
    '• Chuyển tài liệu thành lời đọc: Nhập văn bản trực tiếp hoặc từ tệp TXT, SRT, Word và PDF có lớp văn bản, tiết kiệm thời gian nhập liệu.',
    '• Nghe thử và xuất âm thanh: Kiểm tra lời đọc trước khi lưu thành tệp MP3 hoặc WAV để sử dụng cho video, bài giảng và nội dung thuyết minh.',
    '• Cá nhân hóa giọng nói: Tạo hồ sơ giọng từ mẫu âm thanh, lưu và quản lý để sử dụng cho những lần tạo nội dung tiếp theo.',
    '• Chủ động sử dụng offline: Tạo giọng nói ngay trên máy tính sau khi cài đầy đủ mô hình, không cần gửi văn bản hoặc mẫu giọng lên dịch vụ trực tuyến.'
)
$zip = [System.IO.Compression.ZipFile]::Open($introPath, [System.IO.Compression.ZipArchiveMode]::Update)
try {
    $reader = [System.IO.StreamReader]::new($zip.GetEntry('word/document.xml').Open())
    [xml]$doc = $reader.ReadToEnd()
    $reader.Dispose()
    $ns = [System.Xml.XmlNamespaceManager]::new($doc.NameTable)
    $ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    $featureParagraphs = @($doc.SelectNodes('//w:body/w:p', $ns) | Where-Object {
        $text = ($_.SelectNodes('.//w:t', $ns) | ForEach-Object { $_.InnerText }) -join ''
        $text.StartsWith('• ')
    })
    if ($featureParagraphs.Count -ne 5) { throw 'Expected five feature paragraphs; document was not changed.' }
    for ($i = 0; $i -lt 5; $i++) {
        $nodes = $featureParagraphs[$i].SelectNodes('.//w:t', $ns)
        $nodes[0].InnerText = $replacements[$i]
        for ($j = 1; $j -lt $nodes.Count; $j++) { $nodes[$j].InnerText = '' }
    }
    $zip.GetEntry('word/document.xml').Delete()
    $writer = [System.IO.StreamWriter]::new($zip.CreateEntry('word/document.xml').Open(), [System.Text.UTF8Encoding]::new($false))
    $writer.Write($doc.OuterXml)
    $writer.Dispose()
} finally { $zip.Dispose() }
$verifyZip = [System.IO.Compression.ZipFile]::OpenRead($introPath)
try {
    $reader = [System.IO.StreamReader]::new($verifyZip.GetEntry('word/document.xml').Open())
    [xml]$verified = $reader.ReadToEnd()
    $reader.Dispose()
    foreach ($replacement in $replacements) {
        if (-not $verified.DocumentElement.InnerText.Contains($replacement)) { throw 'Content verification failed.' }
    }
} finally { $verifyZip.Dispose() }
Write-Output 'Updated and verified five feature paragraphs.'

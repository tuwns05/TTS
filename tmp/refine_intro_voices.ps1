$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$path = 'C:\work_space\TTS\docs\GioiThieuSI_TTS_A4.docx'
$intro = 'SI-TTS là phần mềm chuyển văn bản tiếng Việt thành giọng nói trên máy tính Windows, hỗ trợ tạo lời đọc cho bài giảng, video, bản tin và tài liệu thuyết minh. Với nhiều giọng đọc có sẵn cùng khả năng tùy chỉnh cách đọc, người dùng có thể lựa chọn giọng phù hợp với từng nội dung, nghe thử và xuất âm thanh để sử dụng.'
$voices = '• Nhiều giọng đọc để lựa chọn: Cung cấp các giọng đọc tiếng Việt có sẵn, giúp người dùng chọn giọng phù hợp với nội dung và đối tượng nghe.'
$styles = '• Linh hoạt cách thể hiện: Chọn phong cách Tự nhiên, Tin tức hoặc Kể chuyện; điều chỉnh tốc độ, cao độ và âm lượng theo nhu cầu.'
function Set-ParagraphText($paragraph, [string]$value, $ns) {
    $texts = $paragraph.SelectNodes('.//w:t', $ns)
    $texts[0].InnerText = $value
    for ($i = 1; $i -lt $texts.Count; $i++) { $texts[$i].InnerText = '' }
}
$zip = [System.IO.Compression.ZipFile]::Open($path, [System.IO.Compression.ZipArchiveMode]::Update)
try {
    $reader = [System.IO.StreamReader]::new($zip.GetEntry('word/document.xml').Open())
    [xml]$doc = $reader.ReadToEnd()
    $reader.Dispose()
    $ns = [System.Xml.XmlNamespaceManager]::new($doc.NameTable)
    $ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    $introParagraph = $null
    $voiceParagraph = $null
    foreach ($paragraph in $doc.SelectNodes('//w:body/w:p', $ns)) {
        $text = ($paragraph.SelectNodes('.//w:t', $ns) | ForEach-Object { $_.InnerText }) -join ''
        if ($text.StartsWith('SI-TTS là ')) { $introParagraph = $paragraph }
        if ($text.StartsWith('• Tạo giọng đọc tiếng Việt:')) { $voiceParagraph = $paragraph }
    }
    if ($null -eq $introParagraph -or $null -eq $voiceParagraph) { throw 'Expected paragraphs missing; no changes saved.' }
    Set-ParagraphText $introParagraph $intro $ns
    Set-ParagraphText $voiceParagraph $voices $ns
    $styleParagraph = $voiceParagraph.CloneNode($true)
    Set-ParagraphText $styleParagraph $styles $ns
    [void]$voiceParagraph.ParentNode.InsertAfter($styleParagraph, $voiceParagraph)
    $zip.GetEntry('word/document.xml').Delete()
    $writer = [System.IO.StreamWriter]::new($zip.CreateEntry('word/document.xml').Open(), [System.Text.UTF8Encoding]::new($false))
    $writer.Write($doc.OuterXml)
    $writer.Dispose()
} finally { $zip.Dispose() }
$zip = [System.IO.Compression.ZipFile]::OpenRead($path)
try {
    $reader = [System.IO.StreamReader]::new($zip.GetEntry('word/document.xml').Open())
    [xml]$check = $reader.ReadToEnd()
    $reader.Dispose()
    foreach ($value in @($intro, $voices, $styles)) {
        if (-not $check.DocumentElement.InnerText.Contains($value)) { throw 'Verification failed.' }
    }
} finally { $zip.Dispose() }
Write-Output 'Introduction and voice selection updated and verified.'

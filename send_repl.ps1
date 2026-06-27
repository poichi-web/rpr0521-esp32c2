$port = New-Object System.IO.Ports.SerialPort 'COM3', 115200
$port.ReadTimeout = 3000
$port.Encoding = [System.Text.Encoding]::GetEncoding('iso-8859-1')
$port.Open()
Start-Sleep -Milliseconds 300

# Ctrl+C to interrupt
$port.Write([byte[]](0x03), 0, 1)
Start-Sleep -Milliseconds 500

# Ctrl+E = paste mode
$port.Write([byte[]](0x05), 0, 1)
Start-Sleep -Milliseconds 300

# Send script line by line
$script = [System.IO.File]::ReadAllText('c:\dev\rpr0521_test\rpr0521_upython.py', [System.Text.Encoding]::UTF8)
foreach ($line in ($script -split "`n")) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($line.TrimEnd() + "`r`n")
    $port.Write($bytes, 0, $bytes.Length)
    Start-Sleep -Milliseconds 5
}

# Ctrl+D to execute
$port.Write([byte[]](0x04), 0, 1)
Start-Sleep -Seconds 4

# Read output
$out = ''
for ($i=0; $i -lt 30; $i++) {
    try { $out += $port.ReadLine() + "`n" } catch { break }
}
$port.Close()
Write-Host $out

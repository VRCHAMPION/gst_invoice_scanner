$files = @('results.js', 'history.js', 'companies.js', 'analytics.js', 'page-upload.js')
$base = 'd:\projects\gst_invoice_scanner\frontend\js\'

foreach ($file in $files) {
    $path = $base + $file
    $lines = Get-Content $path
    $newLines = @()
    foreach ($line in $lines) {
        # Skip lines that are ONLY "headers: getAuthHeaders()" (with optional comma/whitespace)
        if ($line -match '^\s*headers:\s*getAuthHeaders\(\),?\s*$') {
            continue
        }
        # Remove ...getAuthHeaders() from spread patterns
        $line = $line -replace ',\s*\.\.\.getAuthHeaders\(\)', ''
        $line = $line -replace '\.\.\.getAuthHeaders\(\),?\s*', ''
        # Clean up headers: { 'Content-Type': '...', } -> headers: { 'Content-Type': '...' }
        $line = $line -replace ",\s*}", ' }'
        $newLines += $line
    }
    Set-Content $path ($newLines -join "`r`n")
    Write-Host "Cleaned: $file"
}

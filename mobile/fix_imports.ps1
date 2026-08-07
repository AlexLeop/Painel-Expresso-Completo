$files = Get-ChildItem -Path "c:\Users\lxleo\Documents\Expresso Neves\Painel Expresso Neves e Django DRF\mobile\app\src\main\java\com\nevesgo\app\presentation" -Filter "*.kt" -Recurse

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw

    $changed = $false
    
    if ($content -notmatch "import com\.nevesgo\.app\.ui\.theme\.\*") {
        $content = $content -replace "(?m)^(package .*`r?`n)","`$1`r`nimport com.nevesgo.app.ui.theme.*"
        $changed = $true
    }
    
    if ($content -match "\bColor\b" -and $content -notmatch "import androidx\.compose\.ui\.graphics\.Color") {
        $content = $content -replace "(?m)^(import com\.nevesgo\.app\.ui\.theme\.\*`r?`n)","`$1import androidx.compose.ui.graphics.Color`r`n"
        $changed = $true
    }
    
    if ($content -match "\bborder\b" -and $content -notmatch "import androidx\.compose\.foundation\.border") {
        $content = $content -replace "(?m)^(import com\.nevesgo\.app\.ui\.theme\.\*`r?`n)","`$1import androidx.compose.foundation.border`r`n"
        $changed = $true
    }
    
    if ($content -match "\bBorderStroke\b" -and $content -notmatch "import androidx\.compose\.foundation\.BorderStroke") {
        $content = $content -replace "(?m)^(import com\.nevesgo\.app\.ui\.theme\.\*`r?`n)","`$1import androidx.compose.foundation.BorderStroke`r`n"
        $changed = $true
    }

    if ($changed) {
        Set-Content -Path $file.FullName -Value $content -NoNewline
        Write-Host "Updated $($file.Name)"
    }
}

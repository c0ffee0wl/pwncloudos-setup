# PowerShell profile - managed by pwncloudos-setup (ported from linux-setup)
# UTF-8 for correct ANSI/glyph rendering. Wrapped: setting console encoding can
# throw when stdout is redirected / no real console is attached. Mostly a no-op
# on PS 7 (already UTF-8) but fixes glyphs on Windows PowerShell 5.1.
try {
    $OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new()
    [Console]::InputEncoding = [Text.UTF8Encoding]::new()
} catch {}

# ls-style helpers (-Force shows hidden; -Hidden alone would show ONLY hidden)
function l  { Get-ChildItem @args }
function la { Get-ChildItem -Force @args }
function ll { Get-ChildItem -Force @args }
# This is the All-Hosts profile, so reload that one (not $PROFILE = current-host)
function Update-Profile { . $PROFILE.CurrentUserAllHosts }
Set-Alias reload Update-Profile

Import-Module PSReadLine -ErrorAction SilentlyContinue
$hasPSReadLine = $null -ne (Get-Module PSReadLine)
if ($hasPSReadLine) {
    Set-PSReadLineOption -HistoryNoDuplicates -HistorySearchCursorMovesToEnd `
                         -BellStyle None -MaximumHistoryCount 10000
    Set-PSReadLineKeyHandler -Key Tab        -Function MenuComplete
    Set-PSReadLineKeyHandler -Key UpArrow    -Function HistorySearchBackward
    Set-PSReadLineKeyHandler -Key DownArrow  -Function HistorySearchForward
    Set-PSReadLineKeyHandler -Chord 'Ctrl+LeftArrow'  -Function BackwardWord
    Set-PSReadLineKeyHandler -Chord 'Ctrl+RightArrow' -Function ForwardWord

    # Predictive IntelliSense - feature-detect (PSReadLine 2.1+; plugins need 7.2+).
    # Keep PowerShell's default InlineView (ListView warns in small / VS Code
    # windows); press F2 to switch to ListView - the ListPrediction colors cover it.
    if ((Get-Command Set-PSReadLineOption).Parameters.ContainsKey('PredictionSource')) {
        $src = if ($PSVersionTable.PSVersion -ge [version]'7.2') { 'HistoryAndPlugin' } else { 'History' }
        Set-PSReadLineOption -PredictionSource $src
    }
}

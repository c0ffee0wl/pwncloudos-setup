# === Light-background theme (a light terminal was detected during setup) ===
# Colors mimic the PowerShell ISE light theme. PS 7.2+ uses the native $PSStyle
# API; Windows PowerShell 5.1 falls back to ConsoleColor names (no $PSStyle).
if ($PSVersionTable.PSVersion -ge [version]'7.2') {
    $ISETheme = @{
        Command                  = $PSStyle.Foreground.FromRGB(0x0000FF)
        Comment                  = $PSStyle.Foreground.FromRGB(0x006400)
        ContinuationPrompt       = $PSStyle.Foreground.FromRGB(0x0000FF)
        Default                  = $PSStyle.Foreground.FromRGB(0x0000FF)
        Emphasis                 = $PSStyle.Foreground.FromRGB(0x287BF0)
        Error                    = $PSStyle.Foreground.FromRGB(0xE50000)
        InlinePrediction         = $PSStyle.Foreground.FromRGB(0x93A1A1)
        Keyword                  = $PSStyle.Foreground.FromRGB(0x00008b)
        ListPrediction           = $PSStyle.Foreground.FromRGB(0x06DE00)
        Member                   = $PSStyle.Foreground.FromRGB(0x000000)
        Number                   = $PSStyle.Foreground.FromRGB(0x800080)
        Operator                 = $PSStyle.Foreground.FromRGB(0x757575)
        Parameter                = $PSStyle.Foreground.FromRGB(0x000080)
        String                   = $PSStyle.Foreground.FromRGB(0x8b0000)
        Type                     = $PSStyle.Foreground.FromRGB(0x008080)
        Variable                 = $PSStyle.Foreground.FromRGB(0xff4500)
        ListPredictionSelected   = $PSStyle.Background.FromRGB(0x93A1A1)
        Selection                = $PSStyle.Background.FromRGB(0x00BFFF)
    }
    if ($hasPSReadLine) { Set-PSReadLineOption -Colors $ISETheme }

    # Text formatting colors
    $PSStyle.Formatting.FormatAccent       = $PSStyle.Foreground.Green
    $PSStyle.Formatting.TableHeader        = $PSStyle.Foreground.Green
    $PSStyle.Formatting.ErrorAccent        = $PSStyle.Foreground.Cyan
    $PSStyle.Formatting.Error              = $PSStyle.Foreground.Red
    $PSStyle.Formatting.Warning            = $PSStyle.Foreground.Yellow
    $PSStyle.Formatting.Verbose            = $PSStyle.Foreground.Yellow
    $PSStyle.Formatting.Debug              = $PSStyle.Foreground.Yellow
    $PSStyle.Progress.Style                = $PSStyle.Foreground.Yellow

    # File system colors (listing files)
    $PSStyle.FileInfo.Directory            = $PSStyle.Background.FromRgb(0x2f6aff) + $PSStyle.Foreground.BrightWhite
    $PSStyle.FileInfo.SymbolicLink         = $PSStyle.Foreground.Cyan
    $PSStyle.FileInfo.Executable           = $PSStyle.Foreground.BrightMagenta
    $PSStyle.FileInfo.Extension['.ps1']    = $PSStyle.Foreground.Cyan
    $PSStyle.FileInfo.Extension['.ps1xml'] = $PSStyle.Foreground.Cyan
    $PSStyle.FileInfo.Extension['.psd1']   = $PSStyle.Foreground.Cyan
    $PSStyle.FileInfo.Extension['.psm1']   = $PSStyle.Foreground.Cyan
} elseif ($hasPSReadLine) {
    # Windows PowerShell 5.1: dark ConsoleColor names for contrast on white
    Set-PSReadLineOption -Colors @{
        Command   = 'DarkBlue'
        Parameter = 'DarkGray'
        Operator  = 'Black'
        String    = 'DarkCyan'
        Variable  = 'DarkGreen'
        Type      = 'DarkMagenta'
        Number    = 'DarkRed'
        Member    = 'Black'
        Comment   = 'Gray'
        Error     = 'Red'
    }
}

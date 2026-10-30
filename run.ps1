# Run the eval on Windows even when Python is not on PATH.
param(
    [switch]$Test,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$EvalArgs
)
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pyCommand = Get-Command py -ErrorAction SilentlyContinue
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pythonPrefix = @()
if ($pythonCommand) {
    $pythonExecutable = $pythonCommand.Source
} elseif ($pyCommand) {
    $pythonExecutable = $pyCommand.Source
    $pythonPrefix = @('-3')
} elseif (Test-Path -LiteralPath $bundledPython) {
    $pythonExecutable = $bundledPython
} else {
    Write-Error 'Install Python 3.11 or newer, reopen PowerShell, then try again.'
    exit 1
}
Push-Location $PSScriptRoot
try {
    if ($Test) {
        & $pythonExecutable @pythonPrefix -m unittest discover -s tests -v
    } else {
        & $pythonExecutable @pythonPrefix (Join-Path $PSScriptRoot 'run_eval.py') @EvalArgs
    }
    $evalExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $evalExitCode

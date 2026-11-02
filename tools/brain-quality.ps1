$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\brain-quality.py" @args
exit $LASTEXITCODE

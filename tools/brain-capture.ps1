$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\brain-capture.py" @args
exit $LASTEXITCODE

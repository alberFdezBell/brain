$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\brain-ask.py" @args
exit $LASTEXITCODE

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\brain-session.py" @args
exit $LASTEXITCODE

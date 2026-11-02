$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$PSScriptRoot\brain-doctor.py" @args
exit $LASTEXITCODE

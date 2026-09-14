param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('start','finish','stop','status','save','new-record','add-record','batch-record','assemble-pack','assemble-unit','report')][string]$Action,
    [Parameter(Mandatory=$true, Position=1)][string]$Workbench,
    [Parameter(Position=2)][string]$Unit,
    [string]$Items,
    [string]$Note = '',
    [string]$Target,
    [string]$Source,
    [string]$Pack,
    [string]$RecordType,
    [switch]$KeepUnitOpen,
    [string]$Step,
    [ValidateSet('success','failure')][string]$Outcome,
    [ValidateSet('business','adapter')][string]$Layer = 'business',
    [string]$EventId,
    [string]$PythonExecutable
)
$ErrorActionPreference = 'Stop'
$runtimePython = $env:TRAVEL_GUIDE_PYTHON
if (-not $runtimePython) {
    $runtimePython = $PythonExecutable
}
if (-not $runtimePython) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notmatch 'WindowsApps') { $runtimePython = $pythonCommand.Source }
}
if (-not $runtimePython -or -not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
    [Console]::Error.WriteLine('Set TRAVEL_GUIDE_PYTHON to a Python 3.10+ executable with Pillow, then resume the current workbench.')
    exit 2
}
if ($Action -eq 'report') {
    if (-not $Step -or -not $Outcome) { Write-Error 'report requires -Step and -Outcome'; exit 2 }
    $cliArgs = @('-X','utf8',(Join-Path $PSScriptRoot 'record_operation.py'),$Workbench,$Step,$Outcome,'--layer',$Layer)
    if ($EventId) { $cliArgs += @('--event-id',$EventId) }
} elseif ($Action -eq 'assemble-unit') {
    if (-not $Pack) { Write-Error 'assemble-unit requires -Pack'; exit 2 }
    $cliArgs = @('-X','utf8',(Join-Path $PSScriptRoot 'assemble_research_unit.py'),$Workbench,$Pack)
} elseif ($Action -in @('new-record','add-record','batch-record','assemble-pack')) {
    if (-not $Pack) { Write-Error 'Record operations require -Pack'; exit 2 }
    $recordAction = @{ 'new-record'='new'; 'add-record'='add'; 'batch-record'='batch'; 'assemble-pack'='assemble' }[$Action]
    $cliArgs = @('-X','utf8',(Join-Path $PSScriptRoot 'research_records.py'),$recordAction,$Workbench,$Pack)
    if ($Action -eq 'new-record') { $cliArgs += @('--id',$Unit,'--type',$RecordType) }
    if ($Action -in @('add-record','batch-record')) { $cliArgs += @('--record',$Source) }
    if ($Action -ne 'new-record' -and -not $KeepUnitOpen) { $cliArgs += '--finish-unit' }
} elseif ($Action -eq 'save') {
    if (-not $Target -or -not $Source) {
        Write-Error 'save requires -Target and -Source; paths may be relative to Workbench.'
        exit 2
    }
    $targetPath = if ([IO.Path]::IsPathRooted($Target)) { $Target } else { Join-Path $Workbench $Target }
    $sourcePath = if ([IO.Path]::IsPathRooted($Source)) { $Source } else { Join-Path $Workbench $Source }
    $cliArgs = @('-X','utf8',(Join-Path $PSScriptRoot 'write_research_json.py'),$targetPath,'--from-file',$sourcePath,'--workbench',$Workbench,'--finish-unit')
    if ($Pack) { $cliArgs += @('--pack-id',$Pack) }
} else {
    $cliArgs = @('-X','utf8',(Join-Path $PSScriptRoot 'research_checkpoint.py'),$Workbench,$Action)
    if ($Action -eq 'start') {
        if (-not $Unit -or -not $Items) {
            Write-Error 'start requires Unit and -Items with comma-separated concrete record IDs.'
            exit 2
        }
        $cliArgs += @('--unit',$Unit,'--items')
        $cliArgs += @($Items.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if ($Note) { $cliArgs += @('--note',$Note) }
}
& $runtimePython @cliArgs
$operationExitCode = $LASTEXITCODE
if ($Action -ne 'report') {
    $operationStep = "$Action|$Pack|$Unit|$Target|$Source"
    $operationOutcome = if ($operationExitCode -eq 0) { 'success' } else { 'failure' }
    # Reporter output is suppressed to keep the command's original stdout schema;
    # the record is available at .research-state/operation-results.json.
    & $runtimePython -X utf8 (Join-Path $PSScriptRoot 'record_operation.py') $Workbench $operationStep $operationOutcome | Out-Null
    if ($LASTEXITCODE -eq 2 -and $operationExitCode -eq 0) { $operationExitCode = 2 }
}
exit $operationExitCode

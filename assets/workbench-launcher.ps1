param(
    [Parameter(Mandatory=$true, Position=0)][string]$Action,
    [Parameter(Position=1)][string]$Unit,
    [string]$Items,
    [string]$Note,
    [string]$Target,
    [string]$Source,
    [string]$Pack,
    [string]$RecordType,
    [switch]$KeepUnitOpen,
    [string]$Step,
    [string]$Outcome,
    [string]$Layer,
    [string]$EventId
)
$ErrorActionPreference = 'Stop'
$boundArguments = @{}
foreach ($entry in $PSBoundParameters.GetEnumerator()) {
    $boundArguments[$entry.Key] = $entry.Value
}
$boundArguments['Workbench'] = $PSScriptRoot
$boundArguments['PythonExecutable'] = '__PYTHON_EXECUTABLE__'
& '__SKILL_WRAPPER__' @boundArguments
exit $LASTEXITCODE

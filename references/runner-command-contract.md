# Runner setup and optional record recovery

The Skill uses Python CLIs, not a particular agent tool API. Use the host's documented shell or process tool. Python 3.10+ with Pillow is required; verify the interpreter with `scripts/runtime_preflight.py`. Run commands from the Skill root or use absolute script paths. Quote paths for the actual shell, including spaces and non-ASCII characters.

Final JavaScript syntax checks require an existing Node executable. Reuse the host's runtime: if it is outside PATH, set `TRAVEL_GUIDE_NODE` for the controller process (or pass `--node` to a standalone `quick_forward_test.py`). Do not silently skip syntax checks or install a second runtime merely because PATH discovery failed.

For normal production, follow `production-flow.md`: write and validate complete packs. Record timers and assembly commands below are optional recovery tools, not required steps.

Initialization prints `CONTINUE_ARGV`, a JSON array containing the verified interpreter, absolute status script and workbench path. Execute these arguments with the host's process API, or quote each argument appropriately in its shell. Do not paste the array as a shell command or invent a Codex/DeepSeek-specific tool identifier.

`research_status.py` exits 2 while packs remain incomplete and prints the next batch. This is a pending research state, not an interpreter failure. Read each command's output and status semantics before retrying.

`research_status.py` is stateful: it writes research-plan.json and .contract-errors, may repair safe JSON syntax, and invokes compilation when packs pass. For forensic read-only checks, use a disposable copy and compare source hashes. Preserve the child process exit code; a later successful print/cleanup command can hide it in a shell wrapper. Contract failure returns 2, completion returns 0.

Cross-platform Python examples (replace both paths):

```text
python /path/to/skill/scripts/research_status.py /path/to/workbench
python /path/to/skill/scripts/research_checkpoint.py /path/to/workbench status
python /path/to/skill/scripts/research_records.py --help
python /path/to/skill/scripts/assemble_research_unit.py --help
```

## Optional PowerShell launcher

### Host recovery without a new production run

If a Bash environment lacks basic commands or reports success without artifacts, use the host's available process tool with the verified Python executable, or native PowerShell commands on Windows. Do not spend production time repairing an unrelated Bash toolchain. A process exit code of zero alone is not asset completion: verify that the expected output files exist, decode, and match the official receipt report. Capture stdout, stderr and the actual child's exit code together; never let a later print or cleanup mask failure.

For research failures, inspect the per-pack `.contract-errors/<pack>.json` and full compiler `.contract-errors/compiled-profile.txt`; fix the reported owning data as a batch. The compact authoring checklist is in research-data-shapes.md, including photography/outfits, food groups and coordinates. Do not read every validator source before starting a trip.

For image failures, use fetch-recovery.md: keep useful text-only souvenirs, declare verified same-place reuse explicitly, and import legitimately acquired local files using import_local_assets.py rather than writing receipts by hand. A non-public DNS answer and an unresolved hostname are different failures. Host security denials remain binding; neither unrestricted urllib nor manual receipts is a permitted workaround. A SIGTERM without preserved stderr is an unknown external termination, not proof that the image helper itself is broken. Preserve completed records and rerun only the failed bounded batch after diagnosis. Existing 429 host backoff remains in force.

On every host, prefer the verified Python executable and the absolute script/workbench paths. Initialization prints `CONTINUE_ARGV`, an argument array ready for the host command tool. On Windows, initialization also writes optional `travel.ps1`. Its absolute path binds the workbench; the caller may use any working directory. If script execution is disabled, use the direct Python CLI; do not change execution policy, unblock files or add bypass flags to use this Skill. Set `TRAVEL_GUIDE_PYTHON` to the selected Python executable if launcher discovery fails. Use each CLI's `--help` for its arguments; PowerShell flag names are not Python flags.

The launcher regression class first probes a harmless script under the existing policy. A recognized policy denial is reported as skipped, not passed; other probe failures remain failures. Direct Python tests still run. Do not describe a suite with skipped launcher checks as proof that PowerShell works.

```powershell
& '<absolute workbench>/travel.ps1' status
```

Each command below is one alternative action after the absolute launcher path, never a shell command chain:

```powershell
& '<absolute workbench>/travel.ps1' start core-01 -Items 'place-a'
& '<absolute workbench>/travel.ps1' new-record place-a -Pack places-core -RecordType sight
& '<absolute workbench>/travel.ps1' add-record -Pack places-core -Source 'research/drafts/place-a.next.json'
& '<absolute workbench>/travel.ps1' batch-record -Pack places-shopping -Source 'research/drafts/shopping-batch-01'
& '<absolute workbench>/travel.ps1' assemble-unit -Pack places-core
& '<absolute workbench>/travel.ps1' status
& '<absolute workbench>/travel.ps1' finish -Note 'Saved reviewed evidence'
& '<absolute workbench>/travel.ps1' stop -Note 'Actual unit overrun'
```

`start` happens before actual research/authoring. The timer permits at most two core places and defaults to one while Google/identity/image work is unresolved. Do not reset or rename an unfinished unit. `new-record` creates one null-filled object to complete; it is never finished research.

`add-record` validates one object, atomically stores it by ID and finishes the active timer. Use `-KeepUnitOpen` only for an intermediate write in a previously planned two-place unit. `batch-record` takes an isolated directory of independent record JSON files, validates every record before writing any, then saves them and finishes the active timer. It supports all four place packs, including shopping and restaurants (`places-food`). Do not mix image request/metadata JSON in that record directory. A failed batch preserves previously accepted records.

`assemble-unit` is the default full-pack assembly command: after all required records exist, it checks idle state, starts a mechanical assembly timer, assembles all records, validates the canonical pack, atomically saves it and finishes the timer. It refuses to steal another active timer. Each attempt fingerprints the semantic record collection and actual validator dependencies. After a validator gap (for example missing core support), save the corrected records with `batch-record` and invoke the same `assemble-unit` command: changed inputs create a new numbered attempt. Unchanged input, including whitespace-only edits or reverting to a previously failed hash, is rejected and counts as a delivered command failure. Never rename a timer to bypass this. The attempt ledger retains errors and every original timer; active same-hash retries reuse their start time, and five-minute overruns still stop. `status` exposes cumulative assembly phase wall time and attempt elapsed totals, including failed attempts; repair gaps remain in phase wall time. No separate status/start/validate/finish calls are needed. The final compiler retains all counts, cross-pack relationships and provenance requirements.

For a final non-place JSON write, `save -Target 'research/framing.json' -Source 'research/framing.next.json' -Pack framing` combines atomic save, local validation and finish. Omit `-Pack` for explicit partial drafts only. Intermediate writes use the existing Python writer without `--finish-unit`. A saved file does not excuse an overrun: elapsed time over 300 seconds still returns code 2.

## Failure accounting

The PowerShell wrapper records delivered command results in `.research-state/operation-results.json`. Two consecutive failed business commands with the same key trigger repeat-stop in the optional recovery workflow. An invocation rejected before the script runs is an adapter error, not a data-validation result. Correct the invocation through the host's supported interface without resetting research or timers. Respect host access denials; changing interfaces is not authorization to bypass them. Active timer wall time includes correction time.

## Workbench-local network session
Before the first external batch, probe one already-selected official host with `network_session.py <workbench> --check-host <hostname>`. A known Fake-IP DNS result is not evidence that the Internet is broken. Only after observing a local compatible proxy may you add `--confirm-known-proxy --evidence "<actual observation>"`. This stores a setting in this workbench, not the installed Skill or global shell. Use `network_session.py <workbench> --run fetch_declared_assets.py <profile> <workbench>` (or another bundled network script) for subsequent commands; child processes inherit the explicit setting. TLS verification and rejection of private/literal addresses remain enabled. Never use this option for ordinary private IPs or to bypass an access denial.

Run `diagnose_build.py <workbench>` after a research/media batch, before rendering, to collect source freshness, text width, missing media fields and pending map reviews together. It does not claim QA or completion; fix owning records in one batch rather than discovering these only at handoff. Place probe images under `qa/` so they cannot enter the public media inventory.

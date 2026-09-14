# Fast build orchestration

Use this reference only when the user explicitly requests subagents/delegation for the current task and the host permits it. Otherwise use one agent, even when parallel-agent slots are available. The goal is lower wall time and context use without weakening the handbook contract; speedup is not guaranteed.

## Decide whether to delegate

- Stay single-agent for a small ordinary build, one-pack repair, render-only change, or any task with fewer than two independent research packs.
- Use subagents when two or more packs can be completed without reading or editing the same target file. Never spawn agents merely because slots are available.
- Choose agents by capability: use the strongest available reasoner for route selection, cross-pack conflicts and editorial judgment; use capable general agents for bounded place or food research; use faster agents for exact-link checks, asset feasibility and mechanical normalization. Model names are examples, not requirements.

## Dependency order

The root agent first fixes the brief, day-area outline, selection criteria and provisional stable place IDs. Parallel research may then cover core places, food, and shopping/experiences. Itinerary and discovery bindings begin only after their referenced place IDs are frozen. Final asset download, compilation, rendering and release gates remain controller-owned deterministic stages.

Do not let multiple agents independently redesign the route or invent competing place inventories. If a research result requires replacing a frozen place, return the proposed replacement and reason to the root agent; only the root agent changes shared IDs.

## Minimal delegation packet

Give each subagent only:

1. Destination, dates/days, travelers, selected interests/constraints and quality mode.
2. One task JSON from `research/tasks/`, its target file and the relevant frozen IDs or area boundary.
3. The exact source, truthfulness and stop-loss rules needed by that task.
4. A requirement to write only its assigned file, validate it immediately and report the file path plus concise exceptions.

Do not send the entire conversation, every reference, validator source, other packs, rendered HTML or previous search transcripts. Generated task JSON is the compact contract. Agents should return structured files rather than long prose summaries.

## Parallel work and merge

- Run at most one writer per target file. Parallelize independent reads and place lookups inside a pack when supported.
- Validate each completed pack on arrival while other agents continue. Reject only the named invalid fields; do not rerun accepted research.
- Preserve successful files and source evidence across retries. Cache compact failed-source incidents so another agent does not repeat the same dead URL or mismatched image.
- After place packs pass, run one root-level coherence check for identity, duplicates, area fit and interest coverage. Do not ask every agent to perform the same global review.

## Token and time controls

- Put stable rules before dynamic trip data in delegation prompts so compatible hosts can reuse prompt prefixes.
- Use low or medium reasoning for bounded extraction and link checks; reserve higher reasoning for route tradeoffs and ambiguous identity conflicts.
- Keep candidate work shallow until selection: verify identity, coordinates and asset feasibility first; research full prose and dynamic facts only for frozen choices.
- Use scripts for scaffolding, schema validation, compilation, asset decoding, hashing, rendering and audits. Do not spend model context reproducing deterministic checks.
- After each major phase, carry forward only accepted facts, file paths, source incidents, unresolved conflicts and the next action. Drop search transcripts and rejected prose.
- For a repair, use the controller's changed-section dependency set and rerun only affected stages. A rating-only or copy-only repair must not trigger broad destination research or image reacquisition.

## User-visible progress

The root agent sends compact updates at meaningful transitions: build started, candidate inventory frozen, research packs completed, assets verified, render complete and final QA. During a long phase, send a status update within roughly one minute even when delegated work is still running. Subagent activity never replaces root-agent communication.

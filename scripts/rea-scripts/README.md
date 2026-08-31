# REA Runtime Scripts

These scripts reproduce REA captures, runtime campaigns, UI probes,
streaming checks, recovery scenarios, and cloud smoke tests. They remain
available for forensic reproduction, but are intentionally outside the normal
maintenance surface.

The authoritative maintenance scripts remain in the parent directory:
build/install, documentation, workflow security, manifest generation, generated
artifact tracking, deterministic health measurement, Nim release verification,
and the operational release gate.

These scripts may reference study scenarios under the project documentation.
They must not be added to the normal shell patch or
the default release path without a new review.

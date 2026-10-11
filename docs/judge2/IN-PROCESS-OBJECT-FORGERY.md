# Judge 2 — Residual in-process object-forgery limitation

## Scope

Judge 2's gate-bound adjudication path is designed to accept validated inputs through the public `adjudicate()` API. The loaded decision contract is checked against its expected SHA-256 digest, and an AST guard checks production code for prohibited direct access to private adjudication helpers.

## Residual limitation

These controls are not a Python sandbox. Code already executing inside the same Python process can deliberately bypass ordinary construction paths and force object state, for example by using low-level object operations to forge an instance. The API boundary, contract-hash verification, and AST guard reduce accidental or unsupported access paths, but they do not establish isolation from hostile code with execution in the same interpreter.

## Defense in depth

The current defense is the combination of:

1. **One public adjudication entry point:** callers submit the structured input to `adjudicate()`; they cannot supply a caller-created gate result through that API.
2. **Contract integrity check:** adjudication verifies the SHA-256 digest of the loaded rules contract against the expected digest.
3. **AST guard:** tests inspect production Python modules for direct references, attribute access, dynamic-string references, and module aliases targeting private adjudication helpers.

Adversarial API probes and the AST-guard tests provide evidence for these specific controls; they are not proof against every possible same-process attack. Do not describe this boundary as a sandbox or as protection against arbitrary malicious Python code executing in-process.

## Future hardening

If the threat model later includes hostile code running in the same interpreter, evaluate process isolation and a narrower serialized interface as a separate design change. Such a change requires its own threat-model review and tests; it is not implied by the current implementation.

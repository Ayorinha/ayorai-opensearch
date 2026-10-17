"""Verifiable audit log — phase 1 core library (ADR-010).

Pure functions only: RFC 6962 Merkle hashing with inclusion and consistency
proofs, and salted commitments for leaves. Nothing here stores events, signs
checkpoints, touches the API or imports the Judge. Until phase 3 is merged
and deployed, no deployment has a verifiable audit log.
"""

from ayorai_attractor.auditlog.commitment import (
    DOMAIN_LABEL,
    SALT_SIZE,
    commit,
    new_salt,
    verify_commitment,
)
from ayorai_attractor.auditlog.merkle import (
    HASH_SIZE,
    consistency_proof,
    empty_root,
    inclusion_proof,
    leaf_hash,
    root_from_inclusion,
    tree_root,
    verify_consistency,
    verify_inclusion,
)

__all__ = [
    "DOMAIN_LABEL",
    "HASH_SIZE",
    "SALT_SIZE",
    "commit",
    "consistency_proof",
    "empty_root",
    "inclusion_proof",
    "leaf_hash",
    "new_salt",
    "root_from_inclusion",
    "tree_root",
    "verify_commitment",
    "verify_consistency",
    "verify_inclusion",
]

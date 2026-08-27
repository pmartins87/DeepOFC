# OpenOFC strategic solver pure migration — c21c3c4

Status: **BYTE_COPY_PASS**

Frozen source: `pmartins87/myoh_private@c21c3c4f1017c83df07eb22230318a8131bf40d1`

- G1 inventory payload SHA-256: `a0e75d22e17d90b98881d324b2721f7c20276a3b9df83a2a7147f24cd9c53e18`
- migrated files: **123**
- all source/target bytes identical: **true**
- provenance-records SHA-256: `b06d189712d76f6943b168b37623ca85501941f6024a2f760e9e8a67db7ba109`
- provenance object SHA-256 (before embedding self-reference field): `473053506acd653008de846f1f80c88351535b1c1d0ab6d667dad9fac794dabe`
- roles: `{"benchmark": 1, "contract": 35, "helper": 1, "source": 48, "test": 38}`

The migration preserves the exact relative path `tools/openofc_solver/...` to avoid mixing namespace/import refactors with ownership transfer.

This result proves byte identity only. Strategic authority remains temporary until independent DeepOFC tests and deterministic old-vs-new behavioral equivalence also pass.

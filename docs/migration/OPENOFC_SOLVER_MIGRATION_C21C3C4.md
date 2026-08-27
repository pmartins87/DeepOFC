# OpenOFC strategic solver pure migration — c21c3c4

Status: **BYTE_COPY_PASS**

Frozen source: `pmartins87/myoh_private@c21c3c4f1017c83df07eb22230318a8131bf40d1`

- G1 v2 inventory payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`
- migrated files: **126**
- all source/target bytes identical: **true**
- provenance-records SHA-256: `fc985fb4d28018a1f9db6cc545323b61a4150a64505b8ccc9f9e653dec29fdca`
- provenance object SHA-256 (before embedding self-reference field): `4041f7560f9a94b5e85b9c1c986f39e690bca5e3635328fad1bff1fdd1b11766`
- roles: `{"benchmark": 2, "contract": 35, "helper": 1, "source": 50, "test": 38}`

The migration preserves the exact relative path `tools/openofc_solver/...` to avoid mixing namespace/import refactors with ownership transfer.

This result proves byte identity only. Strategic authority remains temporary until independent DeepOFC tests and deterministic old-vs-new behavioral equivalence also pass.

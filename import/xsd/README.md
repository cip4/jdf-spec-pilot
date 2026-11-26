# Imported XML schemas (reference input)

These are read-only reference inputs for the bootstrap import. The
specification (MIF tables) remains the source of truth; the schemas only seed
the machine-readable structure.

## xjdf/xjdf.xsd

- XJDF Schema `2.x.146-SNAPSHOT-fa8d5b5` (2026-10-30)
- Source: `cip4/XJDF-Schema` (provided directly by the editor)

## jdf-1.x/*.xsd

- JDF 1.x schema sources (`JDF.xsd`, `JDFCore.xsd`, `JDFTypes.xsd`,
  `JDFResource.xsd`, `JDFResourceElements.xsd`, `JDFProcess.xsd`,
  `JDFMessage.xsd`, `JDFCapability.xsd`)
- Source: restored from `cip4/JDF-Schema` (main, `--depth 1`).

Note: the restored JDF sources still contain the build template placeholders
(`@@version@@`, `@@buildTime@@`); the earlier snapshot that carried
`1.x.102-SNAPSHOT-4d0bafd` was removed by mistake during setup. Drop the exact
snapshot here again if byte-level provenance matters. It does not affect the
XJDF-first import.

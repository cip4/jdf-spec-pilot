# JDF/XJDF Specification — pilot

This repository is a **pilot** for maintaining the CIP4 **JDF / XJDF
specification** as plain Markdown on GitHub, with GitHub Actions doing the
builds.

The goal is a specification that is:

- **easy to edit and review** on github.com, through normal pull requests,
- **built automatically** for all three variants — `JDF 1.x`, `XJDF 2.x` and
  `Both` — from **one common source**, so the variants cannot drift apart,
- **data-driven**: the element and attribute tables are structured data, so the
  same model can also generate the XSD, JSON Schema and diagrams.

> **Status: evaluation, not the release.** Today the authoritative source is
> the FrameMaker project in
> [cip4/JDF-Specification](https://github.com/cip4/JDF-Specification). Nothing
> here replaces it until the conversion has been proven. The **specification
> text always wins** over the XML schemas.

## What is in this repository

```
spec/        Markdown specification pages (the human-readable spec)
  book.yaml  reading order, replacing JDF.book / XJDF.book / Both.book
  config.yaml titles, versions and metadata, replacing Build/*.ini
model/       the data model as YAML (elements, resources, messages, enums, types)
  model.schema.json  the rules for those YAML files
examples/    XML/JSON samples (validated and embedded in CI)
graphics/    SVG diagrams
import/
  mif/       MIF exports of the FrameMaker source (input to the migration)
  xsd/       reference XSDs, plus the generated XSD import (staging)
specbuild/   the Python toolchain (import, reconcile, sync, build)
tests/       automated tests
```

## How it works

### Markdown on GitHub, tables generated from data

Pages are ordinary Markdown and render on github.com without any build. The
model tables are **generated from YAML and committed into the page** between
markers, so GitHub shows them too:

```markdown
<!-- BEGIN GENERATED model:elements/Icon - do not edit -->
| Name | Data Type | Description |
| --- | --- | --- |
| BitDepth (required) | integer | Bit depth of one color. |
...
<!-- END GENERATED model:elements/Icon -->
```

Never edit a generated block by hand. Edit `model/elements/Icon.yaml` and run
`specbuild sync`.

### One source, three variants

Conditional text uses invisible HTML comments, so github.com shows everything
(which is the "Both" document). The build removes them per variant:

```
<!-- jdf --> ... <!-- /jdf -->        only in the JDF 1.x spec
<!-- xjdf --> ... <!-- /xjdf -->      only in the XJDF 2.x spec
<!-- both-only --> ... <!-- /both-only -->   only in the Both spec
<!-- draft --> ... <!-- /draft -->    removed from release builds
```

These correspond to the FrameMaker conditions `JDF-1x`, `JDF-2x`,
`JDF-neither`, `Comment-1x/2x` and the `-background` example variants.

### The data model

Each model file describes one node. Example (`model/elements/Icon.yaml`):

```yaml
name: Icon
kind: element
variants: [jdf, xjdf]
description: Details of an icon representing a Device.
attributes:
  - name: BitDepth
    type: integer
    required: true
  - name: IconUsage
    type: enumerations
    values: { from: DeviceStatus, multiple: true }
elements:
  - name: FileSpec
    cardinality: "?"
```

Supported fields include `kind`, `abstract`, `substitutes`, `extends`,
`variants`, `history`, `attributes`, `elements`, `values`, `base`, `itemType`,
`union` and `facets`. The full rules are in `model/model.schema.json`.

## Getting started

Requires Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"

specbuild check                    # validate the model and generated blocks
specbuild sync                     # regenerate generated blocks
specbuild build --variant both     # build HTML for the Both spec
specbuild build --variant jdf --release --out build/jdf
python -m pytest -q
```

Additional commands used during the migration:

```bash
specbuild import-xsd     # XJDF XSD -> import/xsd/xjdf/ (staging, not model/)
specbuild reconcile      # -> import/reconcile-report.md
specbuild roundtrip      # import -> emit XSD -> re-import proof
```

## Bootstrapping from the XML schemas (XJDF first)

The XSDs contain the machine-readable structure (elements, types, cardinality,
enumerations). We use them to seed the model, then let the specification text
supply descriptions, defaults, history and the JDF 1.x-only content.

1. `import-xsd` reads `import/xsd/xjdf/xjdf.xsd` and writes YAML into
   `import/xsd/xjdf/` (staging). Inheritance is flattened to match the
   per-element spec tables; substitution groups form the type hierarchy.
2. `reconcile` compares the staged import with `model/` and writes
   `import/reconcile-report.md`. Every difference is resolved in favour of the
   specification text.
3. `roundtrip` proves the pipeline is lossless at model level.

The XJDF import currently yields **370 elements, 45 enumerations and 24 simple
types**, and the round trip passes. The JDF 1.x importer (includes, attribute
groups, `Constraint`/`Version` metadata) is the next step.

## Continuous integration

- **CI** (`.github/workflows/ci.yml`) runs on pull requests, on pushes to
  `main`, and on demand. It runs the tests, validates the model, imports and
  reconciles the XSD, proves the round trip, builds all three variants and
  uploads the previews and the reconciliation report as artifacts.
- **Preview** (`.github/workflows/pages.yml`) publishes the HTML build to
  GitHub Pages. Enable it once under *Settings → Pages → Source: GitHub
  Actions*.

## Roadmap

- [x] model meta-schema, pilot slice, `check` / `sync` / HTML `build`
- [x] XJDF XSD importer and reconciliation report
- [x] model-level XSD round-trip proof
- [x] CI and Pages preview pipeline
- [ ] merge the XJDF import into `model/` (spec text wins)
- [ ] JDF 1.x importer
- [ ] import the MIF files (prose, tables, cross-references, conditions)
- [ ] XSD / JSON Schema generation for release
- [ ] Mermaid diagrams and interactive model browser
- [ ] PDF output (WeasyPrint or Typst)
- [ ] replace the FrameMaker build for releases

## Who this is for

- **Editors**: change prose and tables in Markdown and YAML; the tables update
  from the data.
- **Committee reviewers**: the reconcile report shows where the schemas and the
  specification disagree.
- **Toolchain maintainers**: `specbuild/` is small, typed Python with tests.

## Provenance and licensing

- The specification content originates from
  [cip4/JDF-Specification](https://github.com/cip4/JDF-Specification) and is
  copyright CIP4 Organization.
- The reference schemas in `import/xsd/` keep their original licenses
  (`cip4/XJDF-Schema`, `cip4/JDF-Schema`). They are read-only inputs.
- A repository license must be chosen by CIP4 before any public release of this
  pilot.

See [AGENTS.md](AGENTS.md) for the working rules and conventions of this
repository.

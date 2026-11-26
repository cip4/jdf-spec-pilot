# AGENTS.md

Guidance for anyone (human or AI agent) working in this repository. Read this
before editing. The repository is self-contained: everything needed to build,
test and understand it is listed here.

## What this repository is

A pilot for maintaining the CIP4 **JDF / XJDF specification** as Markdown on
GitHub, with GitHub Actions building the JDF, XJDF and Both variants from one
common source. The FrameMaker project in `cip4/JDF-Specification` is still the
authoritative source until the migration is proven.

## Golden rules

1. **The specification text is the source of truth.** In any conflict between
   the XML schemas and the specification tables, the specification wins.
2. **Never hand-edit generated blocks.** Content between
   `<!-- BEGIN GENERATED ... -->` and `<!-- END GENERATED ... -->` is produced
   from `model/`. Edit the YAML and run `specbuild sync`.
3. **One common model, no drift.** JDF 1.x and XJDF 2.x are expressed with
   variant markers (`variants:` in YAML, HTML comments in prose), never by
   separate divergent copies.
4. **`import/xsd/` is read-only input.** Do not modify the reference `.xsd`
   files. The staged import (`import/xsd/xjdf/{elements,enums,types}`) is
   generated and gitignored.
5. **Descriptions come from the specification**, not from imagination. The XSD
   import supplies structure only; text, defaults, history and JDF 1.x-only
   content come from the MIF tables.
6. **Do not touch binary FrameMaker files here.** MIF exports are the migration
   input; `.fm`/`.book` are not edited in this repository.

## Layout

```
spec/            Markdown pages; book.yaml = reading order; config.yaml = metadata
model/           YAML data model; model.schema.json = rules
specbuild/       Python toolchain (see modules below)
import/xsd/      reference XSDs + generated staging (gitignored)
import/mif/      MIF exports (migration input, add when available)
examples/        XML/JSON samples
graphics/        SVG/PNG
tests/           pytest tests
.github/         CI + Pages workflows and PR template
```

Toolchain modules:

- `specbuild/model.py` — load and validate model YAML (JSON Schema via `jsonschema`).
- `specbuild/render.py` — render a model node to a Markdown table and block.
- `specbuild/sync.py` — replace generated blocks in `spec/**/*.md`.
- `specbuild/build.py` — variant filtering and HTML build.
- `specbuild/xsd_import.py` — import XSD → staging model.
- `specbuild/xsd_emit.py` — emit XSD from the model and run the round trip.
- `specbuild/reconcile.py` — compare staged import with `model/`.
- `specbuild/cli.py` — `specbuild` command.

## Environment

- Python 3.10+ (CI uses 3.12). The shell on Windows is PowerShell, but all
  documented commands are cross-platform.
- Setup:

  ```bash
  python -m pip install -e ".[dev]"
  ```

## Commands

| Command | Purpose |
| --- | --- |
| `specbuild check` | Validate all model YAML and confirm generated blocks are current. |
| `specbuild sync` | Regenerate the generated blocks from `model/`. |
| `specbuild build --variant both\|jdf\|xjdf [--release] [--out DIR]` | Build HTML for a variant. `--release` drops `<!-- draft -->` content. |
| `specbuild import-xsd [--xsd PATH] [--out DIR]` | Import the XJDF XSD into staging. |
| `specbuild reconcile` | Write `import/reconcile-report.md`. |
| `specbuild roundtrip` | Import → emit XSD → re-import; must report `PASS`. |
| `python -m pytest -q` | Run the test suite. |

Before finishing any change run: `python -m pytest -q` and `specbuild check`.

## Generated blocks

In a spec page:

```markdown
<!-- BEGIN GENERATED model:elements/Icon - do not edit; edit model/elements/Icon.yaml -->
...table...
<!-- END GENERATED model:elements/Icon -->
```

- The identifier (`elements/Icon`, `enums/DeviceStatus`, …) is the path under
  `model/` without the `.yaml` extension.
- `specbuild sync` rewrites every block; `specbuild check` fails if any is stale.
- Enum pages use `render_enum`; element/resource/message pages use
  `render_node`.

## Variant comments

| Marker | Shown in |
| --- | --- |
| `<!-- jdf --> ... <!-- /jdf -->` | JDF 1.x build |
| `<!-- xjdf --> ... <!-- /xjdf -->` | XJDF 2.x build |
| `<!-- both-only --> ... <!-- /both-only -->` | Both build only |
| `<!-- draft --> ... <!-- /draft -->` | Draft builds only (removed with `--release`) |

On github.com all blocks are visible, which corresponds to the Both document.

## Data model conventions

Each `model/**/*.yaml` file must satisfy `model/model.schema.json`. Common fields:

- `name`, `kind` (`element|resource|message|enum|type`), `description`
- `variants: [jdf, xjdf]` (omit for both)
- `abstract`, `substitutes`, `extends`, `context`
- `attributes`: `{name, type, required, variants, default, values: {from|list, multiple}, history}`
- `elements`: `{name, cardinality: "1|?|+|*", variants, history}`
- enum: `values: [{name, description, since, deprecated, variants}]`, optional `multiple`
- type: `base`, `itemType`, `union`, `facets`

Normalized type names: `integer`, `string`, `boolean`, `float`, `double`,
`NMTOKEN`, or a custom type name such as `XYPair`.

### Recipes

- **Add or change a node:** edit `model/<bucket>/<Name>.yaml`, run
  `specbuild sync`, then `specbuild check`.
- **Add a spec page:** create `spec/**/<Name>.md` with the two markers, add the
  file to `spec/book.yaml`, run `specbuild sync`.
- **Resolve a reconcile difference:** the specification wins. Update the model
  (or note the decision), then re-run `specbuild reconcile`.
- **Add a variant-only statement:** wrap it in the matching HTML comment marker.

## Import / reconcile / round trip

- The XSD import **flattens inheritance** so each element is self-contained,
  matching the spec tables. Substitution groups and `abstract` are preserved.
- Two elements in XJDF are declared locally (`AddressLine`,
  `OrganizationalUnit`) and therefore have no global node; this is a known,
  harmless gap for the pilot.
- `roundtrip` proves losslessness **at model level**, not byte equality with the
  original XSD. Do not "fix" formatting differences in the generated XSD.

## Testing and CI

- Tests live in `tests/`. Keep them fast; do not require network access.
- CI (`.github/workflows/ci.yml`) runs tests, `check`, `import-xsd` +
  `reconcile`, `roundtrip`, and builds all three variants. Artifacts:
  `spec-previews`, `reconcile-report`.
- Preview (`.github/workflows/pages.yml`) deploys HTML to GitHub Pages once
  Pages is enabled in repository settings.

## Coding conventions

- Python 3.10+, standard library plus `pyyaml`, `jsonschema`, `markdown`.
  Add new dependencies to `pyproject.toml` (`[project].dependencies`).
- Use `yaml.safe_load` / `yaml.safe_dump` only.
- Keep modules small and typed; no network calls in the toolchain or tests.
- Do not add comments that restate code; explain non-obvious intent only.

## Known limitations

- JDF 1.x importer is not implemented yet (includes, attribute groups,
  `Constraint` / `Version` metadata). XJDF is done first by decision.
- The staged import is not yet merged into `model/`; the MIF tables are needed
  for descriptions, defaults, history and JDF-only content.
- PDF output is not implemented yet (planned: WeasyPrint or Typst).
- The provenance of `import/xsd/jdf-1.x/` is the upstream source templates
  (build placeholders), not a built snapshot. Replace if exact provenance is
  required.

## Do not

- Do not edit generated blocks, `import/xsd/*.xsd`, or anything under the
  gitignored staging folders by hand.
- Do not invent specification text or silently change semantics.
- Do not commit `build/`, `_site/`, `.venv/`, or staging output.
- Do not split the model into divergent JDF/XJDF copies.

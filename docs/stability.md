# Stability

taskli 1.0 begins a stability promise. Within the 1.x series, the things below
won't change in a way that breaks your scripts or your data. Breaking changes
wait for 2.0 and are called out in the [changelog](../CHANGELOG.md).

## What stays stable

**The command-line grammar.**

- Flag names and what they mean. New flags and new values can be added;
  existing ones aren't removed or repurposed.
- `LIST` stays the one positional argument.
- One operation runs per call. The exception is `-d`, `-i`, `-u`, and `-rm`,
  which combine freely.
- Exit codes: `0` for success, `1` for a domain error or a partial failure
  (some ids in a batch weren't found), and `2` for a usage error.

**The on-disk schema.**

- Every list and config file carries a `version`. Newer taskli versions can
  upgrade files written by older 1.x versions with `tk --migrate`.
- Any schema change ships with a `tk --migrate` step.
- Loading never rewrites an outdated file. Until you migrate, loading fails
  with an error that points you to `tk --migrate` (see
  [Upgrading files](config.md#upgrading-files)).
- Additive, optional fields don't need a migration.

## What isn't covered

- Rendered output: styling, layout, and colors can change in any release.
- The exact wording of messages. Match on exit codes, not text.
- The Python API. `import taskli` is an implementation detail, not a library.

## Deprecations

Where practical, a flag or behavior that's going away gets at least one minor
release of warning before it's removed in the next major version.

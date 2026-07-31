# Marketplace archive

The marketplace only loads plugin sources referenced by
`.claude-plugin/marketplace.json`. Superseded plugin directories and accidental
duplicate files are kept here for recovery and history instead of remaining in the
active `plugins/` tree.

- `legacy-plugins/2026-07-26/`: versioned plugin directories replaced by a newer source
- `duplicate-files/2026-07-26/`: Finder-style duplicate files such as `VERSION 2`

The shared runtime under `plugins/shared/` is active infrastructure and must not be
archived.

# Public Surface Status

```text
CURRENT_TREE=PUBLIC_SURFACE_BOUNDED
CURRENT_TREE_GATE=PASS
REPOSITORY_STATUS=HOLD
KNOWN_HISTORICAL_REFS=HOLD
CANDIDATE_GENERATION=SOFTWARE_ONLY
REALIZED_CONSEQUENCE=NOT_AUTHORIZED
PHYSICAL_AUTHORITY=NONE
OPERATIONAL_AUTHORITY=NONE
PRODUCTION_AUTHORITY=NONE
```

## State separation

`CANDIDATE_GENERATION != REALIZED_CONSEQUENCE`

The repository may generate, evaluate, and report bounded software candidates. No
candidate, test result, `OPEN` verdict, checksum, or release-gate result authorizes
a physical or operational consequence.

## Meaning

The checked tree has passed the local public-surface verifier. `HOLD` remains active
because legacy tag and closed pull-request references remain reachable and require
separate removal or provider-side purging.

A tree-level result applies only to one exact revision. It does not certify older
commits, tags, forks, caches, attachments, release assets, or external archives.

## Authority

Nothing in this repository authorizes physical action, production deployment,
safety-critical use, or transfer of authority beyond the bounded software surface.

The canonical public claim contract is
[punkt/contracts/claim-levels.md](punkt/contracts/claim-levels.md).

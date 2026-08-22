# Public Claim Levels

The governing separation is:

```text
CANDIDATE_GENERATION != REALIZED_CONSEQUENCE
PHYSICAL_AUTHORITY=NONE
OPERATIONAL_AUTHORITY=NONE
REPOSITORY_STATUS=HOLD
```

A software result is evidence about the declared test surface. It is not authority
to produce an external consequence.

## OPEN

- The artifact is a bounded software demonstrator.
- Its declared test can be reproduced for the exact revision.
- Its output may be reported as a software result within the declared test surface.
- Its authority ends at the software boundary.

## HOLD

- Production suitability.
- Safety or hardware claims.
- Generalization beyond the documented test surface.
- Scientific or physical interpretation without external validation.
- Any transition from candidate output to external consequence.

## KILL

- Treating a demonstrator result as physical or operational authorization.
- Presenting an uncertified artifact as a safety component.
- Publishing protected implementation material through a public path.
- Claiming that an `OPEN` software verdict establishes production, scientific, or
  physical validity.

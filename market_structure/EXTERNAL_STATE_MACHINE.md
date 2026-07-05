# External Structure State Machine

## Normal continuation

```text
WAITING_BOS
    |
    | BOS breaks last confirmed HH/LL
    v
WAITING_PULLBACK
    |
    | pullback pivot forms
    v
WAITING_CONTINUATION
    |
    | continuation pivot forms
    v
WAITING_BOS
```

## Reversal

```text
WAITING_BOS or WAITING_CONTINUATION
    |
    | CHOCH breaks last confirmed HL/LH
    v
WAITING_REVERSAL_PULLBACK
    |
    | reversal pullback pivot forms
    v
WAITING_REVERSAL_CONTINUATION
    |
    | reversal continuation pivot forms
    v
WAITING_REVERSAL_CONFIRMATION
    |
    | BOS confirms candidate direction
    v
WAITING_PULLBACK
```

## Failed reversal

```text
WAITING_REVERSAL_CONTINUATION
or
WAITING_REVERSAL_CONFIRMATION
    |
    | price invalidates candidate pullback
    v
RESTORE_PRE_CHOCH_SNAPSHOT
```

## Derived targets

```text
Normal phases read from confirmed:

BULLISH confirmed:
    BOS   = last_confirmed_HH
    CHOCH = last_confirmed_HL

BEARISH confirmed:
    BOS   = last_confirmed_LL
    CHOCH = last_confirmed_LH

Reversal phases read from candidate:

BULLISH candidate:
    BOS   = candidate.HH
    CHOCH = candidate.HL

BEARISH candidate:
    BOS   = candidate.LL
    CHOCH = candidate.LH
```

Confirmed structure is not overwritten while a reversal is forming. A
candidate structure is promoted to confirmed only after reversal BOS.

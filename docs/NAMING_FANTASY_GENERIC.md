# Fantasy naming rule

DeepOFC has exactly one runtime state named `Fantasy`.

The deal size is data, never part of the mode name:

- `fantasy_card_count=14`
- `fantasy_card_count=15`
- `fantasy_card_count=16`
- `fantasy_card_count=17`

Do not introduce new generic runtime/API names containing `Fantasy15`, `fantasy15`, `FANTASY15`, or equivalent count-bound variants.

Count-specific fixtures may describe the actual captured deal size, but should use explicit evidence wording such as `fantasy_15_cards` rather than implying a separate mode.

This rule applies to recognizers, state enums, source-card APIs, runtime controllers, Confirm regions, logs, tests that describe generic behavior, and new documentation.

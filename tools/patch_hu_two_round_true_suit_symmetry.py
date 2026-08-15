from pathlib import Path

path = Path("deepofc/hu_two_round.py")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        '''BASE_BOARDS = (\n    PlayerBoard(\n        top=_cards(("2c", "2d")),\n        middle=_cards(("4c", "4d", "5c")),\n        bottom=_cards(("8c", "8d", "7c", "7d")),\n    ),\n    PlayerBoard(\n        top=_cards(("2h", "2s")),\n        middle=_cards(("4h", "4s", "5h")),\n        bottom=_cards(("8h", "8s", "7h", "7s")),\n    ),\n)\n''',
        '''BASE_BOARDS = (\n    PlayerBoard(\n        top=_cards(("2c", "2d")),\n        middle=_cards(("4c", "4d", "5c")),\n        bottom=_cards(("Kc", "Kd", "Qc", "Qd")),\n    ),\n    PlayerBoard(\n        top=_cards(("2h", "2s")),\n        middle=_cards(("4h", "4s", "5h")),\n        bottom=_cards(("Kh", "Ks", "Qh", "Qs")),\n    ),\n)\n''',
    ),
    (
        '''ROUND3_HANDS = (\n    (\n        _cards(("Tc", "Jc", "Qc")),\n        _cards(("Td", "Jd", "Qd")),\n    ),\n    (\n        _cards(("Th", "Jh", "Qh")),\n        _cards(("Ts", "Js", "Qs")),\n    ),\n)\n''',
        '''ROUND3_HANDS = (\n    (\n        _cards(("6c", "7c", "8c")),\n        _cards(("6d", "7d", "8d")),\n    ),\n    (\n        _cards(("6h", "7h", "8h")),\n        _cards(("6s", "7s", "8s")),\n    ),\n)\n''',
    ),
    (
        '''ROUND4_HANDS = (\n    (\n        _cards(("Kc", "Ac", "Kd")),\n        _cards(("Kd", "Ad", "Kc")),\n    ),\n    (\n        _cards(("Kh", "Ah", "Ks")),\n        _cards(("Ks", "As", "Kh")),\n    ),\n)\n''',
        '''ROUND4_HANDS = (\n    (\n        _cards(("9c", "Tc", "Jc")),\n        _cards(("9d", "Td", "Jd")),\n    ),\n    (\n        _cards(("9h", "Th", "Jh")),\n        _cards(("9s", "Ts", "Js")),\n    ),\n)\n''',
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"patch anchor not found:\n{old}")
    text = text.replace(old, new, 1)

anchor = (
    '# The fixed boards and private supports use a rank-preserving suit-only mirror.\n'
    '# Chance is intentionally a reduced, uniformly weighted support of 32 physically\n'
)
replacement = (
    '# The fixed boards and private supports use a rank-preserving suit-only mirror.\n'
    '# Bottom starts KK/QQ, Middle starts 44 and private ranks are all distinct\n'
    '# within each round and disjoint across rounds. Every legal terminal is\n'
    '# therefore non-foul: Bottom two-pair always outranks Middle pair of 4s,\n'
    '# which always outranks Top pair of 2s.\n'
    '# Chance is intentionally a reduced, uniformly weighted support of 32 physically\n'
)
if anchor not in text:
    raise SystemExit("comment anchor not found")
text = text.replace(anchor, replacement, 1)

path.write_text(text, encoding="utf-8")
print("HU TWO-ROUND NON-FOUL SUIT SYMMETRY PATCH: APPLIED")

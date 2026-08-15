from pathlib import Path

path = Path("deepofc/hu_two_round.py")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        'SUIT_MIRROR = {"c": "d", "d": "c", "h": "s", "s": "h"}\nRANK_MIRROR = {8: 9, 9: 8}\n',
        'SUIT_MIRROR = {"c": "h", "h": "c", "d": "s", "s": "d"}\n',
    ),
    (
        '''BASE_BOARDS = (\n    PlayerBoard(\n        top=_cards(("2c", "2h")),\n        middle=_cards(("4c", "4h", "5c")),\n        bottom=_cards(("8c", "8d", "8h", "7c")),\n    ),\n    PlayerBoard(\n        top=_cards(("2d", "2s")),\n        middle=_cards(("4d", "4s", "5d")),\n        bottom=_cards(("9d", "9c", "9s", "7d")),\n    ),\n)\n''',
        '''BASE_BOARDS = (\n    PlayerBoard(\n        top=_cards(("2c", "2d")),\n        middle=_cards(("4c", "4d", "5c")),\n        bottom=_cards(("8c", "8d", "7c", "7d")),\n    ),\n    PlayerBoard(\n        top=_cards(("2h", "2s")),\n        middle=_cards(("4h", "4s", "5h")),\n        bottom=_cards(("8h", "8s", "7h", "7s")),\n    ),\n)\n''',
    ),
    (
        '''ROUND3_HANDS = (\n    (\n        _cards(("Tc", "Jc", "Qc")),\n        _cards(("Th", "Jh", "Qh")),\n    ),\n    (\n        _cards(("Td", "Jd", "Qd")),\n        _cards(("Ts", "Js", "Qs")),\n    ),\n)\n''',
        '''ROUND3_HANDS = (\n    (\n        _cards(("Tc", "Jc", "Qc")),\n        _cards(("Td", "Jd", "Qd")),\n    ),\n    (\n        _cards(("Th", "Jh", "Qh")),\n        _cards(("Ts", "Js", "Qs")),\n    ),\n)\n''',
    ),
    (
        '''ROUND4_HANDS = (\n    (\n        _cards(("Kc", "Ac", "Kh")),\n        _cards(("Kh", "Ah", "Kc")),\n    ),\n    (\n        _cards(("Kd", "Ad", "Ks")),\n        _cards(("Ks", "As", "Kd")),\n    ),\n)\n''',
        '''ROUND4_HANDS = (\n    (\n        _cards(("Kc", "Ac", "Kd")),\n        _cards(("Kd", "Ad", "Kc")),\n    ),\n    (\n        _cards(("Kh", "Ah", "Ks")),\n        _cards(("Ks", "As", "Kh")),\n    ),\n)\n''',
    ),
    (
        '''    return Card(\n        rank=RANK_MIRROR.get(card.rank, card.rank),\n        suit=SUIT_MIRROR[card.suit],\n    )\n''',
        '''    return Card(\n        rank=card.rank,\n        suit=SUIT_MIRROR[card.suit],\n    )\n''',
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"patch anchor not found:\n{old}")
    text = text.replace(old, new, 1)

text = text.replace(
    '# Chance is intentionally a reduced, uniformly weighted support of 32 physically\n',
    '# The fixed boards and private supports use a rank-preserving suit-only mirror.\n'
    '# Chance is intentionally a reduced, uniformly weighted support of 32 physically\n',
    1,
)
path.write_text(text, encoding="utf-8")
print("HU TWO-ROUND TRUE SUIT SYMMETRY PATCH: APPLIED")

from pathlib import Path

path = Path("deepofc/hu_two_round.py")
text = path.read_text(encoding="utf-8")

anchors = {
    "def action_public_key(action: NormalPlacementAction)": "@lru_cache(maxsize=None)\ndef action_public_key(action: NormalPlacementAction)",
    "def _apply(\n": "@lru_cache(maxsize=None)\ndef _apply(\n",
    "    def round3_first_info(self, outcome: TwoRoundChanceOutcome)": "    @lru_cache(maxsize=None)\n    def round3_first_info(self, outcome: TwoRoundChanceOutcome)",
    "    def round3_second_info(\n": "    @lru_cache(maxsize=None)\n    def round3_second_info(\n",
    "    def round4_info(\n": "    @lru_cache(maxsize=None)\n    def round4_info(\n",
    "    def _round3_actions(\n": "    @lru_cache(maxsize=None)\n    def _round3_actions(\n",
    "    def _boards_after_round3(\n": "    @lru_cache(maxsize=None)\n    def _boards_after_round3(\n",
    "    def _round4_actions(\n": "    @lru_cache(maxsize=None)\n    def _round4_actions(\n",
}

for old, new in anchors.items():
    if old not in text:
        raise SystemExit(f"cache patch anchor not found: {old!r}")
    text = text.replace(old, new, 1)

needle = 'class HUTwoRoundSubgame:\n    """Reduced two-round HU OFC extensive-form benchmark with perfect recall."""\n'
replacement = (
    'class HUTwoRoundSubgame:\n'
    '    """Reduced two-round HU OFC extensive-form benchmark with perfect recall.\n\n'
    '    Pure state/action projections are memoized only by immutable canonical\n'
    '    arguments. These caches change no chance support, infoset identity, legal\n'
    '    action, utility or strategy semantics; they only remove repeated exact work.\n'
    '    """\n'
)
if needle not in text:
    raise SystemExit("class docstring anchor not found")
text = text.replace(needle, replacement, 1)

path.write_text(text, encoding="utf-8")
print("HU TWO-ROUND EXACT MEMOIZATION PATCH: APPLIED")

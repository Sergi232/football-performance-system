"""DATA-04 v3 compatibility wrapper.

Extends the validated DATA-04 v2 importer with the approved raw variable
``shots_on_target`` mapped directly from PannaData ``ontargetScoringAtt``.
No derived metric is introduced here.
"""
from __future__ import annotations

import import_demo_player_match_stats_v2 as base

base.STAT_COLUMNS = dict(base.STAT_COLUMNS)
base.STAT_COLUMNS["shots_on_target"] = "ontargetScoringAtt"
base.PAIR_CONSTRAINTS = list(base.PAIR_CONSTRAINTS)
if ("shots_on_target", "shots_total") not in base.PAIR_CONSTRAINTS:
    base.PAIR_CONSTRAINTS.append(("shots_on_target", "shots_total"))


if __name__ == "__main__":
    base.main()

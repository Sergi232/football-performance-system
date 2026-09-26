# Match Rating — product contract

## Purpose

`Match Rating` is the immediate player-match evaluation exposed to the coaching staff after a match. It is deliberately separate from the historical `Performance Index`.

## Operational requirement

After the first processed match of a club, every player with `minutes_played > 0` must have:

- a Match Rating on the `/10` display scale;
- an evidence confidence value;
- a transparent rating context/status;
- observed player-match data available for explanation;
- inclusion in the match report.

No prior club history is required for the Match Rating.

## Historical layer

`Performance Index` is complementary and may use historical/role context for:

- evolution;
- form;
- consistency;
- role profile;
- descriptive trends.

It must not be presented as the per-match rating.

## Missing evidence

Missing evidence must not be silently converted into observed zero. When evidence is insufficient for a complete evaluation, the product keeps the player visible and exposes reduced confidence/status rather than hiding the row or inventing actions.

## Source-role limitation

If an external source labels a played appearance only as `Substitute` without a reliable tactical role, the match report may use a generic rating context. It must not infer a tactical position. The final amateur collector should record the player's entry role so this limitation is avoided in first-party data.

## Goalkeepers

Goalkeepers follow a separate rating path and are never evaluated with outfield positional dimensions.

## LLM boundary

The assistant is downstream of the materialized Match Rating. It may explain the rating and its evidence, but it must not calculate, alter or replace the rating.

## Current experimental versions

- Match Rating: `match_rating_v0.1-experimental`
- Performance Index: `performance_score_v0.2-experimental`

The `/10` presentation transform remains experimental and must be recalibrated before claiming equivalence with any external rating provider.

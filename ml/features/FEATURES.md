# Feature Dictionary — `player_features` (version `v1`)

One row per **player-season** (aggregated across mid-season club moves), built by
`ml/features/build.py` from `player_season_stats`. Promoted context lives in
columns; the numeric feature vector lives in the JSONB `features` blob.

## Context columns (promoted, queryable)

| Column | Type | Definition | Source |
|---|---|---|---|
| `player_id`,`season_id`,`club_id`,`league_id` | FK | Canonical keys (primary club = most minutes) | — |
| `feature_set_version` | str | Feature schema version (`v1`) | — |
| `age` | float | Age in the season = season start year − birth year | players |
| `minutes`,`matches` | int | Season totals (across clubs) | fbref_kaggle |
| `position`,`position_group` | str | Detailed position; group ∈ {GK,DEF,MID,FWD,UNK} | players |
| `club_elo` | float | Club Elo at season end (summer snapshot) | ClubElo |
| `league_strength` | float | Mean club Elo of the league-season | derived |
| `market_value_eur` | int | **Target** — valuation within the season window | Transfermarkt |

## Feature vector (JSONB `features`)

**Per-90 features** — `<metric>_p90` = metric ÷ (minutes/90). Source in parens.

- Attacking: `goals` `assists` `shots` `sot` `npxg` `xag` (fbref_kaggle); `xg` `xa` `np_xg` `xg_chain` `xg_buildup` (understat)
- Creation: `sca` `gca` `key_passes`
- Passing: `pass_cmp` `pass_prog` `prog_pass_dist` `pass_final_third` `ppa`
- Possession: `carries` `carries_prog` `carries_prog_dist` `take_ons_att` `take_ons_succ` `touches` `prog_rec`
- Defense: `tackles` `tackles_won` `tackles_def3rd` `interceptions` `tkl_plus_int` `blocks` `clearances` `dribblers_challenged`
- Misc: `recoveries` `aerials_won` `aerials_lost` `fouls` `fouled`

**Rate features** (unitless ratios): `pass_cmp_pct` (cmp/att), `shot_accuracy` (sot/shots),
`take_on_pct` (succ/att), `aerial_win_pct` (won/(won+lost)), `np_g_per_shot` (goals/shots).

**Percentiles** — for every base feature above, two ranks in [0,1]:
- `<feature>_pct_pos` — percentile within **season × position_group**
- `<feature>_pct_lg` — percentile within **season × league**

Total per row: **44 base + 88 percentile = 132 feature keys.**

## Scaling artifacts (`ml/artifacts/features_v1/`, gitignored, regenerable)

`python -m ml.features.scaler` fits a `StandardScaler` on median-imputed base
features and persists `scaler.joblib`, `feature_names.json` (input contract),
`medians.json` (serve-time imputation), `metadata.json`. Percentile features are
already in [0,1] and are not scaled. Use `ml.features.scaler.transform(...)` to
turn `features` dicts into a model-input matrix.

## Rebuild

```
python -m etl.load --step all      # rebuild normalized DB from raw
python -m ml.features.build        # build player_features (v1)
python -m ml.features.scaler       # fit + save scaler artifacts
```

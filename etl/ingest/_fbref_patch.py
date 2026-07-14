"""FBrefExtended: soccerdata's FBref with the season stat-type gate widened.

soccerdata 1.9.0's `read_player_season_stats` / `read_team_season_stats` only
allow 5 stat types, but their code path is generic — it builds the URL as
`.../{stat_type}/...` and parses the table `id=stats_{stat_type}`. The extra
detailed categories (passing, passing_types, gca, defense, possession) live on
FBref at exactly those slugs, so the only thing stopping us is a conservative
validation list.

Rather than fork/vendor ~90 lines of soccerdata internals (which would rot), we
recompile soccerdata's *own* method source with the allow-list widened, exec'd
against soccerdata's live module namespace so every private helper
(`_parse_table`, `_fix_nation_col`, `FBREF_API`, ...) is the real one. If
soccerdata reformats the list in a future release, `_recompile` fails loudly
instead of silently doing nothing. Pinned to soccerdata==1.9.0 (see pyproject).

The patch is applied IN PLACE on `soccerdata.fbref.FBref` (not a subclass):
soccerdata validates the `leagues` argument against a registry keyed by
`type(self).__name__`, so a subclass named anything other than "FBref" fails
league validation with an empty valid-leagues list. `FBrefExtended` is kept as
an alias to the patched class for readable call sites.
"""

from __future__ import annotations

import inspect
import re
import textwrap
from collections.abc import Iterable

import soccerdata as sd
from soccerdata.fbref import FBref

# FBref-native page slugs. gca == goal & shot creation. keeper_adv omitted: its
# page slug ("keepersadv") differs from its table id, which the generic path
# can't express.
PLAYER_STAT_TYPES = [
    "standard", "keeper", "shooting", "playing_time", "misc",
    "passing", "passing_types", "gca", "defense", "possession",
]
TEAM_STAT_TYPES = [
    "standard", "keeper", "shooting", "playing_time", "misc",
    "passing", "passing_types", "gca", "defense", "possession",
]


def _recompile(method, list_var: str, allowed: Iterable[str]):
    """Return a copy of `method` with its `<list_var> = [...]` allow-list replaced."""
    src = textwrap.dedent(inspect.getsource(method))
    replacement = f"{list_var} = [" + ", ".join(f'"{s}"' for s in allowed) + "]"
    patched, n = re.subn(rf"{list_var}\s*=\s*\[[^\]]*\]", replacement, src, count=1)
    if n != 1:
        raise RuntimeError(
            f"_fbref_patch: could not find `{list_var} = [...]` in "
            f"{method.__qualname__}; soccerdata internals changed."
        )
    namespace: dict = {}
    # exec against a copy of soccerdata.fbref's globals so the recompiled method
    # resolves all the real private helpers.
    exec(patched, dict(vars(sd.fbref)), namespace)  # noqa: S102
    return namespace[method.__name__]


# Patch in place (see module docstring re: league registry keyed on class name).
FBref.read_player_season_stats = _recompile(
    FBref.read_player_season_stats, "player_stats", PLAYER_STAT_TYPES
)
FBref.read_team_season_stats = _recompile(
    FBref.read_team_season_stats, "team_stats", TEAM_STAT_TYPES
)

# Alias so call sites read clearly; it IS soccerdata's FBref, patched.
FBrefExtended = FBref

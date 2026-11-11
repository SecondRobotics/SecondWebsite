import pytest

from highscores import lib
from highscores.models import Leaderboard, Score


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, lib.WRONG_VERSION_MESSAGE),
        ("v21.2z", lib.WRONG_VERSION_MESSAGE),
        ("v21.3d", lib.WRONG_VERSION_MESSAGE),
        ("v21.3e", None),
        ("21.3e", None),
        ("v21.3f", None),
        ("v21.10a", None),
        ("v22.0a", None),
        ("v21.3e_p1", lib.PRERELEASE_MESSAGE),
        ("invalid", lib.ERROR_CORRUPT_CODE_MESSAGE),
    ],
)
def test_high_score_client_version(version, expected):
    score = Score(client_version=version, leaderboard=Leaderboard(auto_or_teleop="TELE"))

    assert lib.check_generic_game_settings(score, "TELE") == expected


def test_changing_minimum_client_version(monkeypatch):
    monkeypatch.setattr(lib, "MINIMUM_CLIENT_VERSION", "21.10b")
    score = Score(client_version="v21.10a", leaderboard=Leaderboard(auto_or_teleop="TELE"))

    assert lib.check_generic_game_settings(score, "TELE") == lib.WRONG_VERSION_MESSAGE

    score.client_version = "v21.10b"
    assert lib.check_generic_game_settings(score, "TELE") is None

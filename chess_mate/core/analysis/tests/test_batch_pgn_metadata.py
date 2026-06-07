from core.analysis.batch_pgn_metadata import extract_platform_metadata_from_pgn


def test_extract_lichess_url_from_site_header():
    pgn = (
        '[Event "Rated rapid"]\n'
        '[Site "https://lichess.org/AbCdEfGh"]\n'
        '[Date "2026.05.01"]\n'
        '[White "alice"]\n'
        '[Black "bob"]\n'
        '[Result "1-0"]\n\n1. e4 e5 1-0'
    )
    meta = extract_platform_metadata_from_pgn(pgn)
    assert meta["platform_game_url"] == "https://lichess.org/AbCdEfGh"
    assert meta["platform"] == "lichess"
    assert meta["date_played"] == "2026-05-01"


def test_extract_chesscom_url_from_link_header():
    pgn = (
        '[Event "Live Chess"]\n'
        '[Site "Chess.com"]\n'
        '[Link "https://www.chess.com/game/live/123456789"]\n'
        '[Date "2026.05.02"]\n'
        '[White "alice"]\n'
        '[Black "bob"]\n'
        '[Result "0-1"]\n\n1. d4 d5 0-1'
    )
    meta = extract_platform_metadata_from_pgn(pgn)
    assert meta["platform_game_url"] == "https://www.chess.com/game/live/123456789"
    assert meta["platform"] == "chess.com"

import pytest
from unittest.mock import patch, MagicMock
from core.tasks import analyze_game_task, analyze_batch_games_task
from core.models import Game

@pytest.fixture
def game():
    return Game.objects.create(
        pgn='[Event "Rated Game"]\n[Site "https://lichess.org"]\n[White "Player1"]\n[Black "Player2"]\n[Result "1-0"]\n\n1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.O-O Be7 6.d3 d6 7.c3 O-O 8.Re1 Nb8 9.Nbd2 Nbd7 10.Nf1 c6 11.Bc2 Qc7 12.Ng3 Re8 13.d4 Bf8 14.Nh4 g6 15.f4 Bg7 16.f5 Nf8 17.Rf1 Bd7 18.Bg5 Qd8 19.Qd2 Qb6 20.Rf2 Ng4 21.Rf3 exd4 22.cxd4 Bxd4+ 23.Kh1 Ne5 24.Rb3 Qc5 25.Rxb7 Rab8 26.Rxb8 Rxb8 27.Rb1 Rxb2 28.Rxb2 Bxb2 29.Bf6 Qc4 30.Bb3 Qd3 31.Qh6 Qb1+ 32.Nf1 Qxf1# 1-0',
        user_id=1,
        platform='lichess',
        game_id='12345',
        result='1-0'
    )

@patch('core.tasks.analyze_game_task')
def test_analyze_game_task(game, mock_analyze_game_task):
    mock_analyze_game_task.return_value = {
        'status': 'success',
        'analysis': {},
        'feedback': {},
        'opening_name': 'Ruy Lopez'
    }
    result = analyze_game_task(game.id)
    assert result['status'] == 'success'
    assert 'analysis' in result
    assert 'feedback' in result

@patch('core.tasks.analyze_batch_games_task')
def test_analyze_batch_games_task(game, mock_analyze_batch_games_task):
    mock_analyze_batch_games_task.return_value = [{
        'status': 'success',
        'analysis': {},
        'feedback': {},
        'opening_name': 'Ruy Lopez'
    }]
    result = analyze_batch_games_task([game.id])
    assert len(result) == 1
    assert result[0]['status'] == 'success'
    assert 'analysis' in result[0]
    assert 'feedback' in result[0] 
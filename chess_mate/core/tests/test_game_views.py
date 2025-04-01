"""
Tests for game views.
"""

import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from ..models import Game, Profile
from .. import game_views
from .. import constants

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user():
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )
    Profile.objects.create(
        user=user,
        email_verified=True,
        credits=10
    )
    return user

@pytest.fixture
def authenticated_client(api_client, test_user):
    url = reverse('login')
    data = {
        'email': 'test@example.com',
        'password': 'testpassword123'
    }
    response = api_client.post(url, data, format='json')
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client

@pytest.fixture
def test_game(test_user):
    return Game.objects.create(
        user=test_user,
        platform='chess.com',
        white='testuser',
        black='opponent',
        result='win',
        pgn='[Event "Test Game"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
        raw_game_data={},
        opening_name='Ruy Lopez',
        analysis_status='completed'
    )

@pytest.mark.django_db
class TestGameViews:
    def test_user_games_view(self, authenticated_client, test_user, test_game):
        url = reverse('user_games')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['platform'] == 'chess.com'
        assert response.data[0]['white'] == 'testuser'
        assert response.data[0]['black'] == 'opponent'
    
    @patch('chess_mate.core.chess_services.ChessComService.get_user_games')
    def test_fetch_games_chess_com(self, mock_get_games, authenticated_client, test_user):
        # Mock the chess.com service
        mock_get_games.return_value = [
            {
                'white': {'username': 'testuser'},
                'black': {'username': 'opponent1'},
                'pgn': '[Event "Test Game 1"]\n1. e4 e5',
                'time_control': 'rapid',
                'end_time': 1610000000,
                'result': '1-0'
            },
            {
                'white': {'username': 'opponent2'},
                'black': {'username': 'testuser'},
                'pgn': '[Event "Test Game 2"]\n1. d4 d5',
                'time_control': 'rapid',
                'end_time': 1610010000,
                'result': '0-1'
            }
        ]
        
        # Create mock save_game function
        with patch('chess_mate.core.chess_services.save_game') as mock_save_game:
            # Make save_game return a game with ID
            def side_effect(user, platform, data):
                game = Game(id=len(mock_save_game.mock_calls))
                return game
            mock_save_game.side_effect = side_effect
            
            url = reverse('fetch_games')
            data = {
                'platform': 'chess.com',
                'username': 'testuser',
                'game_type': 'rapid',
                'num_games': 5
            }
            
            response = authenticated_client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_200_OK
            assert mock_get_games.called
            assert mock_get_games.call_args[0][0] == 'testuser'
            assert mock_get_games.call_args[0][1] == 'rapid'
            assert mock_get_games.call_args[0][2] == 5
            assert mock_save_game.call_count == 2
            assert response.data['saved_games'] == [0, 1]
            
            # Check if credits were deducted
            profile = Profile.objects.get(user=test_user)
            assert profile.credits == 9  # Started with 10
    
    @patch('chess_mate.core.chess_services.LichessService.get_user_games')
    def test_fetch_games_lichess(self, mock_get_games, authenticated_client, test_user):
        # Mock the lichess service
        mock_get_games.return_value = [
            {
                'players': {
                    'white': {'user': {'name': 'testuser'}},
                    'black': {'user': {'name': 'opponent1'}}
                },
                'pgn': '[Event "Test Game 1"]\n1. e4 e5',
                'speed': 'rapid',
                'createdAt': 1610000000,
                'winner': 'white'
            }
        ]
        
        # Create mock save_game function
        with patch('chess_mate.core.chess_services.save_game') as mock_save_game:
            # Make save_game return a game with ID
            def side_effect(user, platform, data):
                game = Game(id=len(mock_save_game.mock_calls))
                return game
            mock_save_game.side_effect = side_effect
            
            url = reverse('fetch_games')
            data = {
                'platform': 'lichess',
                'username': 'testuser',
                'game_type': 'rapid',
                'num_games': 5
            }
            
            response = authenticated_client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_200_OK
            assert mock_get_games.called
            assert mock_get_games.call_args[0][0] == 'testuser'
            assert mock_get_games.call_args[0][1] == 'rapid'
            assert mock_get_games.call_args[0][2] == 5
            assert mock_save_game.call_count == 1
            assert response.data['saved_games'] == [0]
            
            # Check if credits were deducted
            profile = Profile.objects.get(user=test_user)
            assert profile.credits == 9  # Started with 10
    
    def test_analyze_game(self, authenticated_client, test_user, test_game):
        # Set game to unanalyzed first
        test_game.analysis_status = 'not_analyzed'
        test_game.save()
        
        # Create a mock for the celery task and task manager
        with patch('chess_mate.core.tasks.analyze_game_task.delay') as mock_task:
            mock_task.return_value = MagicMock(id='mock-task-id')
            
            with patch.object(game_views.task_manager, 'register_task') as mock_register:
                url = reverse('analyze_game', kwargs={'game_id': test_game.id})
                response = authenticated_client.post(url)
                
                assert response.status_code == status.HTTP_202_ACCEPTED
                assert mock_task.called
                assert mock_task.call_args[0][0] == test_game.id
                assert mock_register.called
                assert mock_register.call_args[0][0] == 'mock-task-id'
                assert mock_register.call_args[0][1] == test_game.id
                assert mock_register.call_args[0][2] == test_user.id
                
                # Check if credits were deducted
                profile = Profile.objects.get(user=test_user)
                assert profile.credits == 9  # Started with 10
                
                # Check if game status was updated
                test_game.refresh_from_db()
                assert test_game.analysis_status == 'analyzing'
    
    def test_get_game_analysis(self, authenticated_client, test_user, test_game):
        # Set up a game with analysis data
        test_game.analysis_status = 'analyzed'
        test_game.analysis = {
            'analysis_results': {
                'summary': {
                    'user_accuracy': 85.5
                },
                'moves': [
                    {'move': 'e4', 'evaluation': 0.2}
                ]
            }
        }
        test_game.save()
        
        url = reverse('get_game_analysis', kwargs={'game_id': test_game.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'analysis_data' in response.data
        assert response.data['analysis_data']['analysis_results']['summary']['user_accuracy'] == 85.5
    
    def test_check_analysis_status(self, authenticated_client, test_user):
        # Mock the task manager and AsyncResult
        task_id = 'mock-task-id'
        game_id = 123
        
        with patch.object(game_views.task_manager, 'get_task_info') as mock_get_task_info:
            mock_get_task_info.return_value = {
                'user_id': test_user.id,
                'game_id': game_id,
                'progress': 50
            }
            
            with patch('chess_mate.core.game_views.AsyncResult') as mock_async_result:
                mock_result = MagicMock()
                mock_result.state = 'PROGRESS'
                mock_async_result.return_value = mock_result
                
                url = reverse('check_analysis_status', kwargs={'task_id': task_id})
                response = authenticated_client.get(url)
                
                assert response.status_code == status.HTTP_200_OK
                assert response.data['status'] == 'IN_PROGRESS'
                assert response.data['progress'] == 50
    
    def test_batch_analyze(self, authenticated_client, test_user):
        # Create two test games
        game1 = Game.objects.create(
            user=test_user,
            platform='chess.com',
            white='testuser',
            black='opponent1',
            pgn='[Event "Test Game 1"]\n1. e4 e5',
            analysis_status='not_analyzed'
        )
        
        game2 = Game.objects.create(
            user=test_user,
            platform='chess.com',
            white='opponent2',
            black='testuser',
            pgn='[Event "Test Game 2"]\n1. d4 d5',
            analysis_status='not_analyzed'
        )
        
        # Create mocks for the task and task manager
        with patch('chess_mate.core.tasks.analyze_batch_games_task.delay') as mock_task:
            mock_task.return_value = MagicMock(id='mock-batch-task-id')
            
            with patch.object(game_views.task_manager, 'register_batch_task') as mock_register:
                url = reverse('batch_analyze')
                data = {
                    'game_ids': [game1.id, game2.id]
                }
                
                response = authenticated_client.post(url, data, format='json')
                
                assert response.status_code == status.HTTP_202_ACCEPTED
                assert mock_task.called
                assert sorted(mock_task.call_args[0][0]) == sorted([game1.id, game2.id])
                assert mock_register.called
                assert mock_register.call_args[0][0] == 'mock-batch-task-id'
                assert sorted(mock_register.call_args[0][1]) == sorted([game1.id, game2.id])
                assert mock_register.call_args[0][2] == test_user.id
                
                # Check if credits were deducted (2 games = 2 credits)
                profile = Profile.objects.get(user=test_user)
                assert profile.credits == 8  # Started with 10
                
                # Check if game statuses were updated
                game1.refresh_from_db()
                game2.refresh_from_db()
                assert game1.analysis_status == 'analyzing'
                assert game2.analysis_status == 'analyzing'
    
    def test_check_batch_analysis_status(self, authenticated_client, test_user):
        # Mock the task manager and AsyncResult
        task_id = 'mock-batch-task-id'
        game_ids = [101, 102]
        
        with patch.object(game_views.task_manager, 'get_task_info') as mock_get_task_info:
            mock_get_task_info.return_value = {
                'user_id': test_user.id,
                'game_ids': game_ids,
                'progress': 75
            }
            
            with patch('chess_mate.core.game_views.AsyncResult') as mock_async_result:
                mock_result = MagicMock()
                mock_result.state = 'PROGRESS'
                mock_async_result.return_value = mock_result
                
                url = reverse('check_batch_analysis_status', kwargs={'task_id': task_id})
                response = authenticated_client.get(url)
                
                assert response.status_code == status.HTTP_200_OK
                assert response.data['status'] == 'IN_PROGRESS'
                assert response.data['progress'] == 75
    
    def test_generate_ai_feedback(self, authenticated_client, test_user, test_game):
        # Set up a game with analysis data
        test_game.analysis_status = 'analyzed'
        test_game.analysis = {
            'analysis_results': {
                'summary': {
                    'user_accuracy': 85.5
                },
                'moves': [
                    {'move': 'e4', 'evaluation': 0.2}
                ]
            }
        }
        test_game.save()
        
        # Mock the feedback generator
        with patch.object(game_views.AIFeedbackGenerator, 'generate_feedback') as mock_generate:
            mock_generate.return_value = "This is AI feedback for your game."
            
            url = reverse('generate_ai_feedback', kwargs={'game_id': test_game.id})
            response = authenticated_client.post(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert mock_generate.called
            assert 'feedback' in response.data
            assert response.data['feedback']['content'] == "This is AI feedback for your game."
            
            # Check if credits were deducted (feedback costs 2)
            profile = Profile.objects.get(user=test_user)
            assert profile.credits == 8  # Started with 10
            
            # Check if feedback was saved to the game
            test_game.refresh_from_db()
            assert 'feedback' in test_game.analysis
            assert test_game.analysis['feedback']['content'] == "This is AI feedback for your game." 
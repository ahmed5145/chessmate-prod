"""
Tests for dashboard views.
"""

import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import timedelta

from ..models import Game, Profile, GameAnalysis
from .. import dashboard_views

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
        credits=10,
        chess_com_username='testuser',
        lichess_username='testuser_lichess',
        elo_rating=1500,
        analysis_count=5
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
def sample_games(test_user):
    # Create a mix of games with different results and platforms
    games = []
    
    # Win as white on chess.com
    games.append(Game.objects.create(
        user=test_user,
        platform='chess.com',
        white='testuser',
        black='opponent1',
        result='win',
        pgn='[Event "Test Game 1"]\n1. e4 e5',
        opening_name='King\'s Pawn',
        date_played=timezone.now() - timedelta(days=10),
        analysis_status='analyzed',
        analysis={
            'analysis_results': {
                'summary': {
                    'user_accuracy': 85.5
                },
                'mistakes': [
                    {'type': 'blunder', 'move_number': 5, 'piece': 'queen'},
                    {'type': 'missed_tactic', 'move_number': 8, 'piece': 'knight'}
                ]
            }
        }
    ))
    
    # Loss as black on chess.com
    games.append(Game.objects.create(
        user=test_user,
        platform='chess.com',
        white='opponent2',
        black='testuser',
        result='loss',
        pgn='[Event "Test Game 2"]\n1. d4 d5',
        opening_name='Queen\'s Pawn',
        date_played=timezone.now() - timedelta(days=5),
        analysis_status='analyzed',
        analysis={
            'analysis_results': {
                'summary': {
                    'user_accuracy': 78.2
                },
                'mistakes': [
                    {'type': 'inaccuracy', 'move_number': 12, 'piece': 'bishop'},
                    {'type': 'missed_tactic', 'move_number': 15, 'piece': 'rook'},
                    {'type': 'blunder', 'move_number': 32, 'piece': 'king'}
                ]
            }
        }
    ))
    
    # Draw as white on lichess
    games.append(Game.objects.create(
        user=test_user,
        platform='lichess',
        white='testuser_lichess',
        black='opponent3',
        result='draw',
        pgn='[Event "Test Game 3"]\n1. Nf3 Nf6',
        opening_name='Reti Opening',
        date_played=timezone.now() - timedelta(days=2),
        analysis_status='analyzed',
        analysis={
            'analysis_results': {
                'summary': {
                    'user_accuracy': 90.1
                },
                'mistakes': [
                    {'type': 'inaccuracy', 'move_number': 20, 'piece': 'pawn'}
                ]
            }
        }
    ))
    
    # Recent game not analyzed yet
    games.append(Game.objects.create(
        user=test_user,
        platform='lichess',
        white='opponent4',
        black='testuser_lichess',
        result='win',
        pgn='[Event "Test Game 4"]\n1. c4 e5',
        opening_name='English Opening',
        date_played=timezone.now() - timedelta(hours=12),
        analysis_status='not_analyzed'
    ))
    
    # Older game for trend analysis
    games.append(Game.objects.create(
        user=test_user,
        platform='chess.com',
        white='testuser',
        black='opponent5',
        result='win',
        pgn='[Event "Test Game 5"]\n1. e4 c5',
        opening_name='Sicilian Defense',
        date_played=timezone.now() - timedelta(days=40),
        analysis_status='analyzed',
        analysis={
            'analysis_results': {
                'summary': {
                    'user_accuracy': 75.8
                },
                'mistakes': [
                    {'type': 'blunder', 'move_number': 7, 'piece': 'queen'},
                    {'type': 'missed_checkmate', 'move_number': 25, 'piece': 'rook'}
                ]
            }
        }
    ))
    
    return games

@pytest.mark.django_db
class TestDashboardViews:
    def test_dashboard_view_cache_miss(self, authenticated_client, test_user, sample_games):
        # Mock the cache to always miss
        with patch.object(dashboard_views.cache_manager, 'get', return_value=None):
            with patch.object(dashboard_views.cache_manager, 'set') as mock_set:
                url = reverse('dashboard')
                response = authenticated_client.get(url)
                
                assert response.status_code == status.HTTP_200_OK
                
                # Check user data
                assert response.data['user']['username'] == 'testuser'
                assert response.data['user']['chess_com_username'] == 'testuser'
                assert response.data['user']['lichess_username'] == 'testuser_lichess'
                
                # Check game stats
                assert response.data['game_stats']['total_games'] == 5
                assert response.data['game_stats']['analyzed_games'] == 4
                
                # Check performance stats
                assert response.data['performance']['overall']['win_count'] == 2
                assert response.data['performance']['overall']['loss_count'] == 1
                assert response.data['performance']['overall']['draw_count'] == 1
                
                # Check openings data exists
                assert 'openings' in response.data
                
                # Check insights data exists
                assert 'insights' in response.data
                
                # Verify cache was set
                assert mock_set.called
    
    def test_dashboard_view_cache_hit(self, authenticated_client, test_user):
        # Mock cached data
        mock_data = {
            'user': {
                'username': 'testuser',
                'credits': 10
            },
            'game_stats': {
                'total_games': 5
            }
        }
        
        # Mock the cache to return data
        with patch.object(dashboard_views.cache_manager, 'get', return_value=mock_data):
            url = reverse('dashboard')
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data == mock_data
    
    def test_refresh_dashboard(self, authenticated_client, test_user):
        # Mock the cache to delete
        with patch.object(dashboard_views.cache_manager, 'delete') as mock_delete:
            url = reverse('refresh_dashboard')
            response = authenticated_client.post(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert 'message' in response.data
            assert mock_delete.called
    
    def test_get_performance_trend_cache_miss(self, authenticated_client, test_user, sample_games):
        # Mock the cache to always miss
        with patch.object(dashboard_views.cache_manager, 'get', return_value=None):
            with patch.object(dashboard_views.cache_manager, 'set') as mock_set:
                url = reverse('get_performance_trend')
                response = authenticated_client.get(url)
                
                assert response.status_code == status.HTTP_200_OK
                
                # Check that we have trend data points
                assert len(response.data) > 0
                
                # Check trend data structure
                trend_point = response.data[0]
                assert 'game_id' in trend_point
                assert 'date' in trend_point
                assert 'accuracy' in trend_point
                assert 'result' in trend_point
                assert 'avg_accuracy' in trend_point
                
                # Verify cache was set
                assert mock_set.called
    
    def test_get_performance_trend_cache_hit(self, authenticated_client, test_user):
        # Mock cached data
        mock_data = [
            {
                'game_id': 1,
                'date': '2023-01-01T12:00:00Z',
                'accuracy': 85.5,
                'result': 'win'
            }
        ]
        
        # Mock the cache to return data
        with patch.object(dashboard_views.cache_manager, 'get', return_value=mock_data):
            url = reverse('get_performance_trend')
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data == mock_data
    
    def test_get_mistake_analysis_cache_miss(self, authenticated_client, test_user, sample_games):
        # Mock the cache to always miss
        with patch.object(dashboard_views.cache_manager, 'get', return_value=None):
            with patch.object(dashboard_views.cache_manager, 'set') as mock_set:
                url = reverse('get_mistake_analysis')
                response = authenticated_client.get(url)
                
                assert response.status_code == status.HTTP_200_OK
                
                # Check mistake data structure
                assert 'total_mistakes' in response.data
                assert 'by_type' in response.data
                assert 'by_game_phase' in response.data
                assert 'by_piece' in response.data
                
                # Check specific mistake types
                mistake_types = [item['type'] for item in response.data['by_type']]
                assert 'blunder' in mistake_types
                assert 'missed_tactic' in mistake_types
                
                # Check game phases
                assert 'opening' in response.data['by_game_phase']
                assert 'middlegame' in response.data['by_game_phase']
                assert 'endgame' in response.data['by_game_phase']
                
                # Check pieces
                assert 'queen' in response.data['by_piece']
                assert 'king' in response.data['by_piece']
                
                # Verify cache was set
                assert mock_set.called
    
    def test_get_mistake_analysis_cache_hit(self, authenticated_client, test_user):
        # Mock cached data
        mock_data = {
            'total_mistakes': 6,
            'by_type': [
                {'type': 'blunder', 'count': 3, 'percentage': 50.0}
            ],
            'by_game_phase': {
                'opening': 33.3,
                'middlegame': 50.0,
                'endgame': 16.7
            },
            'by_piece': {
                'queen': 33.3,
                'king': 16.7,
                'rook': 33.3,
                'bishop': 16.7,
                'knight': 0,
                'pawn': 0
            }
        }
        
        # Mock the cache to return data
        with patch.object(dashboard_views.cache_manager, 'get', return_value=mock_data):
            url = reverse('get_mistake_analysis')
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.data == mock_data
    
    def test_no_analyzed_games(self, authenticated_client, test_user):
        # Delete all games
        Game.objects.all().delete()
        
        # Mock the cache to always miss
        with patch.object(dashboard_views.cache_manager, 'get', return_value=None):
            url = reverse('get_mistake_analysis')
            response = authenticated_client.get(url)
            
            assert response.status_code == status.HTTP_200_OK
            assert 'message' in response.data
            assert 'No analyzed games found' in response.data['message'] 
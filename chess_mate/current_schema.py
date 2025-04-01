# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class CorePlayer(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=100)
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'core_player'


class CoreProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    credits = models.IntegerField()
    bullet_rating = models.IntegerField()
    blitz_rating = models.IntegerField()
    rapid_rating = models.IntegerField()
    classical_rating = models.IntegerField()
    email_verified = models.BooleanField()
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    preferences = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    chesscom_username = models.CharField(max_length=100, blank=True, null=True)
    lichess_username = models.CharField(max_length=100, blank=True, null=True)
    rating_history = models.JSONField()
    user = models.OneToOneField(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'core_profile'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class GameAnalysis(models.Model):
    id = models.BigAutoField(primary_key=True)
    metrics = models.JSONField()
    phase_metrics = models.JSONField()
    time_metrics = models.JSONField()
    tactical_metrics = models.JSONField()
    positional_metrics = models.JSONField()
    feedback = models.JSONField()
    time_control_feedback = models.JSONField()
    study_plan = models.JSONField()
    cache_key = models.CharField(unique=True, max_length=100)
    analysis_metadata = models.JSONField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    game_id = models.BigIntegerField(unique=True)

    class Meta:
        managed = False
        db_table = 'game_analysis'


class Games(models.Model):
    platform = models.CharField(max_length=20, blank=True, null=True)
    game_id = models.CharField(max_length=100, blank=True, null=True)
    pgn = models.TextField(blank=True, null=True)
    result = models.CharField(max_length=10, blank=True, null=True)
    white = models.CharField(max_length=100, blank=True, null=True)
    black = models.CharField(max_length=100, blank=True, null=True)
    opponent = models.CharField(max_length=100, blank=True, null=True)
    opening_name = models.CharField(max_length=200, blank=True, null=True)
    date_played = models.DateTimeField(blank=True, null=True)
    time_control = models.CharField(max_length=50, blank=True, null=True)
    time_control_type = models.CharField(max_length=20, blank=True, null=True)
    eco_code = models.CharField(max_length=3, blank=True, null=True)
    opening_played = models.CharField(max_length=200, blank=True, null=True)
    opening_variation = models.CharField(max_length=200, blank=True, null=True)
    opponent_opening = models.CharField(max_length=200, blank=True, null=True)
    analysis_version = models.IntegerField(blank=True, null=True)
    last_analysis_date = models.DateTimeField(blank=True, null=True)
    analysis_status = models.CharField(max_length=20, blank=True, null=True)
    analysis_priority = models.IntegerField(blank=True, null=True)
    analysis = models.JSONField(blank=True, null=True)
    feedback = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    analysis_completed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'games'


class TokenBlacklistBlacklistedtoken(models.Model):
    id = models.BigAutoField(primary_key=True)
    blacklisted_at = models.DateTimeField()
    token = models.OneToOneField('TokenBlacklistOutstandingtoken', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'token_blacklist_blacklistedtoken'


class TokenBlacklistOutstandingtoken(models.Model):
    id = models.BigAutoField(primary_key=True)
    token = models.TextField()
    created_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    user = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)
    jti = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'token_blacklist_outstandingtoken'


class Transactions(models.Model):
    id = models.BigAutoField(primary_key=True)
    transaction_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    credits = models.IntegerField()
    status = models.CharField(max_length=20)
    stripe_payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'transactions'

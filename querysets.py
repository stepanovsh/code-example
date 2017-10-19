# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.timezone import now
from django.db.models import Max, Case, When, IntegerField, QuerySet
from django.db.models import Sum, F


class UserQueryset(QuerySet):

    def with_max_game_points(self, game_type, from_datetime, until_datetime=None):
        users = self.annotate(statistic_value=Max(
            Case(
                When(user_statistic__stat_type=game_type,
                     user_statistic__created__gte=from_datetime,
                     user_statistic__created__lte=until_datetime or now(),
                     then=F('user_statistic__points')),
                default=0,
                output_field=IntegerField()
            )))
        users = users.filter(statistic_value__gt=0).order_by('-statistic_value')
        return users

    def with_most_points_scored(self, game_type, from_datetime, until_datetime=None):
        users = self.annotate(statistic_value=Sum(
            Case(
                When(user_statistic__stat_type=game_type,
                     user_statistic__created__gte=from_datetime,
                     user_statistic__created__lte=until_datetime or now(),
                     then=F('user_statistic__points')),
                default=0,
                output_field=IntegerField()
            )))
        users = users.filter(statistic_value__gt=0).order_by('-statistic_value')
        return users
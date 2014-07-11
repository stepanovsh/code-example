from __future__ import unicode_literals
from itertools import izip, tee
from random import random, randint

from django.db import models


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


class BannerManager(models.Manager):

    def get_banner(self, place):
        qs = self.get_query_set().filter(checked=True, left__gt=0, is_show=True)
        qs = qs.select_related('product', 'banner__product__place')

        if place == 'header':
            qs = qs.filter(product__place__slug=place)
        elif place == 'column':
            qs = qs.filter(product__place__slug=place)
        count = len(qs)
        if count == 0:
            from banner.models import Banner
            try:
                return Banner.objects.filter(
                    product__place__slug=place, is_default=True).select_related('product__place').order_by('?')[0]
            except IndexError:
                return None

        show_ratios = sorted(list(set([order.show_ratio for order in qs])), reverse=True)
        random_index = randint(0, count - 1)

        if len(show_ratios) == 1:
            order = qs[random_index]
            return order.banner

        show_chances = [0.0] + [float(ratio) / sum(show_ratios) for ratio in show_ratios]
        show_intervals = [chance1 + chance2 for chance1, chance2 in pairwise(show_chances)]
        rand = random()

        for i, end in enumerate(show_intervals):
            if rand < end:
                lookup_qs = [ad for ad in qs if ad.show_ratio == show_ratios[i]]
                count = len(lookup_qs)
                random_index = randint(0, count - 1)
                order = lookup_qs[random_index]
                break
        return order.banner

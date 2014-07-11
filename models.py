from __future__ import unicode_literals
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now

from caching.base import CachingMixin

from model_utils.models import TimeStampedModel
from skd_tools.decorators import cache_func
from distribution.models import ServiceTemplate
from balance.models import TransactionLog


class AdsServiceProduct(CachingMixin, models.Model):
    name = models.CharField(_('service name'), max_length=200)
    code = models.CharField(_('service code'), max_length=5)
    price = models.DecimalField(_('price of service'), max_digits=10, decimal_places=2)
    first_package_price = models.DecimalField(_('first package price'), max_digits=10, decimal_places=2, blank=True, null=True)
    second_package_price = models.DecimalField(_('second package price'), max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(_('service description'), max_length=200)

    @property
    def get_ten_price(self):
        return self.price * 10

    @property
    def get_fifty_price(self):
        return self.price * 50

    @property
    def get_three_price(self):
        return self.price * 3

    @property
    def get_six_price(self):
        return self.price * 6

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('service product')
        verbose_name_plural = _('service product')


class ServiceManager(models.Manager):
    PERFORMER_ON_MAIN = 8

    # @cache_func('performer_main', method=True)
    def get_permormer_tape(self):
        service = AdsServiceProduct.objects.get(code='aitmp')
        performer_order = self.filter(service=service).order_by('-created').select_related(
            'user__photo', 'user__firstname', 'user__is_pro')
        performer_order = performer_order.extra(select={'status': 'SELECT "users_customuserstatus"."status" '
                                                        'FROM "users_customuserstatus" WHERE "users_customuserstatus"."user_id" '
                                                        '= "ads_adsserviceorder"."user_id" '})

        if performer_order:
            performer_tape = list(performer_order)
            if len(performer_tape) > self.PERFORMER_ON_MAIN:
                return reversed(performer_tape[0:8])
            elif len(performer_tape) < self.PERFORMER_ON_MAIN:
                append_performer_count = self.PERFORMER_ON_MAIN - len(performer_tape)
                for i in range(0, append_performer_count):
                    performer_tape.append(None)
                return reversed(performer_tape)
            else:
                return reversed(performer_tape)
        else:
            return [None for i in range(0, 8)]

    # @cache_func('performer_article', method=True)
    def get_article_tape(self):
        service = AdsServiceProduct.objects.get(code='atart')
        performer_order = self.filter(service=service).order_by('-created').select_related('user')
        performer_order = performer_order.extra(select={'status': 'SELECT "users_customuserstatus"."status" '
                                                        'FROM "users_customuserstatus" WHERE "users_customuserstatus"."user_id" '
                                                        '= "ads_adsserviceorder"."user_id" '})

        if performer_order:
            performer_tape = list()
            for performer in performer_order:
                performer_tape.append(performer)

            if len(performer_tape) > self.PERFORMER_ON_MAIN:
                return performer_tape[0:8]
            elif len(performer_tape) < self.PERFORMER_ON_MAIN:
                append_performer_count = self.PERFORMER_ON_MAIN - len(performer_tape)
                for i in range(0, append_performer_count):
                    performer_tape.append(None)
                return performer_tape
            else:
                return performer_tape
        else:
            return [None for i in range(0, 8)]


class AdsServiceOrder(models.Model):
    ONE_MONTH, THREE_MONTH, SIX_MONTH = range(1, 4, 1)
    ONE_ITEM = 1
    TEN_ITEM = 10
    FIFTY_ITEM = 50

    ADS_MONTH_CHOICES = (
        (ONE_MONTH, _('1 month')),
        (THREE_MONTH, _('3 month')),
        (SIX_MONTH, _('6 month')),
    )
    ADS_ITEM_CHOICES = (
        (ONE_ITEM, _('1 item')),
        (TEN_ITEM, _('10 items')),
        (FIFTY_ITEM, _('50 items')),
    )
    TYPE_TRANSACTION = (
        (1, _('payment'),),
        (2, _('repayment'),),
        (3, _('add admin'),),
    )

    objects = ServiceManager()

    service = models.ForeignKey(AdsServiceProduct, verbose_name=_('product'))
    user = models.ForeignKey('users.CustomUser', verbose_name=_('user'), related_name='adsserviceorders')
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    prolongate = models.BooleanField(_('automatic prolongation'), default=False)
    type_transaction = models.PositiveSmallIntegerField(_('type transaction'), default=1)
    period = models.PositiveSmallIntegerField(_('period'), choices=ADS_MONTH_CHOICES, default=0)
    num_item = models.PositiveSmallIntegerField(_('item'), choices=ADS_ITEM_CHOICES, default=0)

    class Meta:
        verbose_name = _('service order')
        verbose_name_plural = _('service order')

    @property
    def price_order(self):
        if self.period:
            if self.period == self.ONE_MONTH:
                price = self.service.price
            elif self.period == self.THREE_MONTH:
                price = self.service.first_package_price
            elif self.period == self.SIX_MONTH:
                price = self.service.second_package_price
        elif self.num_item and self.service.code != 'distr':
            if self.num_item == self.ONE_ITEM:
                price = self.service.price
            elif self.num_item == self.TEN_ITEM:
                price = self.service.first_package_price
            elif self.num_item == self.FIFTY_ITEM:
                price = self.service.second_package_price
        elif self.num_item and self.service.code == 'distr':
            price = self.service.price * self.num_item
        else:
            price = self.service.price
        return price

    @property
    def debit_funds(self):
        self.user.balance -= self.price_order
        self.user.save()

    def prolongate_order(self):
        if self.price_order < self.user.balance:
            self.user.balance -= self.price_order
            self.user.save()
            self.save()
            return True
        return False

    def __unicode__(self):
        return u'{}: {}'.format(self.created, self.user)


class DistributionManager(models.Manager):

    def wait_moderation(self):
        return self.filter(status=1).count()


class Distribution(TimeStampedModel):
    MODERATION, SEND, DENIED = range(1, 4)
    STATUS_CHOICES = (
        (MODERATION, _('Moderation'),),
        (SEND, _('Sent'),),
        (DENIED, _('Denied'),),
    )

    user = models.ForeignKey('users.CustomUser', verbose_name=_('user'), related_name='distributions')
    order = models.ForeignKey(AdsServiceOrder, verbose_name=_('order'), related_name='distributions', blank=True, null=True)
    message = models.TextField(_('text'), max_length=1000)
    country = models.ForeignKey('transports.Country', verbose_name=_('country'), blank=True, null=True)
    city = models.ForeignKey('transports.City', verbose_name=_('city'), blank=True, null=True)
    specialization = models.ManyToManyField('service.Specialization', verbose_name=_('specialization'), blank=True, null=True)
    is_pro_only = models.BooleanField(_('is pro only'), default=False)
    status = models.PositiveSmallIntegerField(_('status'), choices=STATUS_CHOICES, default=MODERATION)
    is_checked = models.BooleanField(_('is checked'), default=False)

    objects = DistributionManager()

    class Meta:
        verbose_name = _('distribution')
        verbose_name_plural = _('distribution')

    def __unicode__(self):
        return u'{}: {}'.format(self.user, self.message)

    @property
    def can_moderation(self):
        if self.status == self.DENIED:
            return True
        return False


def order_change_balance(sender, created, instance, **kwargs):
    if created:
        if sender == AdsServiceOrder:
            change = instance.price_order
            if instance.type_transaction == 2:
                log_type = TransactionLog.REPAYMENT
                if instance.user.mail_notifications.get().balance_change:
                    template = ServiceTemplate.objects.get(key='balance_change')
                    change_url = reverse_lazy('profile:mailing')
                    instance.user.send_service_notification(template, {'site': settings.DOMAIN,
                                                                       'user': instance.user,
                                                                       'change': change,
                                                                       'date': now(),
                                                                       'change_url': change_url})
            elif instance.type_transaction == 3:
                log_type = TransactionLog.ADMIN_SERVICE
            else:
                log_type = TransactionLog.PRODUCT

            TransactionLog.objects.create(
                user=instance.user, product=instance.service, change=change, log_type=log_type)

models.signals.post_save.connect(order_change_balance, sender=AdsServiceOrder)

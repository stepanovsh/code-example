# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.apps import apps
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError

from ordered_model.models import OrderedModelBase
from model_utils.models import TimeStampedModel
from model_utils.choices import Choices


class Notification(TimeStampedModel):
    NOTIFICATION_TYPE_CHOICES = Choices(
        (1, 'EVENT1', _('Event 1'),),
        (2, 'EVENT2', _('Event 2'),),
        (3, 'EVENT3', _('Event 3'),),
    )
    NOTIFICATION_MESSAGE_MAPPING = {
        NOTIFICATION_TYPE_CHOICES.EVENT1: {
            'message': _('Event 1 message'),
            'should_save': True,
            'extra_info': False
        },
        NOTIFICATION_TYPE_CHOICES.EVENT2: {
            'message': _('Event 2 message'),
            'should_save': True,
            'extra_info': False
        },
        NOTIFICATION_TYPE_CHOICES.EVENT3: {
            'message': _('Event 3 message'),
            'should_save': False,
            'extra_info': True
        },

    }
    message = models.TextField(_('Message'), max_length=255)
    extra_data = JSONField(_('External data'), blank=True, null=True)
    is_read = models.BooleanField(_('Is read'), default=False)
    user = models.ForeignKey('user.User', verbose_name=_('user'),
                                 related_name='user_notifications')
    notification_type = models.PositiveSmallIntegerField(_('Notification Type'), choices=NOTIFICATION_TYPE_CHOICES,
                                                         null=True)

    class Meta:
        db_table = 'Notification'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ('-created',)

    def __str__(self):
        return '{} - {}'.format(self.user.display_name, self.get_notification_type_display())

    @classmethod
    def get_unread_count(cls, user):
        return cls.objects.filter(user=user, is_read=False).count()

    @classmethod
    def prepare_notification(cls, user, notification_type, message=None, extra_data=None, format_params=None):
        notification_obj = cls(
            user=user,
            notification_type=notification_type,
        )
        if message is not None:
            notification_obj.message = message
        else:
            message = cls.NOTIFICATION_MESSAGE_MAPPING[notification_type]['message']
            if cls.NOTIFICATION_MESSAGE_MAPPING[notification_type]['extra_info'] and format_params is not None:
                message = message.format(*format_params)
            notification_obj.message = message

        if extra_data is not None:
            notification_obj.extra_data = extra_data

        if cls.NOTIFICATION_MESSAGE_MAPPING[notification_type].get('should_save', False):
            notification_obj.save()
        if settings.USE_AWS_SNS and notification_obj.user.can_receive_notifications:
            notification_obj.send_message()

        return notification_obj

    def send_message(self):
        body = {
            'aps': {
                'alert': self.message,
                'badge': self.get_unread_count(self.user),
                'sound': 'default'
            },
            'custom': {
                'notification_type': self.notification_type,
                'extra_data': self.extra_data if self.extra_data else {}
            }
        }
        if self.id:
            body['custom']['notification_id'] =  self.id
        devices = DeviceModel.objects.filter(user=self.user)
        for device in devices:
            send_push.delay(device.arn, body, True)


class Banner(OrderedModelBase):
    """
    Onboarding Banner Model
    """

    BANNER_SCREEN_CHOICES = Choices(
        (1, 'SCREE1', _('Screen1'),),
        (2, 'SCREE2', _('Screen2'),),
        (3, 'SCREE3', _('Screen3'),),
    )

    BANNER_SCREEN_CHOICES_NEED_ID = {
        BANNER_SCREEN_CHOICES.SCREE1: {
            'external_info': False
        },
        BANNER_SCREEN_CHOICES.SCREE2: {
            'external_info': True,
            'app_path': 'application',
            'model_name': 'Model1',
            'serializer_path': 'application.serializers.Serializer1',
        },
        BANNER_SCREEN_CHOICES.SCREE3: {
            'external_info': True,
            'app_path': 'application',
            'model_name': 'Model2',
            'serializer_path': 'application.serializers.Serializer2',
        },
    }

    image = models.ImageField(_('Image'), upload_to=photo_directory_path)
    is_shown = models.BooleanField(_('is Show'), default=True)
    screen = models.PositiveSmallIntegerField(_('Screen'), choices=BANNER_SCREEN_CHOICES, null=True, blank=True)
    external_id = models.BigIntegerField(_('External object id'), null=True, blank=True)
    ordering = models.PositiveIntegerField(editable=False, db_index=True)
    order_field_name = 'ordering'

    class Meta:
        verbose_name = _('Banner')
        verbose_name_plural = _('Banners')
        ordering = ('ordering',)

    def get_image_url(self, request=None):
        if request is None or settings.USE_AWS_S3_FOR_MEDIA:
            return self.image.url
        return request.build_absolute_uri(self.image.url)

    def clean(self):
        if self.screen and self.BANNER_SCREEN_CHOICES_NEED_ID[self.screen]['external_info']:
            external_model = apps.get_model(
                self.BANNER_SCREEN_CHOICES_NEED_ID[self.screen]['app_path'],
                self.BANNER_SCREEN_CHOICES_NEED_ID[self.screen]['model_name']
            )
            try:
                external_model.objects.get(id=self.external_id)
            except external_model.DoesNotExist:
                raise ValidationError({
                    'external_id': _('Object does not exist')
                })
        if (not self.screen and self.external_id) or \
                (self.screen and self.BANNER_SCREEN_CHOICES_NEED_ID[self.screen]['external_info'] is False and
                     self.external_id):
            raise ValidationError({
                'external_id': _('Please select correct screen')
            })

    def get_serializer(self):
        path = self.BANNER_SCREEN_CHOICES_NEED_ID[self.screen]['serializer_path']
        path = path.split('.')
        if len(path) != 4:
            return None
        el = __import__(path[0])
        path_index = 1
        while path_index < 4 and hasattr(el, path[path_index]):
            el = getattr(el, path[path_index], None)
            path_index += 1
        return el
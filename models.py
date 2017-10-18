# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField

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

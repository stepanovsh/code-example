# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.db.models.signals import post_save


Notification = apps.get_model('notification', 'Notification')
Transaction = apps.get_model('payment', 'Transaction')


def post_save_charge(sender, instance, created, **kwargs):

    if not instance.status == sender.STATUS_CHOICES.SUCCESSFUL:
        return

    if instance.paid and not instance.balance_refilled:
        current_balance = instance.customer.user.balance
        instance.customer.user.balance = current_balance + instance.amount

        instance.customer.user.save(update_fields=['balance'])

        instance.balance_refilled = True
        instance.save(update_fields=['balance_refilled'])

        Transaction.create_transaction_from_instance(instance=instance)

        Notification.prepare_notification(
            instance.customer.user,
            Notification.NOTIFICATION_TYPE_CHOICES.TRANSFER_RECEIVED,
            format_params=(instance.amount,)
        )


post_save.connect(post_save_charge, sender='payment.PayPalCharge')
post_save.connect(post_save_charge, sender='payment.StripeCharge')
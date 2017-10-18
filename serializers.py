# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from rest_framework import serializers
from phonenumber_field.phonenumber import to_python

User = get_user_model()

UserProfile = apps.get_model('profile', 'UserProfile')


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    birth_date = serializers.DateField(required=False)
    sex = serializers.IntegerField(required=False)
    photo = serializers.FileField(required=False)
    can_receive_notifications = serializers.BooleanField(required=False)
    phone_number = serializers.CharField(required=False)

    user_fields = ['first_name', 'last_name', 'birth_date', 'sex', 'photo', 'can_receive_notifications']
    user_profile_fields = ['nickname', 'province', 'bio', 'phone_number', 'education',
                           'specialization', 'specialization_details']
    disabled_field = ['first_name', 'last_name']

    class Meta:
        model = UserProfile
        fields = (
            'first_name', 'last_name', 'nickname', 'birth_date', 'sex', 'photo',
            'province', 'specialization', 'specialization_details', 'bio', 'education',
            'phone_number', 'can_receive_notifications')

    def validate_phone_number(self, value):

        phone_number = to_python(value)
        if phone_number and not phone_number.is_valid():
            raise serializers.ValidationError(_('Please check your phone number'))
        return value

    def validate_birth_date(self, value):
        if value is None or value >= now().date():
            raise serializers.ValidationError(_('Please enter valid birth date'))
        return value

    def validate_sex(self, value):
        if value is None or value not in [k[0] for k in User.SEX_CHOICES]:
            raise serializers.ValidationError(_('Invalid choices'))
        return value

    def update(self, instance, validated_data):
        user = instance.user
        for k, v in validated_data.items():
            if k in self.user_profile_fields:
                if k == 'specialization':
                    instance.specialization_id = v
                elif k == 'province':
                    instance.province_id = v
                else:
                    setattr(instance, k, v)
            if k in self.user_fields:
                setattr(user, k, v)
        user.save()
        instance.save()
        return instance

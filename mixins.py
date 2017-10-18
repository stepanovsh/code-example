# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework.serializers import Serializer


class SerializerContextMixin:

    def get_serializer_context(self):
        return {
            'request': self.request
        }


class RequiredFieldsSerializerMixin(Serializer):
    required_fields = None

    def get_fields(self):
        fields = super(RequiredFieldsSerializerMixin, self).get_fields()
        if self.required_fields is None:
            return fields
        for key, field in fields.items():
            if key in self.required_fields:
                field.required = True
            else:
                field.required = False
        return fields

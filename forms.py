from __future__ import unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _
from service.models import Specialization
from users.models import CustomUser
from ads.models import AdsServiceOrder, Distribution


class RaisingApplicationForm(forms.Form):
    CHOICE_LIST = (
        (1, 'goods'),
        (2, 'transport'),
        (3, 'service'),)
    CHOICE_USE = (
        (1, 'use'),
        (2, 'buy'),)
    waybill = forms.IntegerField(min_value=1, widget=forms.HiddenInput())
    w_type = forms.ChoiceField(choices=CHOICE_LIST, widget=forms.HiddenInput())
    u_type = forms.ChoiceField(choices=CHOICE_USE, widget=forms.HiddenInput())


class PackageByForm(forms.Form):
    code = forms.CharField(max_length=5)
    num_item = forms.ChoiceField(choices=AdsServiceOrder.ADS_ITEM_CHOICES)


class DistributionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(DistributionForm, self).__init__(*args, **kwargs)

        self.fields.insert(1, 'countries', forms.CharField(required=False))
        self.fields.insert(1, 'cities', forms.CharField(required=False))

        if kwargs.get('instance', None):
            if self.instance.country:
                self.initial['countries'] = self.instance.country.country
            if self.instance.city:
                self.initial['cities'] = self.instance.city.city

    class Meta:
        model = Distribution

        widgets = {
            'specialization': forms.CheckboxSelectMultiple(),
            'message': forms.Textarea(
                attrs={
                    'cols': '20',
                    'rows': '4',
                    'class': 'required',
                    'maxlength': '1000'
                }
            ),
            'is_pro_only': forms.CheckboxInput(attrs={'class': 'customCheckbox'}),
        }
        exclude = [
            'user',
            'order',
            'status'
        ]


class DistributionCalculateForm(forms.Form):
    CHOICE_LIST = ()
    for spec in Specialization.objects.filter(is_enabled=True):
        CHOICE_LIST += ((spec.pk, spec.name,),)

    specialization = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple(), choices=CHOICE_LIST)
    country = forms.IntegerField(required=False)
    city = forms.IntegerField(required=False)
    is_pro_only = forms.BooleanField(required=False)


class ServiceAddAdminForm(forms.Form):
    MAIN, ARTICLE, RAISE, PICK, FIX, PAID = [i for i in range(0, 6)]
    SERVICE_ADMIN = (
        (MAIN, _('Placing on the main page'),),
        (ARTICLE, _('Placing on the article page'),),
        (RAISE, _('Raising applications'),),
        (PICK, _('Dividing applications'),),
        (FIX, _('Fix applications'),),
        (PAID, _('Paid applications')))

    ids = forms.TypedMultipleChoiceField(coerce=int)
    ads_type = forms.ChoiceField(choices=SERVICE_ADMIN)

    def __init__(self, *args, **kwargs):
        super(ServiceAddAdminForm, self).__init__(*args, **kwargs)
        user_id_list = CustomUser.objects.all().values_list('id', flat=True)
        self.fields['ids'].choices = ((uid, uid) for uid in user_id_list)


class PackageServiceAddAdminForm(forms.Form):
    ids = forms.TypedMultipleChoiceField(coerce=int)
    ads_type = forms.IntegerField(widget=forms.HiddenInput)
    num_item = forms.ChoiceField(choices=AdsServiceOrder.ADS_ITEM_CHOICES, widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super(PackageServiceAddAdminForm, self).__init__(*args, **kwargs)
        user_id_list = CustomUser.objects.all().values_list('id', flat=True)
        self.fields['ids'].choices = ((uid, uid) for uid in user_id_list)


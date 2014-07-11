from __future__ import unicode_literals
from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from .models import AdsServiceProduct, AdsServiceOrder, Distribution
from users.models import CustomUser
from message.models import Message, Conversation
from users.utils import ExcludeDeleteActionMixin, ReadOnlyAdminMixin
from distribution.models import ServiceTemplate
from distribution.tasks import SendMailTask


class DistributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_checked', 'status_display')
    list_filter = ('status',)
    search_fields = ('user__email', 'user__first_name')
    actions = ('make_distribution_checked', 'send_message')

    def queryset(self, request):
        return super(DistributionAdmin, self).queryset(request).select_related('user')

    def status_display(self, obj):
        return mark_safe('<span alt="{}">{}</span>'.format(obj.status, obj.get_status_display()))
    status_display.allowed_tags = True
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'status'

    def make_distribution_checked(self, request, queryset):
        queryset.update(is_checked=True, status=Distribution.SEND)
        service_template = ServiceTemplate.objects.get(key='distribution_moderation')

        for q in queryset:
            if q.user.mail_notifications.get().aprove:
                change_url = reverse_lazy('profile:mailing')
                c = {'site': settings.DOMAIN,
                     'user': q.user,
                     'action': _('successfully passed'),
                     'change_url': change_url}
                SendMailTask().delay(recipients=[q.user.email], context=c,
                                     subject=service_template.subject, body=service_template)
            spec_id = [c.id for c in q.specialization.all()]
            filter_dict = {
                'specialization__in': spec_id,
                'country': q.country,
                'city': q.city,
                'is_pro': q.is_pro_only,
            }
            filters = {}
            for key in filter_dict:
                if filter_dict[key]:
                    filters[key] = filter_dict[key]
            users = CustomUser.objects.filter(**filters)
            users = users.filter(date_joined__lte=q.created)
            users = users.filter(is_active=True).exclude(Q(is_staff=True) | Q(is_superuser=True) | Q(id=q.user.id))
            title = _('<p>With distribution send <a href="{}">{}</a></p>').format(q.user.get_absolute_url(), q.user.first_name)
            text = q.message + title
            for user in users:
                try:
                    conversation = Conversation.objects.get(
                        Q(user1=user, user2=request.user) | Q(user1=request.user, user2=user))
                except Conversation.DoesNotExist:
                    conversation = Conversation.objects.create(user1=request.user, user2=user)
                conversation.save()

                Message.objects.create(sender=request.user, receiver=user, text=text, conversation=conversation)
        self.message_user(request, _('With distribution confirmed. Messages send'))
    make_distribution_checked.short_description = _('Make selected distributions checked')

    def send_message(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        redirect_url = reverse('message:admin_send_distribution_message') + '?ids={}'.format(','.join(selected))
        return HttpResponseRedirect(redirect_url)
    send_message.short_description = _('Refuse delivery')


class ServiceProductAdmin(ExcludeDeleteActionMixin, admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'first_package_price', 'second_package_price', 'description')
    list_editable = ('price', 'first_package_price', 'second_package_price',)
    readonly_fields = ('code',)

    def has_add_permission(self, request):
        return False


class ServiceOrderAdmin(ExcludeDeleteActionMixin, ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('created', 'user', 'service', 'price_order', 'num_item')
    search_fields = ('user__email',)
    list_filter = ('service',)
    date_hierarchy = 'created'

admin.site.register(AdsServiceProduct, ServiceProductAdmin)
admin.site.register(AdsServiceOrder, ServiceOrderAdmin)
admin.site.register(Distribution, DistributionAdmin)

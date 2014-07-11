# Create your views here.
from __future__ import unicode_literals
import calendar
from django.views.generic import FormView, TemplateView
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages as django_messages
from django.http import HttpResponseRedirect
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.db.models import Max, Min, Sum

from skd_tools.mixins import ActiveTabMixin
from skd_tools.decorators import cache_func
from robokassa.forms import RobokassaForm
from constance import config

from users.utils import LoginRequiredMixin, JSONResponseMixin
from users.models import CustomUser
from distribution.models import ServiceTemplate
from .forms import PaymentForm, AdminFillUpForm
from .models import Transaction, TransactionLog


class BalanceView(ActiveTabMixin, JSONResponseMixin, LoginRequiredMixin, FormView):
    template_name = "balance/balance.html"
    form_class = PaymentForm
    active_tab = ['my_portfolio', 'balance']

    def get_context_data(self, **kwargs):
        context = super(BalanceView, self).get_context_data(**kwargs)
        context['title'] = _('Balance/Fill up your balance')
        return context

    def post(self, request, *args, **kwargs):
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_type = form.cleaned_data['payment_type']
            amount = form.cleaned_data['amount']

            order = Transaction.objects.create(user=request.user, amount=amount, payment_type=payment_type)
            form_robo = RobokassaForm(initial={'OutSum': order.amount,
                                               'InvId': order.id,
                                               'Email': self.request.user.email,
                                               'sInvDesc': config.BILLING_MESSAGE,
                                               # 'IncCurrLabel': '',
                                               'Culture': 'ru'})

            html = render_to_string('balance/ajax_form.html', {'form': form_robo})
            if self.request.is_ajax():

                return self.render_to_json_response({'status': '', 'html': html})
            else:
                raise Http404(_("Ajax only"))
        else:
            if self.request.is_ajax():
                error_list = []
                for k, v in form.errors.items():
                    error_list.append([k, v[0]])
                to_json_responce = dict()
                to_json_responce['status'] = 'error'
                to_json_responce['messages'] = error_list

                return self.render_to_json_response(to_json_responce)
            else:
                raise Http404(_("Ajax only"))


class AdminBalanceFillUp(LoginRequiredMixin, FormView):
    permission_required = 'can_access_admin_panel'
    form_class = AdminFillUpForm
    template_name = 'admin/balance/send_balance_admin.html'

    def get_initial(self):
        try:
            return {'ids': [int(uid) for uid in self.request.GET.get('ids', '').split(',') if uid]}
        except ValueError:
            raise Http404()

    def get_context_data(self, **kwargs):
        ctx = super(AdminBalanceFillUp, self).get_context_data(**kwargs)
        ctx['title'] = _('Fill up balance')
        return ctx

    def form_valid(self, form):
        user_id_set = set(form.cleaned_data['ids'])

        change = form.cleaned_data['change']

        users = CustomUser.objects.filter(id__in=user_id_set)
        for user in users:
            TransactionLog.objects.create(user=user, log_type=TransactionLog.ADMIN, change=change)
            user.balance_amount(change)
            if user.mail_notifications.get().balance_change:
                template = ServiceTemplate.objects.get(key='balance_change')
                change_url = reverse_lazy('profile:mailing')
                user.send_service_notification(template, {'site': settings.DOMAIN,
                                                          'user': user,
                                                          'change': change,
                                                          'date': now(),
                                                          'change_url': change_url})

        django_messages.success(self.request, _('{} messages were sent successfully.').format(len(user_id_set)))
        return HttpResponseRedirect(reverse('admin:users_customuser_changelist'))


class TransactionDiagramAdmin(LoginRequiredMixin, TemplateView):
    template_name = "admin/diagrams/transaction_diagram.html"

    def get_context_data(self, **kwargs):
        context = super(TransactionDiagramAdmin, self).get_context_data(**kwargs)
        context['transaction_stat'] = self.build_diagram_transaction()
        return context

    @cache_func('transaction_admin_diagram', method=True)
    def build_diagram_transaction(self):
        info = Transaction.objects.filter(status='successful').order_by('created')
        min_date, max_date = info.aggregate(Min('created'), Max('created')).values()
        info = info.filter(created__range=(min_date, max_date))
        info = info.extra({'created': 'date(created)'}).values('created', 'amount').annotate(count_sum=Sum('amount'))
        return {'data': [[float(calendar.timegm(views['created'].timetuple()) * 1000), float(views['count_sum'])] for views in info],
                'name': _('all')}

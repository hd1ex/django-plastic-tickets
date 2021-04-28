import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.views import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext
from django.contrib.auth import get_user_model
from django.db.models.functions import Lower

from . import models, forms, util


def tickets_index_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'plastic_tickets/overview.html')


@login_required
def new_ticket_view(request: HttpRequest, active_file='') -> HttpResponse:
    files = util.get_cached_filenames_for_user(request.user)

    if not active_file and len(files) > 0:
        active_file = files[0]
    else:
        active_file = util.get_cached_dir(request.user).joinpath(active_file)

    js_data = json.dumps(models.get_option_tree(),
                         default=lambda d: d.__dict__)

    configured_files = util.get_configured_filenames_for_user(request.user)

    if request.method == 'POST':
        if request.POST.get('config_form') is not None:
            if forms.cache_config(active_file, request.user, request.POST):
                configured_files.append(active_file)
                unconfigured_file = next((f for f in files
                                          if f not in configured_files), None)
                if unconfigured_file is not None:
                    return redirect('plastic_tickets_new_with_file',
                                    active_file=unconfigured_file.name)
        elif request.POST.get('file_upload') is not None:
            files = request.FILES.getlist('file[]')
            if files is not None:
                forms.cache_files(request.user, files)
                return redirect('plastic_tickets_new')
        elif request.POST.get('file_delete') is not None:
            util.delete_all_cached_files_for_user(request.user)
            return redirect('plastic_tickets_new')
        elif request.POST.get('create_ticket') is not None:
            id = forms.submit_ticket(request,
                                     request.user,
                                     request.POST.get('ticket_text', ''),
                                     request.POST.get('send_to_user') == 'on')
            return redirect('plastic_tickets_ticket', id=id)

    count = 1
    selected_pm, selected_mat_type, selected_color = "FFF/FDM", "PLA", ""
    config = models.PrintConfig.objects.filter(file=active_file,
                                               user=request.user).first()
    if config is not None:
        count = config.count
        mat = config.get_first_material()
        selected_pm = mat.type.production_method.name
        _, selected_mat_type = mat.get_disp_list_name()
        selected_color = ",".join(
            str(mat.label) for mat in config.material_stocks.all())
    return render(request, 'plastic_tickets/new_ticket.html',
                  {
                      'files': files, 'active_file': Path(active_file),
                      'count': count,
                      'selected_pm': selected_pm,
                      'selected_mat_type': selected_mat_type,
                      'selected_color': selected_color,
                      'js_data': js_data,
                      'configured_files': configured_files,
                      'fully_configured': set(configured_files) == set(files),
                  })


@login_required
def ticket_view(request: HttpRequest, id: int) -> HttpResponse:
    ticket = get_object_or_404(models.Ticket, id=id)
    config = ticket.printconfig_set.first()

    if config.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden(gettext('Access denied'))

    if request.method == 'POST':
        if not request.user.is_staff:
            return HttpResponseForbidden(gettext('Access denied'))
        if "close" in request.POST and \
           ticket.state == models.Ticket.TicketState.OPEN:
            ticket.state = models.Ticket.TicketState.DONE
            ticket.save()
        elif ("reject" in request.POST and
              ticket.state == models.Ticket.TicketState.OPEN):
            ticket.state = models.Ticket.TicketState.REJECTED
            ticket.save()
        elif ("reopen" in request.POST and
              (ticket.state == models.Ticket.TicketState.DONE or
               ticket.state == models.Ticket.TicketState.REJECTED)):
            ticket.state = models.Ticket.TicketState.OPEN
            ticket.save()
        elif "apply" in request.POST:
            new_assignee = request.POST.get("assignee")
            if new_assignee == "unassigned":
                ticket.assignee = None
                ticket.save()
            else:
                new_user = get_user_model().objects \
                                           .filter(id=new_assignee) \
                                           .first()
                if new_user is not None:
                    ticket.assignee = new_user
                    ticket.save()

    possible_assignees = None
    if request.user.is_staff:
        possible_assignees = get_user_model().objects \
                                             .filter(is_staff=True) \
                                             .order_by(Lower("username"))

    return render(request, 'plastic_tickets/ticket_view.html', context={
        'user': ticket.printconfig_set.first().user,
        'ticket': ticket,
        'ral_colors': models.ral_colors,
        'request': request,
        'possible_assignees': possible_assignees
    })


@login_required
def ticket_list_view(request: HttpRequest) -> HttpResponse:
    tickets = models.Ticket.objects.all()
    js_data = []
    for ticket in tickets:
        config = ticket.printconfig_set.first()
        if config.user == request.user or request.user.is_staff:
            assignee = ticket.assignee
            if assignee is not None:
                assignee = ticket.assignee.get_username()
            js_data.append({'id': ticket.id,
                            'state': ticket.state,
                            'assignee': assignee})
    return render(request, 'plastic_tickets/ticket_list_view.html', context={
        'request': request,
        'js_data': json.dumps(js_data),
        'ticket_states': ["UN", "PR", "DO", "RE"]
    })


@login_required
def materials_list_view(request: HttpRequest) -> HttpResponse:
    js_data = json.dumps([{
        "label": stock.label,
        "props": [str(prop) for prop in stock.material.properties.all()],
        "type": stock.material.type.name,
        "color": stock.material.get_color_name(),
        "ral": stock.material.ral_color_number,
        "amount": stock.current_weight,
        "price": 5
        } for stock in models.MaterialStock.objects.all()])
    return render(request, 'plastic_tickets/materials_list_view.html',
                  {
                      'js_data': js_data
                  })


@login_required
def file_view(request: HttpRequest, id: int, filename: str) -> HttpResponse:
    config = get_object_or_404(models.PrintConfig, ticket__id=id,
                               file__contains=filename)

    if config.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden(gettext('Access denied'))

    filename = f'{id}/{filename}'

    if settings.DEBUG:
        return redirect(f'{settings.PROTECTED_MEDIA}{filename}')

    response = HttpResponse()
    response['Content-Type'] = mimetypes.guess_type(filename)[0]
    response['X-Accel-Redirect'] = f'{settings.PROTECTED_MEDIA}{filename}'
    response['Content-Disposition'] = f'inline;filename={filename}'

    return response

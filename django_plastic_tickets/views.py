import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.views import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext

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
            id = forms.submit_ticket(request.user,
                                     request.POST.get('ticket_text', ''),
                                     request.POST.get('send_to_user') == 'on')
            return redirect('plastic_tickets_ticket', id=id)

    return render(request, 'plastic_tickets/new_ticket.html',
                  {
                      'files': files, 'active_file': Path(active_file),
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

    return render(request, 'plastic_tickets/ticket_view.html', context={
        'user': request.user,
        'ticket': ticket,
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

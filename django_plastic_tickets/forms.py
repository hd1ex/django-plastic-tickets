import shutil
from pathlib import Path
from smtplib import SMTPException
from typing import List

from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import QueryDict, HttpRequest
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext
from django.contrib import messages
from django.conf import settings

from . import models, util


def cache_config(active_file: Path, user: User, post: QueryDict):
    fc = post['file_count']
    stocks_lbl = set(int(label) for label in post['material_color'].split(","))
    if len(stocks_lbl) == 0:
        return False

    # Get DB objects for Options
    stocks = models.MaterialStock.objects.filter(label__in=stocks_lbl)
    if len(stocks_lbl) != len(stocks):
        return False

    # Check for existing cached config
    config = models.PrintConfig.objects.filter(
        file=active_file, user=user).first()

    # Update existing config or create a new one
    if config is not None:
        config.count = int(fc)
    else:
        config = models.PrintConfig(file=active_file,
                                    count=int(fc),
                                    user=user,
                                    ticket=None)
        config.save()  # need to save before the many-to-many field is set
    config.material_stocks.set(stocks, clear=True)
    config.save()
    return True


def cache_files(user: User, files: List[InMemoryUploadedFile]):
    directory = util.get_cached_dir(user)
    for file in files:
        with open(directory.joinpath(file.name), 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)


def submit_ticket(request: HttpRequest, user: User, message: str,
                  send_to_user: bool):
    ticket = models.Ticket(message=message)
    ticket.save()

    configs = models.PrintConfig.objects.filter(user=user, ticket=None)

    ticket_dir = util.FILES_DIR.joinpath(str(ticket.id))
    ticket_dir.mkdir(parents=True)
    for config in configs:
        config.file = shutil.move(config.file, ticket_dir)
        config.ticket = ticket
        config.save()

    util.get_cached_dir(user).rmdir()

    cur_language = translation.get_language()
    try:
        translation.activate('en')
        mail_text = render_to_string('plastic_tickets/ticket_mail.txt',
                                     context={
                                         'user': user,
                                         'message': message,
                                         'configs': configs,
                                         'ticket': ticket
                                     })
    finally:
        translation.activate(cur_language)

    subject = f'Ticket number {ticket.id}'

    try:
        util.send_email(subject, mail_text,
                        user.email if send_to_user else None,
                        user.email)
        messages.add_message(request, messages.INFO,
                             gettext('Email sent successfully.'),
                             'alert alert-success')
    except SMTPException:
        messages.add_message(
            request, messages.ERROR,
            gettext('Email-transport failed. Please email %(rec)s manually '
                    'and mention your ticket id. Sorry for the inconvenience!'
                    ) % {'rec': ', '.join(settings.TICKET_RECIPIENTS)},
            'alert alert-danger')

    return ticket.id

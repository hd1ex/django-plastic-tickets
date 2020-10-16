import shutil
from pathlib import Path
from typing import List

from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import QueryDict
from django.template.loader import render_to_string
from django.utils import translation

from . import models, util


def cache_config(active_file: Path, user: User, post: QueryDict):
    fc = post['file_count']
    pm = post['production_method']
    mt = post['material_type']
    mc = post['material_color']

    # Get DB objects for Options
    material_type = models.MaterialType.objects.filter(
        name__iexact=mt, production_method__name__iexact=pm).first()
    color = models.MaterialColor.objects.filter(name__iexact=mc).first()
    if material_type is None or color is None:
        return False
    # Check for existing cached config
    config = models.PrintConfig.objects.filter(
        file=active_file, user=user).first()

    # Update existing config and return
    if config is not None:
        config.count = int(fc)
        config.material_type = material_type
        config.color = color
        config.save()
        return True

    # Create new (cached) config
    config = models.PrintConfig(file=active_file,
                                count=int(fc),
                                material_type=material_type,
                                color=color,
                                user=user,
                                ticket=None
                                )
    config.save()
    return True


def cache_files(user: User, files: List[InMemoryUploadedFile]):
    directory = util.get_cached_dir(user)
    for file in files:
        with open(directory.joinpath(file.name), 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)


def submit_ticket(user: User, message: str, send_to_user: bool):
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

    util.send_email(subject, mail_text, user.email if send_to_user else None,
                    user.email)

    return ticket.id

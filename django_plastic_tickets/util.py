import shutil
import textwrap
from pathlib import Path
from typing import List, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail

from . import models

FILES_DIR = Path('files/')


def get_cached_dir(user: User) -> Path:
    return Path('cached_files/', user.username)


def get_cached_filenames_for_user(user: User) -> List[Path]:
    cached_dir = get_cached_dir(user)
    cached_dir.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []
    for file in cached_dir.glob('*'):
        files.append(file)

    return files


def get_configured_filenames_for_user(user: User) -> List[Path]:
    return [Path(c.file) for c in
            models.PrintConfig.objects.filter(user=user, ticket=None).all()]


def delete_all_cached_files_for_user(user: User):
    shutil.rmtree(get_cached_dir(user))
    models.PrintConfig.objects.filter(user=user, ticket=None).delete()


def flow_text(text: str) -> str:
    """
    This method applies format=flowed (RFC 3676) to a non-wrapped text.

    Note that there is no paragraph or quote detection.
    Existing new lines are preserved.
    See https://joeclark.org/ffaq.html for a quick description of f=f.

    :param text: is the non flowed text
    :return: flowed text according to RFC 3676
    """
    result = ''

    for line in text.splitlines():
        result += ' \r\n'.join(textwrap.wrap(line, 77))
        result += '\r\n'

    return result


def send_email(subject: str, message: str, cc: Optional[str], reply_to: str):
    if cc is not None:
        cc = [cc]

    message = flow_text(message)

    with mail.get_connection() as connection:
        msg = mail.EmailMessage(
            subject, message, '', settings.TICKET_RECIPIENTS, cc=cc,
            connection=connection,
            headers={'Reply-To': reply_to}
        )

        msg.content_subtype = 'plain; format=flowed'

        msg.send()

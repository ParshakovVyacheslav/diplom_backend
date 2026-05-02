"""Смена email: выпуск подписанного токена и применение после подтверждения по ссылке."""

from __future__ import annotations

import logging
from typing import TypedDict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.core import signing
from django.db import transaction
from django.urls import reverse
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)

SALT_EMAIL_CHANGE = 'accounts.email-change.v1'


class EmailChangePayload(TypedDict):
    user_id: int
    email: str


def max_age_seconds() -> int | None:
    val = getattr(
        settings, 'EMAIL_CHANGE_CONFIRM_MAX_AGE_SECONDS', 3 * 24 * 60 * 60
    )
    if val is None:
        return None
    return int(val)


def normalize_email(email: str) -> str:
    return BaseUserManager.normalize_email((email or '').strip())


def issue_email_change_token(user_id: int, normalized_email: str) -> str:
    return signing.dumps(
        {'user_id': user_id, 'email': normalized_email},
        salt=SALT_EMAIL_CHANGE,
    )


def parse_email_change_token(token: str) -> EmailChangePayload:
    kwargs = {'salt': SALT_EMAIL_CHANGE}
    mx = max_age_seconds()
    if mx is not None:
        kwargs['max_age'] = mx
    data = signing.loads(token, **kwargs)
    if not isinstance(data, dict) or 'user_id' not in data or 'email' not in data:
        raise signing.BadSignature('invalid payload shape')
    return {'user_id': int(data['user_id']), 'email': str(data['email'])}


def resolve_confirm_link(request, raw_token: str) -> str:
    template = (getattr(settings, 'EMAIL_CHANGE_CONFIRM_URL_TEMPLATE', '') or '').strip()
    quoted = quote(raw_token, safe='')
    if template:
        return template.format(token=quoted, quoted_token=quoted)
    path = reverse('api-profile-email-change-confirm')
    base = request.build_absolute_uri(path)
    return f'{base}?{urlencode({"token": raw_token})}'


def send_email_change_confirmation(*, to_email: str, confirm_url: str) -> None:
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string

    subject = getattr(
        settings, 'EMAIL_CHANGE_MAIL_SUBJECT', 'Подтверждение новой почты'
    )
    ctx = {
        'site_name': getattr(settings, 'SITE_NAME', 'RICE'),
        'confirm_url': confirm_url,
    }
    plain = render_to_string('email/email_change.txt', ctx)
    html = render_to_string('email/email_change.html', ctx)
    msg = EmailMultiAlternatives(
        subject,
        plain,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
    )
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)


@transaction.atomic
def apply_pending_email_change_from_token(raw_token: str) -> str:
    """Подтвердить pending_email пользователя из подписанного токена. Вернёт финальный email."""
    payload = parse_email_change_token(raw_token.strip())
    wanted = normalize_email(payload['email'])
    Model = get_user_model()
    user = Model.objects.select_for_update().get(pk=payload['user_id'])

    pending = normalize_email(user.pending_email or '')
    if not pending or pending != wanted:
        logger.warning(
            'Email change reject: stale token or mismatch uid=%s', user.pk
        )
        raise ValueError('TOKEN_MISMATCH')

    if Model.objects.exclude(pk=user.pk).filter(email__iexact=wanted).exists():
        raise ValueError('EMAIL_TAKEN')

    user.email = wanted
    user.pending_email = ''
    user.save(update_fields=('email', 'pending_email'))
    return user.email

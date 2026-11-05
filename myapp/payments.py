import base64
import json
import uuid
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class PayPalError(Exception):
    pass


def _paypal_request(path, method='GET', payload=None, request_id=None):
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        raise PayPalError('PayPal checkout is not configured.')

    environments = {
        'sandbox': 'https://api-m.sandbox.paypal.com',
        'live': 'https://api-m.paypal.com',
    }
    api_base = environments.get(settings.PAYPAL_ENVIRONMENT)
    if api_base is None:
        raise PayPalError('The PayPal environment must be sandbox or live.')

    credentials = f'{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}'.encode()
    token_request = Request(
        f'{api_base}/v1/oauth2/token',
        data=b'grant_type=client_credentials',
        headers={
            'Authorization': f'Basic {base64.b64encode(credentials).decode()}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )
    try:
        with urlopen(token_request, timeout=15) as response:
            access_token = json.loads(response.read())['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        if request_id:
            headers['PayPal-Request-Id'] = request_id
        request = Request(
            f'{api_base}{path}',
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
            method=method,
        )
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, OSError) as error:
        raise PayPalError('PayPal could not complete the request.') from error


def create_paypal_order(total, name, email, items):
    customer_names = name.split(maxsplit=1)
    payer_name = {'given_name': customer_names[0]}
    if len(customer_names) > 1:
        payer_name['surname'] = customer_names[1]
    return _paypal_request(
        '/v2/checkout/orders',
        method='POST',
        request_id=str(uuid.uuid4()),
        payload={
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': 'USD',
                    'value': f'{total:.2f}',
                    'breakdown': {
                        'item_total': {
                            'currency_code': 'USD',
                            'value': f'{total:.2f}',
                        },
                    },
                },
                'description': 'Forma Studio collection',
                'items': items,
            }],
            'payer': {
                'name': payer_name,
                'email_address': email,
            },
            'payment_source': {
                'paypal': {
                    'experience_context': {
                        'brand_name': 'Forma Studio',
                        'user_action': 'PAY_NOW',
                        'shipping_preference': 'GET_FROM_FILE',
                    },
                },
            },
        },
    )


def capture_paypal_order(order_id):
    return _paypal_request(
        f'/v2/checkout/orders/{order_id}/capture',
        method='POST',
        request_id=str(uuid.uuid4()),
        payload={},
    )


def captured_amount(response):
    if not isinstance(response, dict):
        return None
    purchase_units = response.get('purchase_units', [])
    captures = purchase_units[0].get('payments', {}).get('captures', []) if purchase_units else []
    if not captures or captures[0].get('status') != 'COMPLETED':
        return None

    amount = captures[0].get('amount', {})
    if amount.get('currency_code') != 'USD':
        return None
    try:
        return Decimal(amount['value'])
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return None

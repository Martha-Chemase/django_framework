import json
import logging
import re
import smtplib
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.mail import BadHeaderError, EmailMessage
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from myapp.forms import CheckoutDetailsForm, ContactForm
from myapp.payments import PayPalError, capture_paypal_order, captured_amount, create_paypal_order


logger = logging.getLogger(__name__)

PRODUCTS = [
    {
        'id': 'studio-blazer',
        'name': 'The City Leather Jacket',
        'price': 148,
        'category': 'clothing',
        'category_label': 'Clothing',
        'image': 'images/baner_image01.jpg',
        'image_alt': 'A relaxed black leather look, styled for the city',
        'tag': 'Bestseller',
    },
    {
        'id': 'everyday-edit',
        'name': 'The Everyday Edit',
        'price': 128,
        'category': 'clothing',
        'category_label': 'Clothing',
        'image': 'images/baner_image02.jpg',
        'image_alt': 'A confident dark denim look from the new collection',
        'tag': 'New in',
    },
    {
        'id': 'weekend-layer',
        'name': 'The Weekend Layer',
        'price': 116,
        'category': 'clothing',
        'category_label': 'Clothing',
        'image': 'images/cat_item02.jpg',
        'image_alt': 'A soft, versatile black layer for weekends',
        'tag': '',
    },
    {
        'id': 'statement-cap',
        'name': 'The Statement Cap',
        'price': 58,
        'category': 'accessories',
        'category_label': 'Accessories',
        'image': 'images/insta_item06.jpg',
        'image_alt': 'A bright cap adds a playful finish to a look',
        'tag': 'Just landed',
    },
    {
        'id': 'soft-focus-scarf',
        'name': 'The Everyday Carryall',
        'price': 72,
        'category': 'accessories',
        'category_label': 'Accessories',
        'image': 'images/cat_item03.jpg',
        'image_alt': 'A roomy carryall styled as an everyday companion',
        'tag': '',
    },
]


def home(request):
    return render(request, 'home.html', {'featured_products': PRODUCTS[:4]})


def about(request):
    return render(request, 'about.html')


def product(request):
    return render(request, 'products.html', {'products': PRODUCTS})


def contact(request):
    form = ContactForm(request.POST or None)
    sent = False

    if request.method == 'POST' and form.is_valid():
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        message = form.cleaned_data['request']
        try:
            email_message = EmailMessage(
                subject=f'Website message from {name}',
                body=f'From: {name} <{email}>\n\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_EMAIL],
                reply_to=[email],
            )
            sent_count = email_message.send(fail_silently=False)
            if sent_count != 1:
                raise OSError('The contact email could not be delivered.')
            sent = True
            form = ContactForm()
        except (BadHeaderError, OSError, smtplib.SMTPException):
            logger.exception('Could not send the Forma Studio contact form email.')
            form.add_error(None, 'Your message could not be sent right now. Please try again or email us directly.')

    return render(request, 'contact.html', {'form': form, 'sent': sent})


def journal(request):
    return render(request, 'journal.html')


def faqs(request):
    return render(request, 'faqs.html')


def checkout(request):
    return render(request, 'checkout.html', {
        'form': CheckoutDetailsForm(),
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'products': PRODUCTS,
    })


@require_POST
def create_checkout_order(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'The checkout details are invalid.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'The checkout details are invalid.'}, status=400)

    details_form = CheckoutDetailsForm(payload)
    if not details_form.is_valid():
        return JsonResponse({'errors': details_form.errors}, status=400)

    items = payload.get('items')
    if not isinstance(items, list) or not items or len(items) > len(PRODUCTS):
        return JsonResponse({'error': 'Your bag is empty or contains invalid items.'}, status=400)

    products_by_id = {product['id']: product for product in PRODUCTS}
    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            return JsonResponse({'error': 'Your bag contains an invalid item.'}, status=400)
        product_id = item.get('id')
        quantity = item.get('quantity')
        if (
            not isinstance(product_id, str)
            or product_id not in products_by_id
            or isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or not 1 <= quantity <= 99
            or product_id in quantities
        ):
            return JsonResponse({'error': 'Your bag contains an invalid item.'}, status=400)
        quantities[product_id] = quantity

    total = sum(
        (Decimal(products_by_id[product_id]['price']) * quantity for product_id, quantity in quantities.items()),
        Decimal('0.00'),
    )
    paypal_items = [{
        'name': products_by_id[product_id]['name'],
        'sku': product_id,
        'quantity': str(quantity),
        'unit_amount': {
            'currency_code': 'USD',
            'value': f"{Decimal(products_by_id[product_id]['price']):.2f}",
        },
    } for product_id, quantity in quantities.items()]
    try:
        order = create_paypal_order(
            total,
            details_form.cleaned_data['name'],
            details_form.cleaned_data['email'],
            paypal_items,
        )
    except PayPalError:
        logger.exception('Could not create a PayPal checkout order.')
        return JsonResponse(
            {'error': 'PayPal is unavailable right now. Please try again later.'},
            status=503,
        )

    order_id = order.get('id') if isinstance(order, dict) else None
    if not isinstance(order_id, str) or not order_id:
        logger.error('PayPal returned an order without an ID.')
        return JsonResponse({'error': 'PayPal could not start your payment. Please try again.'}, status=502)

    checkout_orders = request.session.get('paypal_checkout_orders', {})
    checkout_orders[order_id] = {'total': f'{total:.2f}'}
    request.session['paypal_checkout_orders'] = checkout_orders
    return JsonResponse({'orderID': order_id})


@require_POST
def capture_checkout_order(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'The payment details are invalid.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'The payment details are invalid.'}, status=400)

    order_id = payload.get('orderID')
    if not isinstance(order_id, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,64}', order_id):
        return JsonResponse({'error': 'The PayPal order is invalid.'}, status=400)

    expected_order = request.session.get('paypal_checkout_orders', {}).get(order_id)
    if not isinstance(expected_order, dict):
        return JsonResponse({'error': 'This checkout has expired. Please start again.'}, status=400)
    try:
        expected_total = Decimal(expected_order['total'])
    except (KeyError, TypeError, InvalidOperation):
        logger.error('PayPal order %s has an invalid expected total in the session.', order_id)
        return JsonResponse({'error': 'The payment could not be verified. Please contact us.'}, status=400)

    try:
        capture = capture_paypal_order(order_id)
    except PayPalError:
        logger.exception('Could not capture PayPal order %s.', order_id)
        return JsonResponse(
            {'error': 'PayPal could not complete your payment. Please try again.'},
            status=502,
        )

    amount = captured_amount(capture)
    if not isinstance(capture, dict) or capture.get('status') != 'COMPLETED' or amount != expected_total:
        logger.error('PayPal order %s completed with an unexpected status or amount.', order_id)
        return JsonResponse(
            {'error': 'The payment could not be verified. Please contact us before trying again.'},
            status=400,
        )

    checkout_orders = request.session['paypal_checkout_orders']
    del checkout_orders[order_id]
    request.session['paypal_checkout_orders'] = checkout_orders
    return JsonResponse({'status': 'COMPLETED', 'amount': f'{amount:.2f}'})

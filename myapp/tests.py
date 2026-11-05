import json
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from myapp.payments import create_paypal_order


class StorefrontPageTests(TestCase):
    def test_homepage_shows_featured_products_and_store_navigation(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Good things.')
        self.assertContains(response, 'The City Leather Jacket')
        self.assertContains(response, 'Shop all')
        self.assertContains(response, 'data-cart-open')
        self.assertContains(response, 'data-carousel')
        self.assertContains(response, 'data-film-player')
        self.assertNotContains(response, 'data-film-download')
        self.assertNotContains(response, 'data-film-toggle')
        self.assertNotContains(response, 'data-carousel-toggle')
        self.assertContains(response, 'Journal')

    def test_product_catalog_shows_products_and_filter_controls(self):
        response = self.client.get('/products/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Forma collection')
        self.assertContains(response, 'The Statement Cap')
        self.assertContains(response, 'data-product-search')
        self.assertContains(response, 'data-filter="accessories"')
        self.assertEqual(len(response.context['products']), 5)

    def test_category_links_preserve_existing_routes(self):
        self.assertEqual(self.client.get('/about/').status_code, 200)
        self.assertEqual(self.client.get('/contact/').status_code, 200)

    def test_journal_and_faq_pages_show_helpful_content(self):
        journal_response = self.client.get('/journal/')
        self.assertEqual(journal_response.status_code, 200)
        self.assertContains(journal_response, 'A little more')
        self.assertContains(journal_response, 'post-large-image1.jpg')

        faq_response = self.client.get('/faqs/')
        self.assertEqual(faq_response.status_code, 200)
        self.assertContains(faq_response, 'When will my order ship?')
        self.assertContains(faq_response, 'Can I return or exchange a piece?')

    def test_contact_form_sends_message_and_reports_success(self):
        response = self.client.post('/contact/', {
            'name': 'Alex Example',
            'email': 'alex@example.com',
            'request': 'I have a question about my order.',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your note has been sent to our team.')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['hello@formastudio.com'])
        self.assertEqual(mail.outbox[0].reply_to, ['alex@example.com'])
        self.assertIn('I have a question about my order.', mail.outbox[0].body)

    def test_contact_form_validates_required_fields(self):
        response = self.client.post('/contact/', {'name': '', 'email': 'not-an-email', 'request': ''})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertContains(response, 'Enter a valid email address.')
        self.assertEqual(len(mail.outbox), 0)

    def test_checkout_shows_paypal_payment_and_customer_details(self):
        response = self.client.get('/checkout/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full name')
        self.assertContains(response, 'Email address')
        self.assertContains(response, 'Secure payment')
        self.assertContains(response, 'PayPal checkout is not connected yet.')
        self.assertNotContains(response, 'name="card_number"')

    @override_settings(PAYPAL_CLIENT_ID='public-client-id')
    def test_checkout_loads_paypal_sdk_without_exposing_server_secret(self):
        response = self.client.get('/checkout/')

        self.assertContains(response, 'https://www.paypal.com/sdk/js?client-id=public-client-id')
        self.assertNotContains(response, 'PAYPAL_CLIENT_SECRET')

    @override_settings(PAYPAL_CLIENT_ID='client-id', PAYPAL_CLIENT_SECRET='client-secret')
    @patch('myapp.views.create_paypal_order', return_value={'id': 'ORDER-123'})
    def test_paypal_order_uses_server_catalog_prices(self, create_order):
        response = self.client.post(
            '/checkout/create-order/',
            data=json.dumps({
                'name': 'Alex Example',
                'email': 'alex@example.com',
                'items': [{'id': 'everyday-edit', 'quantity': 2, 'price': 0.01}],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'orderID': 'ORDER-123'})
        create_order.assert_called_once_with(
            Decimal('256.00'),
            'Alex Example',
            'alex@example.com',
            [{
                'name': 'The Everyday Edit',
                'sku': 'everyday-edit',
                'quantity': '2',
                'unit_amount': {'currency_code': 'USD', 'value': '128.00'},
            }],
        )

    @patch('myapp.payments._paypal_request', return_value={'id': 'ORDER-123'})
    def test_paypal_order_uses_secure_provider_and_server_amount(self, paypal_request):
        items = [{
            'name': 'The Everyday Edit',
            'sku': 'everyday-edit',
            'quantity': '1',
            'unit_amount': {'currency_code': 'USD', 'value': '128.00'},
        }]
        create_paypal_order(Decimal('128.00'), 'Alex Example', 'alex@example.com', items)

        payload = paypal_request.call_args.kwargs['payload']
        self.assertEqual(payload['purchase_units'][0]['amount'], {
            'currency_code': 'USD',
            'value': '128.00',
            'breakdown': {'item_total': {'currency_code': 'USD', 'value': '128.00'}},
        })
        self.assertEqual(payload['purchase_units'][0]['items'], items)
        self.assertEqual(payload['payer']['email_address'], 'alex@example.com')
        self.assertIn('payment_source', payload)

    @override_settings(PAYPAL_CLIENT_ID='client-id', PAYPAL_CLIENT_SECRET='client-secret')
    @patch('myapp.views.create_paypal_order')
    def test_paypal_order_rejects_unknown_items(self, create_order):
        response = self.client.post(
            '/checkout/create-order/',
            data=json.dumps({
                'name': 'Alex Example',
                'email': 'alex@example.com',
                'items': [{'id': 'not-a-product', 'quantity': 1}],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        create_order.assert_not_called()

    @override_settings(PAYPAL_CLIENT_ID='client-id', PAYPAL_CLIENT_SECRET='client-secret')
    @patch('myapp.views.capture_paypal_order', return_value={
        'status': 'COMPLETED',
        'purchase_units': [{
            'payments': {
                'captures': [{
                    'status': 'COMPLETED',
                    'amount': {'currency_code': 'USD', 'value': '128.00'},
                }],
            },
        }],
    })
    def test_paypal_capture_verifies_session_order_and_amount(self, capture_order):
        session = self.client.session
        session['paypal_checkout_orders'] = {'ORDER-123': {'total': '128.00'}}
        session.save()

        response = self.client.post(
            '/checkout/capture-order/',
            data=json.dumps({'orderID': 'ORDER-123'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'COMPLETED', 'amount': '128.00'})
        capture_order.assert_called_once_with('ORDER-123')
        self.assertNotIn('ORDER-123', self.client.session.get('paypal_checkout_orders', {}))

    @override_settings(PAYPAL_CLIENT_ID='client-id', PAYPAL_CLIENT_SECRET='client-secret')
    @patch('myapp.views.capture_paypal_order', return_value={
        'status': 'COMPLETED',
        'purchase_units': [{
            'payments': {
                'captures': [{
                    'status': 'COMPLETED',
                    'amount': {'currency_code': 'USD', 'value': '1.00'},
                }],
            },
        }],
    })
    def test_paypal_capture_rejects_amount_mismatch(self, capture_order):
        session = self.client.session
        session['paypal_checkout_orders'] = {'ORDER-123': {'total': '128.00'}}
        session.save()

        response = self.client.post(
            '/checkout/capture-order/',
            data=json.dumps({'orderID': 'ORDER-123'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('ORDER-123', self.client.session.get('paypal_checkout_orders', {}))

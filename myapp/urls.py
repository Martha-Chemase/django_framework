from django.urls import path

from myapp import views


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='myabout'),
    path('products/', views.product, name='myproduct'),
    path('contact/', views.contact, name='mycontact'),
    path('journal/', views.journal, name='journal'),
    path('faqs/', views.faqs, name='faqs'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/create-order/', views.create_checkout_order, name='paypal-create-order'),
    path('checkout/capture-order/', views.capture_checkout_order, name='paypal-capture-order'),
]
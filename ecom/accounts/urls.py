from django.urls import path
from . import  views

#ecom_app urls

urlpatterns = [
    path('', views.index, name = 'index'),
    path('register/',views.register, name = 'register'),
    path('login/', views.log_in, name = 'login'),
    path('otp/', views.otp, name = 'my_otp'),
    path('resend_otp/', views.resend_otp, name = 'resend_otp'),
    path('verify_email/', views.verify_email, name = 'verify_email'),
    path('verify_otp/', views.verify_otp, name = 'verify_otp'),
    path('reset_pass/', views.reset_pass, name = 'reset_pass'),
    path('logout/', views.log_out, name = 'logout'),
    path('mens_page/', views.mens_page, name = 'mens_page' ),
    path('product_detail/<int:product_id>/', views.product_detail, name = 'product_detail'),
    path('womens_page/', views.womens_page, name = 'womens_page' ),
    path('kids_page/', views.kids_page, name = 'kids_page' ),
    path('shop_page/', views.shop_page, name = 'shop_page' ),
    path('profile/', views.profile, name = 'profile'),
    path('edit_profile/<int:info_id>/', views.edit_profile, name = 'edit_profile'),
    path('change_password/<int:pass_id>/',views.change_password, name = 'change_password'),
    path('address/', views.address, name = 'address'),
    path('add_address/', views.add_address, name = 'add_address'),
    path('edit_address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('delete_address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('search_pro/', views.search_pro, name='search_pro'),
    path('filter_products_by_price/', views.filter_products_by_price, name='filter_products_by_price'),

] 

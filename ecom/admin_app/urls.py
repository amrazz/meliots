from django.urls import path
from . import  views


# Admin_app urls

urlpatterns = [
    path('admin_login/', views.admin_login, name = 'admin_login'),
    path('admin_logout/', views.admin_logout, name = 'admin_logout'),
    path('dashboard/', views.dashboard, name ='dashboard'),
    path('customer/', views.customer, name = 'customer'),
    path('block-user/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock-user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('user_search/', views.user_search, name = 'user_search'),
    path('category/', views.category, name = 'category'),
    path('add_category/', views.add_category, name = 'add_category'),
    path('islisted/<int:cat_id>', views.islisted, name = 'islisted'),
    path('isunlisted/<int:cat_id>', views.isunlisted, name = 'isunlisted'),
    path('edit_category/<int:cat_id>/', views.edit_category, name='edit_category'),
    path('isdeleted/<int:cat_id>/', views.is_deleted, name = 'isdeleted'),
    path('restore/<int:cat_id>/', views.restore, name = 'restore'),
    path('recyclebin/', views.recycle_bin, name = 'recyclebin'),
    path('product/', views.product, name = 'product'),
    path('product_search/', views.product_search, name = 'product_search'),
    path('add_product/', views.add_product, name = 'add_product'),
    path('product_image/', views.product_image, name = 'product_image'),
    path('product_size/', views.product_size, name = 'product_size'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('product_is_deleted/<int:product_id>/', views.product_is_deleted, name = 'product_is_deleted' ),
    path('product_restore/<int:product_id>/', views.product_restore, name = 'product_restore'),
    path('product_recycle_bin/', views.product_recycle_bin, name = 'product_recycle_bin'),
    path('product_is_listed/<int:product_id>/', views.product_is_listed, name = 'product_is_listed'),
    path('product_is_unlisted/<int:product_id>/', views.product_is_unlisted, name = 'product_is_unlisted'),
    path('order/',views.order, name = 'order'),
    path('update_status/', views.update_status, name='update_status'),
    path('admin_order/<int:order_id>/', views.admin_order, name='admin_order'),
    path('admin_coupon/', views.admin_coupon, name='admin_coupon'),
    path('add_coupon/', views.add_coupon, name='add_coupon'),
    path('edit_coupon/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),


    
]

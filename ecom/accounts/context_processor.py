from cart_app.models import *

def default(request):
    cart_count = CartItem.objects.count()

    wishlist_count = WishList.objects.count()
    return {
        'cart_count': cart_count,
        'wishlist_count' : wishlist_count
    }
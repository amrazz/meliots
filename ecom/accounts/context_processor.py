from cart_app.models import *


def default(request):
    user = request.user
    cart_count = CartItem.objects.filter(user_cart__customer__user=user).count()

    wishlist_count = WishList.objects.filter(customer__user=user).count()
    return {"cart_count": cart_count, "wishlist_count": wishlist_count}

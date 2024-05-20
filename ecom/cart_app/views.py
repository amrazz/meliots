from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import JsonResponse
from .models import *
from django.contrib import messages, auth
from admin_app.models import *
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils.crypto import get_random_string
import razorpay
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from django.urls import reverse
from datetime import timedelta

# authorize razorpay client with API Keys.

razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)

# Create your views here.


def custom_404(request, exception):
    return render(request, "404.html", status=404)

def clear_coupon_session(request):
    if request.session.get("coupon_applied", False):
        del request.session["coupon_applied"]
        del request.session["coupon_name"]
        del request.session["coupon_discount_percentage"]
        del request.session["discounted_price"]
        messages.warning(request, "Coupon has been removed due to changes in the cart.")

@never_cache
@login_required(login_url="login")
def shop_cart(request):
    if request.user.is_authenticated:
        user = Customer.objects.get(user=request.user.pk)
        customer = User_Cart.objects.get(customer=user)
        cart_items = CartItem.objects.filter(
            user_cart=customer,
            product__product__is_listed=True,
            product__product__is_deleted=False,
        ).distinct()

        sub_total = sum(item.total_price for item in cart_items)
        total = sub_total

        total_quantity = sum(i.quantity for i in cart_items)
        if total_quantity >= 5:
            shipping_fee = "Free"
        else:
            shipping_fee = 99
        if shipping_fee == 99:
            total += shipping_fee

        context = {
            "cart_items": cart_items,
            "sub_total": sub_total,
            "total": total,
            "shipping_fee": shipping_fee,
        }

        return render(request, "shop_cart.html", context)
    else:
        return redirect("login")


@never_cache
def add_to_cart(request, pro_id):
    if request.user.is_authenticated:
         if request.method == "POST":
            product = ProductColorImage.objects.get(id=pro_id)
            selected_size = request.POST.get("size")
            size = ProductSize.objects.filter(
                productcolor__id=pro_id, size=selected_size
            ).first()


            if not size:
                messages.error(request, "Selected size is not available.")
                return redirect("product_detail", pro_id)

            quantity = int(request.POST.get("quantity"))
            if int(quantity) <= 0:
                messages.error(request, "Invalid quantity.")
                return redirect("product_detail", pro_id)

            if size.quantity < quantity:
                messages.error(request, "Selected quantity exceeds available stock.")
                return redirect("product_detail", pro_id)
            if CartItem.objects.filter(product=product).exists():
                messages.error(request, "Product already in Cart.")
                return redirect("product_detail", pro_id)

            user = Customer.objects.get(user=request.user.pk)
            user_cart = User_Cart.objects.get(customer=user)
            cart_item = CartItem.objects.create(
                user_cart=user_cart,
                product=product,
                quantity=quantity,
                product_size=selected_size,
            )
            cart_item.save()
            clear_coupon_session(request)  

            messages.success(request, "Product added to Cart.")
            return redirect("shop_cart")
    else:
        return redirect("login")


def delete_cart_items(request, pro_id):
    cart_items = CartItem.objects.get(id=pro_id)
    print(pro_id)
    cart_items.delete()
    clear_coupon_session(request)  
    messages.success(request, "Product removed from Cart")
    return redirect("shop_cart")


@never_cache
def update_total_price(request):
    if request.method == "POST":
        cart_item_id = request.POST.get("cart_item_id")
        new_quantity = int(request.POST.get("new_quantity"))
        cart_item = CartItem.objects.get(id=cart_item_id)
        cart_item.quantity = new_quantity
        cart_item.save()
        clear_coupon_session(request)  
        new_total_price = cart_item.total_price

        user = Customer.objects.get(user=request.user.pk)
        customer = User_Cart.objects.get(customer=user)
        cart_items = CartItem.objects.filter(user_cart=customer).distinct()

        sub_total = sum(item.total_price for item in cart_items)
        total_quantity = sum(i.quantity for i in cart_items)
        if total_quantity > 5:
            shipping_fee = "Free"
        else:
            shipping_fee = 99

        if shipping_fee == "Free":
            total = sub_total
        else:
            total = sub_total + shipping_fee

        return JsonResponse(
            {
                "new_total_price": new_total_price,
                "subtotal": sub_total,
                "total": total,
                "shipping_fee": shipping_fee,
            }
        )
    return JsonResponse({"error": "Invalid request"}, status=400)


def checkout(request):
    try:
        today = timezone.now()

        if request.user.is_authenticated:
            user = Customer.objects.get(user=request.user.pk)
            cart = CartItem.objects.filter(user_cart__customer=user)
            coupons = Coupon.objects.filter(is_active=True, expiry_date__gt=today)

            if not cart.exists():
                messages.error(request, "Your cart is empty.")
                return redirect("shop_cart")

            for item in cart:
                for i in item.product.size.all():
                    if item.quantity > i.quantity:
                        CartItem.objects.get(id=item.id).delete()

            sub_total = sum(price.total_price for price in cart)
            total = sub_total
            discount_amount = 0

            cart_qty = sum(item.quantity for item in cart)
            if cart_qty > 5:
                shipping_fee = "Free"
                total = sub_total
            elif cart_qty <= 5:
                shipping_fee = 99
                total = sub_total + shipping_fee

            if request.method == "POST":
                get_coupon = request.POST.get("coupon_code")
                action = request.POST.get("action")

                if action == "remove_coupon":
                    if request.session.get("coupon_applied", False):
                        del request.session["coupon_applied"]
                        del request.session["coupon_name"]
                        del request.session["coupon_discount_percentage"]
                        del request.session["discounted_price"]
                        messages.success(
                            request, "Coupon has been removed successfully."
                        )
                        return redirect("checkout")
                    else:
                        messages.error(request, "No coupon has been applied.")
                        return redirect("checkout")

                if get_coupon:
                    if request.session.get("coupon_applied", False):
                        messages.error(request, "You have already applied a Coupon.")
                        return redirect("checkout")

                    if not Coupon.objects.filter(
                        coupon_code=get_coupon, is_active=True
                    ).exists():
                        messages.error(request, "There is no Coupon with This name.")
                        return redirect("checkout")

                    if not Coupon.objects.filter(
                        coupon_code=get_coupon, expiry_date__gt=today
                    ).exists():
                        messages.error(request, "The coupon has expired.")
                        return redirect("checkout")

                    cpn = Coupon.objects.filter(
                        coupon_code=get_coupon, is_active=True
                    ).first()
                    if cpn:
                        if total >= cpn.minimum_amount and total <= cpn.maximum_amount:
                            discount_amount = (total * cpn.discount_percentage) / 100
                            total -= round(discount_amount)
                            request.session["coupon_applied"] = True
                            request.session["coupon_name"] = cpn.coupon_name
                            request.session["coupon_discount_percentage"] = (
                                cpn.discount_percentage
                            )
                            request.session["discounted_price"] = round(discount_amount)
                            messages.success(
                                request, "Coupon has been applied successfully."
                            )
                        else:
                            messages.error(
                                request,
                                f"Your total must be between ₹ {cpn.minimum_amount} and ₹ {cpn.maximum_amount} to apply this coupon.",
                            )
                            return redirect("checkout")

            custom = Customer.objects.get(user=request.user.pk)
            user_cart = User_Cart.objects.get(customer=custom)
            cart_items = CartItem.objects.filter(user_cart=user_cart)
            addresses = Address.objects.filter(user=request.user)

            if not addresses.exists():
                messages.warning(
                    request, "You have no saved address. Please add an Address first."
                )
                return redirect("address")

            context = {
                "cartitems": cart_items,
                "addresses": addresses,
                "total": total,
                "sub_total": sub_total,
                "shipping_fee": shipping_fee,
                "coupons": coupons,
                "discount_amount": round(discount_amount),
                "coupon_applied": request.session.get("coupon_applied", False),
            }

            return render(request, "checkout.html", context)
        else:
            return redirect("login")
    except Exception as e:
        messages.error(request, "Something went wrong please try again.")
        return redirect("checkout")


def initiate_payment(items):
    data = {
        "currency": "INR",
        "payment_capture": "1",
        "amount": items[0]["amount"],
    }
    print(data["amount"])
    print("this is the amount in the imitia paymnt")
    razorpay_order = razorpay_client.order.create(data=data)
    razorpay_order_id = razorpay_order["id"]
    for item in items:
        item_data = {
            "amount": item["amount"],
            "currency": "INR",
        }
        razorpay_client.order.create(data=item_data)
    return razorpay_order_id


@transaction.atomic
def place_order(request):
    if request.method == "POST":
        address_id = request.POST.get("select_address")
        address = Address.objects.get(id=address_id)
        pm = request.POST.get("payment_method")

        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect("checkout")
        if not pm:
            messages.error(request, "Please select a Payment Method.")
            return redirect("checkout")

        customer = Customer.objects.get(user=request.user.pk)
        cart = CartItem.objects.filter(user_cart__customer=customer)
        subtotal = sum(item.total_price for item in cart)
        total_qty = sum(item.quantity for item in cart)

        if total_qty <= 5:
            shipping_fee = 99
        else:
            shipping_fee = 0
        total = subtotal if total_qty > 5 else 99 + subtotal

        tk_id = get_random_string(10, "ABCDEFGHIJKLMOZ0123456789")
        while Order.objects.filter(tracking_id=tk_id).exists():
            tk_id = get_random_string(10, "ABCDEFGHIJKLMOZ0123456789")

        coupon_applied = request.session.get("coupon_applied")
        coupon_name = request.session.get("coupon_name")
        coupon_discount_percentage = request.session.get("coupon_discount_percentage")
        discounted_price = request.session.get("discounted_price")

        if "coupon_applied" in request.session:
            total -= discounted_price
            used_coupon = Coupon.objects.filter(coupon_name=coupon_name).first()
            if used_coupon:
                used_coupon.used_count += 1
                used_coupon.save()
        else:
            coupon_applied = False
            coupon_name = None
            coupon_discount_percentage = None
            discounted_price = 0

        if request.POST.get("payment_method") == "Razorpay":
            items = [
                {
                    "amount": total * 100,
                }
            ]
            order_id = initiate_payment(items)
            payment = Payment.objects.create(
                method_name=pm,
                amount=total,
                transaction_id=order_id,
                paid_at=timezone.now(),
                pending=False,
                success=True,
            )
            if order_id is None:
                print("hdhfjkshdjkfhdsf")
                messages.error(request, "Payment initiation failed. Please try again.")
                payment.success = False
                payment.failed = True
                payment.pending = True
                payment.save()
                print("dfh paymne  sussufillll")

                order = Order.objects.create(
                    customer=customer,
                    address=address,
                    payment_method=pm,
                    subtotal=subtotal,
                    shipping_charge=shipping_fee,
                    total=total,
                    paid=False,
                    tracking_id=tk_id,
                    coupon_applied=coupon_applied,
                    coupon_name=coupon_name,
                    coupon_discount_percentage=coupon_discount_percentage,
                    discounted_price=discounted_price,
                    payment=payment,
                    status="Payment Failed",
                )
                for cart_item in cart:
                    OrderItem.objects.create(
                        order=order,
                        status="Pending",
                        product=cart_item.product,
                        each_price=cart_item.product.product.offer_price,
                        qty=cart_item.quantity,
                        size=cart_item.product_size,
                    )
                    print("come hererefersdfasdfdsf")

                    product = cart_item.product.pk
                    print(product)
                    product_size = ProductSize.objects.filter(productcolor__id=product)
                    print(product_size)
                    if product_size.exists():
                        for qty in product_size:
                            print("in the if product_size")
                            qty.quantity -= cart_item.quantity
                            qty.save()
                    print("product quantity is reduced")

                cart.delete()

                keys_to_delete = [
                    "coupon_applied",
                    "coupon_name",
                    "coupon_discount_percentage",
                    "discounted_price",
                ]
                for key in keys_to_delete:
                    if key in request.session:
                        del request.session[key]
                return redirect("payment_failure")
            else:
                try:
                    order = Order.objects.create(
                        customer=customer,
                        address=address,
                        payment_method=pm,
                        subtotal=subtotal,
                        shipping_charge=shipping_fee,
                        total=total,
                        paid=True,
                        tracking_id=tk_id,
                        coupon_applied=coupon_applied,
                        coupon_name=coupon_name,
                        coupon_discount_percentage=coupon_discount_percentage,
                        discounted_price=discounted_price,
                        payment_transaction_id=order_id,
                        payment=payment,
                        status="Payment Successful",
                    )
                    for cart_item in cart:
                        OrderItem.objects.create(
                            order=order,
                            status="Order Placed",
                            product=cart_item.product,
                            each_price=cart_item.product.product.offer_price,
                            qty=cart_item.quantity,
                            size=cart_item.product_size,
                        )
                        product = cart_item.product.pk
                        print(product)
                        product_size = ProductSize.objects.filter(
                            productcolor__id=product
                        )
                        print(product_size)
                        if product_size.exists():
                            for qty in product_size:
                                print("in the if product_size")
                                qty.quantity -= cart_item.quantity
                                qty.save()
                                print("product quantity is reduced")

                    cart.delete()

                    keys_to_delete = [
                        "coupon_applied",
                        "coupon_name",
                        "coupon_discount_percentage",
                        "discounted_price",
                    ]
                    for key in keys_to_delete:
                        if key in request.session:
                            del request.session[key]

                    return redirect("order_detail")
                except Exception:
                    pass

        if request.POST.get("payment_method") == "wallet":
            user_customers = customer.user
            balance = Wallet.objects.get(user=user_customers)
            if balance.balance < total:
                messages.error(request, "Insufficient balance in your wallet.")
                return redirect("checkout")
            else:
                transaction_id = "WALLET_TRANSFER_" + get_random_string(
                    4, "ABC123456789"
                )
                while Order.objects.filter(tracking_id=transaction_id).exists():
                    transaction_id += get_random_string(4, "ABC123456789")
                payment = Payment.objects.create(
                    method_name=pm,
                    amount=total,
                    transaction_id=transaction_id,
                    paid_at=timezone.now(),
                    pending=False,
                    success=True,
                )
                try:
                    order = Order.objects.create(
                        customer=customer,
                        address=address,
                        payment_method=pm,
                        subtotal=subtotal,
                        shipping_charge=shipping_fee,
                        total=total,
                        paid=True,
                        tracking_id=tk_id,
                        coupon_applied=coupon_applied,
                        coupon_name=coupon_name,
                        coupon_discount_percentage=coupon_discount_percentage,
                        discounted_price=discounted_price,
                        payment_transaction_id=transaction_id,
                        payment=payment,
                        status="Payment Successful",
                    )
                    for cart_item in cart:
                        order_item = OrderItem.objects.create(
                            order=order,
                            status="Order Placed",
                            product=cart_item.product,
                            each_price=cart_item.product.product.offer_price,
                            qty=cart_item.quantity,
                            size=cart_item.product_size,
                        )
                        product = cart_item.product.pk
                        print(product)
                        product_size = ProductSize.objects.filter(
                            productcolor__id=product
                        )
                        print(product_size)
                        if product_size.exists():
                            for qty in product_size:
                                print("in the if product_size")
                                qty.quantity -= cart_item.quantity
                                qty.save()
                                print("product quantity is reduced")
                    balance.balance -= total
                    balance.save()
                    wallet_transaction = Wallet_transaction.objects.create(
                        wallet=balance,
                        order_item=order_item,
                        transaction_id=transaction_id,
                        money_withdrawn=total,
                    )

                    cart.delete()

                    keys_to_delete = [
                        "coupon_applied",
                        "coupon_name",
                        "coupon_discount_percentage",
                        "discounted_price",
                    ]
                    for key in keys_to_delete:
                        if key in request.session:
                            del request.session[key]

                    messages.success(request, "Order placed successfully.")
                    return redirect("order_detail")
                except Exception:
                    return redirect("payment_failure")

        elif request.POST.get("payment_method") == "COD":
            order = Order.objects.create(
                customer=customer,
                address=address,
                payment_method=pm,
                subtotal=subtotal,
                shipping_charge=shipping_fee,
                total=total,
                tracking_id=tk_id,
                coupon_applied=coupon_applied,
                coupon_name=coupon_name,
                coupon_discount_percentage=coupon_discount_percentage,
                discounted_price=discounted_price,
                status="Pending",
            )

            for cart_item in cart:
                OrderItem.objects.create(
                    order=order,
                    status="Order Placed",
                    product=cart_item.product,
                    each_price=cart_item.product.product.offer_price,
                    qty=cart_item.quantity,
                    size=cart_item.product_size,
                )
                print("come hererefersdfasdfdsf")

                product = cart_item.product.pk
                print(product)
                product_size = ProductSize.objects.filter(productcolor__id=product)
                print(product_size)
                if product_size.exists():
                    for qty in product_size:
                        print("in the if product_size")
                        qty.quantity -= cart_item.quantity
                        qty.save()
                        print("product quantity is reduced")

            cart.delete()

            keys_to_delete = [
                "coupon_applied",
                "coupon_name",
                "coupon_discount_percentage",
                "discounted_price",
            ]
            for key in keys_to_delete:
                if key in request.session:
                    del request.session[key]

            messages.success(request, "Order placed successfully.")
            return redirect("order_detail")
        else:
            return redirect("checkout")


def payment_success(request):
    if request.method == "POST":
        order_id = request.POST.get("razorpay_order_id")
        payment_id = request.POST.get("order_id")
        signature = request.POST.get("razorpay_signature")
    else:
        messages.error(
            request, "Something went wrong in the payment section please try again."
        )
        return redirect("checkout")
    params_dict = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    }
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        # Payment signature verification successful
        # Perform any required actions (e.g., update the order status)
        return render(request, "op.html")
    except razorpay.errors.SignatureVerificationError as e:
        return redirect("payment_failure")


# ____________________________________________________________________________________________________________________
def order_detail(request):
    return render(request, "op.html")


def payment_failure(request):
    return render(request, "opf.html")


def view_all_order(request):
    if request.user.is_authenticated:
        user = request.user
        customer = Customer.objects.get(user=user)
        orders = Order.objects.filter(customer=customer).order_by("-created_at")
        return render(request, "view_all_order.html", {"orders": orders})
    else:
        return redirect("login")


def view_order(request, ord_id):
    if request.user.is_authenticated:
        customer = get_object_or_404(Customer, user=request.user)
        order = get_object_or_404(Order, pk=ord_id)
        items = OrderItem.objects.filter(order=order).order_by("-created_at")
        context = {"order": order, "items": items}
        return render(request, "view_order.html", context)
    else:
        return redirect("login")


def view_status(request, order_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        order_items = OrderItem.objects.get(pk=order_id)
        currentTime = timezone.now().date()
        status_info = {
            "Order Placed": {"color": "#009608", "label": "Order Placed"},
            "Shipped": {"color": "#009608", "label": "Shipped"},
            "Out for Delivery": {"color": "#009608", "label": "Out for Delivery"},
            "Delivered": {"color": "#009608", "label": "Delivered"},
        }
        context = {
            "order_items": order_items,
            "status_info": status_info,
            "currentTime": currentTime,
        }
        return render(request, "view_status.html", context)
    else:
        return redirect("login")


def request_cancel_order(request, order_id):
    print(order_id)
    if request.user.is_authenticated:
        order_item = OrderItem.objects.get(pk=order_id)
        if order_item.order.customer.user == request.user:
            order_item.request_cancel = True
            order_item.save()
            return render(request, "view_status.html", {"order_items": order_item})
    return redirect("login")


def request_return_product(request, order_id):
    if request.user.is_authenticated:
        print("joiii")
        seven_days = timezone.now() - timedelta(days=7)
        order_item = OrderItem.objects.get(pk=order_id)
        print(order_item)

        if order_item.created_at > seven_days and order_item.status == "Delivered":
            print("reached here")
            order_item.request_return = True
            order_item.save()
            print(order_item.request_return)
            return redirect("view_status", order_id)
        else:
            messages.info(
                request, "You can only request for return product within 7 days."
            )
            return redirect("view_status", order_id)
    return redirect("login")


# _______________________________________________________________________________________________________________________


def wishlist_view(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        wished_products = WishList.objects.filter(customer=customer)
        context = {
            "wished_products": wished_products,
        }
        return render(request, "wishlist.html", context)
    else:
        return redirect("login")


def wishlist_add(request, pro_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user)
        product = ProductColorImage.objects.get(id=pro_id)

        if WishList.objects.filter(product=product).exists():
            messages.info(request, "Product already in Wishlist.")
            return redirect("product_detail", pro_id)

        wishlist_item, created = WishList.objects.get_or_create(
            customer=customer, product=product, size="S", qty=1
        )
        wishlist_item.save()

        if created:
            messages.success(request, "Product added to wishlist.")
        else:
            messages.info(request, "Product already in wishlist.")

        return redirect("product_detail", product_id=pro_id)

    else:
        return redirect("login")


def wishlist_del(request, pro_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        WishList.objects.filter(id=pro_id, customer=customer).delete()
        messages.success(request, "Product removed from wishlist.")
        return redirect("wishlist_view")
    else:
        return redirect("login")


# ___________________________________________________________________________________________________________________________________________________________________

#                                                   COUPONS SECTION

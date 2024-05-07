from PIL import Image
from django.shortcuts import render, redirect, HttpResponse
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.contrib import messages, auth
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import *
from cart_app.models import *
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, F
from django.utils.crypto import get_random_string
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch

PRODUCT_PER_PAGE = 9


# Create your views here


@never_cache
def admin_login(request):
    try:
        if request.user.is_superuser:
            return redirect("dashboard")
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")
            sp_user = authenticate(request, username=username, password=password)
            if sp_user is not None and sp_user.is_superuser:
                login(request, sp_user)
                return redirect("dashboard")
            else:
                messages.error(request, "Sorry, only admins are allowed.")
        return render(request, "login.html")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")


@never_cache
def dashboard(request):
    try:
        if request.user.is_superuser:
            users = User.objects.all()
            return render(request, "dashboard.html", {"users": users})
        else:
            messages.error(request, "Only admins are allowed.")
            return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")


@never_cache
def admin_logout(request):
    try:
        logout(request)
        return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")


@never_cache
def customer(request):
    try:
        if request.user.is_superuser:
            users = User.objects.all().order_by("id")
            return render(request, "customer.html", {"users": users})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def block_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        messages.success(request, f"User {user.username} has been blocked.")

    except Exception as e:
        messages.error(request, str(e))
    return redirect("customer")


@never_cache
def unblock_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        messages.success(request, f"User {user.username} has been unblocked.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("customer")


@never_cache
def user_search(request):
    try:
        if request.method == "POST":
            get_search = request.POST.get("search")
            return_search = User.objects.filter(
                Q(username__icontains=get_search) | Q(email__icontains=get_search)
            )
            return render(request, "customer.html", {"users": return_search})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("customer")


@never_cache
def category(request):
    try:
        if request.user.is_superuser:
            cat_gory = Category.objects.all().order_by("id")
            return render(request, "category/category.html", {"cat_gory": cat_gory})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def add_category(request):
    if request.user.is_superuser:
        if request.method == "POST":
            name = request.POST.get("name")
            description = request.POST.get("description")
            image = request.FILES.get("image")
            if not all([name, description, image]):
                messages.error(request, "All fields are required.")
                return redirect("add_category")
            if Category.objects.filter(name=name).exists():
                messages.error(request, "Category with this name already exists.")
                return redirect("add_category")
            create_category = Category.objects.create(
                name=name, description=description, cat_image=image
            )
            create_category.save()
            messages.success(request, "Category added successfully.")
            return redirect("category")
    return render(request, "category/add_category.html")


@never_cache
def edit_category(request, cat_id):
    try:
        if request.user.is_superuser:
            category = Category.objects.get(id=cat_id)

            if request.method == "POST":
                name = request.POST.get("editname")
                description = request.POST.get("description")
                image = request.FILES.get("editimage")
                if not all([name, description]):
                    messages.error(request, "Name and description are required.")
                    return redirect("edit_category", cat_id=cat_id)
                if Category.objects.filter(name=name).exclude(id=cat_id).exists():
                    messages.error(request, "Category with this name already exists.")
                    return redirect("edit_category", cat_id=cat_id)

                category.name = name
                category.description = description
                category.cat_image = image
                category.save()
                messages.success(request, "Category updated successfully.")
                return redirect("category")

        return render(request, "category/edit_category.html", {"category": category})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def islisted(request, cat_id):
    try:
        listed = Category.objects.get(id=cat_id)
        listed.is_listed = True
        listed.save()
        Product.objects.filter(category=listed).update(is_listed=True)

    except Exception as e:
        messages.error(request, str(e))
    return redirect("category")


@never_cache
def isunlisted(request, cat_id):
    try:
        listed = Category.objects.get(id=cat_id)
        listed.is_listed = False
        listed.save()
        Product.objects.filter(category=listed).update(is_listed=False)

    except Exception as e:
        messages.error(request, str(e))
    return redirect("category")


@never_cache
def is_deleted(request, cat_id):
    try:
        deleted = Category.objects.get(id=cat_id)
        deleted.is_deleted = True
        deleted.save()
    except Exception as e:
        messages.error(request, str(e))
    return redirect("recyclebin")


@never_cache
def recycle_bin(request):
    try:
        if request.user.is_superuser:
            category = Category.objects.all().order_by("id")
            Products = Product.objects.all().order_by("id")

            return render(request, "restore.html", {"category": category})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def restore(request, cat_id):
    try:
        restore = Category.objects.get(id=cat_id)
        restore.is_deleted = False
        restore.save()
    except Exception as e:
        messages.error(request, str(e))
    return redirect("category")


# _____________________________________________________________Product_____________________________________________________________________


@never_cache
def product(request):
    try:
        if request.user.is_superuser:
            products = ProductColorImage.objects.filter(is_deleted=False).order_by("id")
            page = request.GET.get("page", 1)
            product_Paginator = Paginator(products, PRODUCT_PER_PAGE)

            try:
                products = product_Paginator.page(page)
            except PageNotAnInteger:
                products = product_Paginator.page(1)
            except EmptyPage:
                products = product_Paginator.page(product_Paginator.num_pages)

            context = {
                "products": products,
                "page_obj": products,
                "is_paginated": product_Paginator.num_pages > 1,
                "paginator": product_Paginator,
            }
            return render(request, "product/product.html", context)
        else:
            messages.error(request, "Only admins are allowed.")
            return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("admin_login")


def is_valid_image(file):
    # Check if the file is an image
    if not isinstance(file, UploadedFile):
        return False

    try:

        Image.open(file)
        return True
    except Exception as e:
        return False


@never_cache
def edit_product(request, product_id):
    try:
        color_image = ProductColorImage.objects.get(id=product_id)
        print(color_image.color)
        sizes = ProductSize.objects.filter(productcolor_id=color_image.pk)
        print("sizes", " :", sizes)
        if request.method == "POST":
            name = request.POST.get("name")
            category_id = request.POST.get("category")
            type = request.POST.get("type")
            price = request.POST.get("price")
            percentage = request.POST.get("percentage")
            if int(percentage) < 0 or int(percentage) > 100:
                messages.error(request, "The percentage must be between 0 and 100.")
                return redirect("product")

            exp_date = request.POST.get("exp_date")
            if exp_date:
                try:
                    exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, "Invalid date format for expiry date.")
                    return redirect("product")
            else:
                exp_date = None

            description = request.POST.get("description")
            if float(price) < 0:
                messages.error(request, "The price cannot be negative number.")
                return redirect("product")
            image1 = request.FILES.get("image1")
            image2 = request.FILES.get("image2")
            image3 = request.FILES.get("image3")
            image4 = request.FILES.get("image4")

            if image1 and not is_valid_image(image1):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")
            elif image2 and not is_valid_image(image2):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")
            elif image3 and not is_valid_image(image3):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")
            elif image4 and not is_valid_image(image4):
                messages.error(request, "This is not a valid image file.")
                return redirect("product")

            category = Category.objects.get(id=category_id)

            color_image.product.name = name
            color_image.product.per_expiry_date = exp_date
            color_image.product.description = description
            color_image.product.type = type
            color_image.product.price = price
            color_image.product.percentage = percentage
            color_image.product.category = category
            color_image.product.save()

            if color_image:
                if image1:
                    color_image.image1 = image1
                if image2:
                    color_image.image2 = image2
                if image3:
                    color_image.image3 = image3
                if image4:
                    color_image.image4 = image4
                color_image.save()

            s = request.POST.get("S")
            m = request.POST.get("M")
            l = request.POST.get("L")

            if ProductSize.objects.filter(productcolor=color_image, size="S").exists():
                ProductSize.objects.filter(productcolor=color_image, size="S").update(
                    quantity=s
                )
            if ProductSize.objects.filter(productcolor=color_image, size="M").exists():
                ProductSize.objects.filter(productcolor=color_image, size="M").update(
                    quantity=m
                )
            if ProductSize.objects.filter(productcolor=color_image, size="L").exists():
                ProductSize.objects.filter(productcolor=color_image, size="L").update(
                    quantity=l
                )

            messages.success(request, "Product updated successfully.")
            return redirect("product")
        else:
            return render(
                request,
                "product/edit_product.html",
                {"color_image": color_image, "sizes": sizes},
            )
    except Product.DoesNotExist:
        messages.error(request, "Product not found.")
        return redirect("product")


@never_cache
def product_search(request):
    try:
        if request.method == "POST":
            search = request.POST.get("search_product")
            products = ProductColorImage.objects.filter(product__name__icontains=search)
            return render(request, "product/product.html", {"products": products})
        print("successfully send")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("product")


# ____________________________________________________________________________________________________________________________________________________
@never_cache
def add_product(request):
    try:
        if request.user.is_superuser:
            categories = Category.objects.all()
            if request.method == "POST":
                name = request.POST.get("name")
                category = request.POST.get("category")
                type = request.POST.get("type")
                price = request.POST.get("price")
                percentage = request.POST.get("percentage")
                exp_date = request.POST.get("exp_date")

                description = request.POST.get("description")

                if not all([name, type, price, description]):
                    messages.error(request, "All fields are required.")
                    return redirect("add_product")

                if Product.objects.filter(name=name).exists():
                    messages.error(request, "Product with this name already exists.")
                    return redirect("add_product")
                try:
                    price = float(price)
                    if price <= 0:
                        raise ValueError
                except ValueError:
                    messages.error(request, "Please enter a valid positive price.")
                    return redirect("add_product")
                add_product = Product.objects.create(
                    name=name,
                    category_id=category,
                    type=type,
                    price=price,
                    percentage=percentage,
                    per_expiry_date=exp_date,
                    description=description,
                )
                add_product.save()
                print("product added successfully")
                return redirect("product_image")
            return render(
                request, "product/add_product.html", {"categories": categories}
            )
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def product_image(request):
    try:
        if request.user.is_superuser:
            products = Product.objects.all()
            if request.method == "POST":
                product_id = request.POST.get("product")
                color = request.POST.get("color")
                image1 = request.FILES.get("image1")
                image2 = request.FILES.get("image2")
                image3 = request.FILES.get("image3")
                image4 = request.FILES.get("image4")

                if not is_valid_image(image1):
                    messages.error(request, "This is not a valid image file.")
                    return redirect("product")
                elif not is_valid_image(image2):
                    messages.error(request, "This is not a valid image file.")
                    return redirect("product")
                elif not is_valid_image(image3):
                    messages.error(request, "This is not a valid image file.")
                    return redirect("product")
                elif not is_valid_image(image4):
                    messages.error(request, "This is not a valid image file.")
                    return redirect("product")

                product = get_object_or_404(Product, id=product_id)
                if not all([product_id, color]):
                    messages.error(request, "Product and color are required.")
                    return redirect("product_image")
                create_product = ProductColorImage.objects.create(
                    product=product,
                    color=color,
                    image1=image1,
                    image2=image2,
                    image3=image3,
                    image4=image4,
                )
                create_product.save()
                return redirect("product_size")
            else:
                return render(
                    request, "product/product_image.html", {"products": products}
                )
        else:
            return redirect("product")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")


@never_cache
def product_size(request):
    try:
        if request.user.is_superuser:
            product_colors = ProductColorImage.objects.all()
            if request.method == "POST":
                product_color_id = request.POST.get("product_color")
                size = request.POST.get("size")
                quantity = request.POST.get("quantity")
                product_color = get_object_or_404(
                    ProductColorImage, id=product_color_id
                )
                product_size = ProductSize.objects.create(
                    productcolor=product_color, size=size, quantity=quantity
                )
                print(product_size)
                product_size.save()

                return redirect("product")
            else:
                return render(
                    request,
                    "product/product_size.html",
                    {"product_colors": product_colors},
                )
        else:
            return redirect("product")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")


# ____________________________________________________________________________________________________________________________________________________
@never_cache
def product_restore(request, product_id):
    try:
        restore_product = ProductColorImage.objects.get(id=product_id)
        restore_product.is_deleted = False
        restore_product.save()
        return redirect("product")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")


@never_cache
def product_is_deleted(request, product_id):
    try:
        products = ProductColorImage.objects.get(id=product_id)
        products.is_deleted = True
        products.save()
        return redirect("product")
    except Exception as e:
        messages.error(request, str(e))
        return redirect("product")


@never_cache
def product_recycle_bin(request):
    try:
        if request.user.is_superuser:
            products = ProductColorImage.objects.filter(is_deleted=True).order_by("id")

            return render(request, "product_restore.html", {"products": products})
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


# ____________________________________________________________________________________________________________________________________________________
@never_cache
def product_is_listed(request, product_id):
    product_color = ProductColorImage.objects.get(id=product_id)
    product_color.is_listed = True
    product_color.save()
    return redirect("product")


@never_cache
def product_is_unlisted(request, product_id):
    product_color = ProductColorImage.objects.get(id=product_id)
    product_color.is_listed = False
    product_color.save()
    return redirect("product")


# ____________________________________________________________________________________________________________________________________________________


def order(request):
    if request.user.is_superuser:
        order_details = Order.objects.all().order_by("-created_at")

        context = {
            "order_details": order_details,
        }
        return render(request, "order/order.html", context)
    else:
        return redirect("admin_login")


def admin_order(request, order_id):
    if request.user.is_superuser:
        order = Order.objects.get(id=order_id)
        item = OrderItem.objects.filter(order=order)
        status_choices = dict(OrderItem.STATUS_CHOICES)

        context = {"item": item, "order": order, "status_choices": status_choices}
        return render(request, "order/order_detail.html", context)
    else:
        return redirect("admin_login")


def update_status(request):
    if request.user.is_superuser and request.method == "POST":
        order_item_id = request.POST.get("order_item_id")
        new_status = request.POST.get("new_status")

        try:
            order_item = OrderItem.objects.get(id=order_item_id)
            order_item.status = new_status
            order_item.save()
            return JsonResponse({"status": "success"})
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "message": "Order item not found."})

    return JsonResponse(
        {"status": "error", "message": "Unauthorized or invalid request."}
    )


@transaction.atomic
def cancel_order(request, order_id):
    print("==========================================================")
    print(f"Entering cancel_order with order_id {order_id}")
    if request.user.is_superuser:
        print("User is a superuser")
        try:
            print("Searching for OrderItem")
            cancel = OrderItem.objects.filter(order=order_id).first()

            if cancel.request_cancel:
                print("Order item requested cancellation")
                cancel.cancel = True
                cancel.status = "Cancelled"

                print("Updating order item")
                cancel.request_cancel = False
                cancel.save()
                print("Order item updated")

                if cancel.order.payment_method != "COD" and cancel.order.paid:
                    print("Order is paid and using a payment method other than COD")
                    user = request.user
                    total_discount = cancel.order.discounted_price

                    print("Calculating discount per item")
                    total_quantity = OrderItem.objects.filter(
                        order_id=order_id
                    ).aggregate(total_quantity=Sum("qty"))["total_quantity"]
                    discount_per_item = total_discount / total_quantity

                    original_price = cancel.product.product.offer_price()

                    cancelled_amount = (original_price - discount_per_item) * cancel.qty

                    print(
                        total_discount,
                        total_quantity,
                        discount_per_item,
                        original_price,
                        cancelled_amount,
                    )

                    print("Searching for wallet for user")
                    wallet, created = Wallet.objects.get_or_create(user=user)
                    print(
                        f"Found wallet for user {user.username} and balance is {wallet.balance}"
                    )
                    wallet.balance += abs(cancelled_amount)
                    wallet.save()
                    print("Wallet updated")

                    tranc_id = "TRANC_"
                    tranc_id += get_random_string(5, "ABCDEFGHIJKLMOZ0123456789")

                    while Wallet_transaction.objects.filter(
                        transaction_id=tranc_id
                    ).exists():
                        tranc_id += get_random_string(5, "ABCDEFGHIJKLMOZ0123456789")
                    print(tranc_id)

                    print("Creating wallet transaction")
                    wallet_transaction_create = Wallet_transaction.objects.create(
                        wallet=wallet,
                        order_item=cancel,
                        money_deposit=abs(cancelled_amount),
                        transaction_id=tranc_id,
                    )
                    print("Wallet transaction created")
                    messages.success(
                        request, f"Amount of ₹{cancelled_amount} added to your Wallet."
                    )
                    print("Amount added to wallet and transaction created")
                    return redirect("admin_order", order_id)

        except OrderItem.DoesNotExist:
            print("Order item does not exist")
            messages.info(request, "Order item does not exist")
            return redirect("order")

        print("Order has already been cancelled")
        messages.info(request, "Order has already been cancelled")
        return redirect("order")
    else:
        print("User is not a superuser")
        return redirect("admin_login")
    print("==========================================================")


def return_order(request, order_id):
    if request.user.is_superuser:
        return_order = OrderItem.objects.get(order_id=order_id)
        if return_order.request_return == True:
            return_order.return_order = True
            return_order.status = "Returned"
            return_order.request_return == False
            return_order.save()
            return redirect("admin_order", order_id)
        messages.info(request, "Order has already been returned")
        return redirect("order")
    else:
        return redirect("admin_login")


# _________________________________________________________________________________________________


def admin_coupon(request):
    if request.user.is_superuser:
        coupons = Coupon.objects.filter(is_active=True).order_by("id")
        context = {"coupons": coupons}
        return render(request, "coupon/admin_coupon.html", context)
    else:
        return redirect("admin_login")


def add_coupon(request):
    # try:
    if request.user.is_superuser:
        today = timezone.now().date()

        if request.method == "POST":
            code = request.POST.get("coupon_code")
            if Coupon.objects.filter(coupon_code=code).exists():
                messages.error(
                    request, "This coupon already exists. Please add a new one."
                )
                return redirect("add_coupon")

            name = request.POST.get("name")
            dis = request.POST.get("discount_percentage")

            if float(dis) < 0 or float(dis) > 100:
                messages.error(
                    request, "Please provide a valid discount between 0 and 100."
                )
                return redirect("add_coupon")

            minimum_amount = request.POST.get("minimum_amount")
            maximum_amount = request.POST.get("maximum_amount")

            if float(minimum_amount) < 0 or float(maximum_amount) < 0:
                messages.error(request, "Price must be a positive value.")
                return redirect("add_coupon")

            end_date = request.POST.get("end_date")
            print(end_date, "==", today)
            usage_limit = request.POST.get("usage_limit")

            if not all(
                [code, name, dis, minimum_amount, maximum_amount, end_date, usage_limit]
            ):
                messages.error(
                    request, "All fields are required for adding the coupon."
                )
                return redirect("add_coupon")
            print("reached")
            coupon = Coupon.objects.create(
                coupon_code=code,
                coupon_name=name,
                discount_percentage=dis,
                minimum_amount=minimum_amount,
                maximum_amount=maximum_amount,
                expiry_date=end_date,
                usage_limit=usage_limit,
            )
            print(coupon)
            print("oiii oiii")
            messages.success(request, "Coupon added successfully.")
            return redirect("admin_coupon")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")
    # except Exception as e:
    #     messages.error(request, str(e))

    return render(request, "coupon/add_coupon.html")


def edit_coupon(request, coupon_id):
    if request.user.is_superuser:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        if request.method == "POST":
            code = request.POST.get("coupon_code")
            name = request.POST.get("name")
            dis = request.POST.get("discount_percentage")
            min_amount = request.POST.get("minimum_amount")
            max_amount = request.POST.get("maximum_amount")
            end_date = request.POST.get("end_date")
            usage_limit = request.POST.get("usage_limit")

            if dis:
                if float(dis) < 0 or float(dis) > 100:
                    messages.error(
                        request,
                        "Please provide a valid discount percentage between 0 and 100.",
                    )
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.discount_percentage = dis

            if min_amount:
                if float(min_amount) < 0:
                    messages.error(request, "Minimum amount must be a positive value.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.minimum_amount = min_amount
            if max_amount:
                if float(max_amount) < 0:
                    messages.error(request, "Maximum amount must be a positive value.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.maximum_amount = max_amount

            if code:
                coupon.coupon_code = code
            if name:
                coupon.coupon_name = name
            if end_date:
                coupon.expiry_date = end_date
            if usage_limit:
                coupon.usage_limit = usage_limit

            coupon.save()
            messages.success(request, "Coupon edited successfully.")
            return redirect("admin_coupon")

        return render(request, "coupon/edit_coupon.html", {"coupon": coupon})
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def del_coupon(request, coupon_id):
    if request.user.is_superuser:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.delete()
        messages.success(request, "The coupon has been deleted Successfully.")
        return redirect("admin_coupon")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def sales_report(request):
    if request.user.is_superuser:
        order = OrderItem.objects.all().order_by("created_at")
        count = order.count()
        total = OrderItem.objects.aggregate(total=Sum("order__total"))["total"]
        total_discount = OrderItem.objects.aggregate(
            total_discount=Sum("order__discounted_price")
        )["total_discount"]

        context = {
            "order": order,
            "count": count,
            "total": total,
            "total_discount": total_discount,
        }
        return render(request, "sales_report.html", context)
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def download_sales_report(request):
    format = request.GET.get("format", "pdf")
    order_items = OrderItem.objects.all().order_by("created_at")

    if format == "pdf":
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'

        # Create a PDF document
        doc = SimpleDocTemplate(
            response, pagesize=letter, topMargin=1 * inch, bottomMargin=1 * inch
        )

        # Create a list to hold table data
        table_data = [
            [
                "PRODUCT",
                "ORDER DATE",
                "CUSTOMER DETAILS",
                "APPLIED COUPON",
                "DISCOUNTED PRICE",
            ],
        ]

        # Populate table data
        for item in order_items:
            created_at_formatted = item.created_at.strftime("%d/%m/%y %H:%M")
            table_data.append(
                [
                    f"{item.product.product.name} ({item.product.color}) {item.size} {item.qty}",
                    created_at_formatted,
                    f"{item.order.customer.user.first_name} {item.order.customer.user.last_name}",
                    str(item.order.coupon_name),
                    str(item.order.discounted_price),
                ]
            )

        # Create a table with adjusted column widths
        table = Table(
            table_data,
            colWidths=[2 * inch, 1.5 * inch, 2 * inch, 1.5 * inch, 1.5 * inch],
        )

        # Define table style
        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )

        # Apply table style
        table.setStyle(table_style)

        # Add table to document
        elements = []
        elements.append(Paragraph("SALES REPORT", getSampleStyleSheet()["Title"]))
        elements.append(Paragraph("MELIOTIS", getSampleStyleSheet()["Normal"]))
        elements.append(
            Paragraph("meliotis100@gmail.com", getSampleStyleSheet()["Normal"])
        )
        elements.append(table)
        doc.build(elements)

        return response
    else:
        return HttpResponse("Unsupported format", status=400)

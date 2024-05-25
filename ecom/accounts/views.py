import re
import json
import random
import pdfkit
from .models import *
from cart_app.models import *
from admin_app.models import *
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.dispatch import receiver
from django.core.mail import send_mail
from datetime import datetime, timedelta
from django.contrib import messages, auth
from ecom.settings import EMAIL_HOST_USER
from django.db.models import Q, FloatField
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.db.models.signals import post_save
from django.core.validators import validate_email
from validate_email_address import validate_email
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.db.models import F, ExpressionWrapper, DecimalField
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, login, logout,get_backends
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


PRODUCT_PER_PAGE = 9


@csrf_exempt
def validate_register(request):
    field_name = request.POST.get('field_name')
    field_value = request.POST.get('field_value')
    response = {'valid': True, 'error': ''}

    try:
        if field_name in ['f_name', 'l_name']:
            if not field_value.isalpha():
                raise ValidationError('Name must contain only letters')
            elif len(field_value) < 2:
                raise ValidationError('Name must be at least 2 characters long')
        
        if field_name == 'username':
            if User.objects.filter(username=field_value).exists():
                raise ValidationError('The username is already taken')
            if not field_value.strip():
                raise ValidationError('The username is not valid')

        elif field_name == 'email':
            if User.objects.filter(email=field_value).exists():
                raise ValidationError('This email is already registered')
            if not re.match(r"^[\w\.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", field_value):
                raise ValidationError('Please enter a valid email address')

        elif field_name == 'pass1':
            validate_password(field_value, user=User)
            if len(field_value) < 6:
                raise ValidationError('The password should be at least 6 characters')
            if not any(char.isupper() for char in field_value):
                raise ValidationError('Password must contain at least one uppercase letter')
            if not any(char.islower() for char in field_value):
                raise ValidationError('Password must contain at least one lowercase letter')
            if not any(char.isdigit() for char in field_value):
                raise ValidationError('Password must contain at least one digit')

    except ValidationError as e:
        response['valid'] = False
        response['error'] = ', '.join(e.messages)

    return JsonResponse(response)

@never_cache
def register(request):
    try:
        if request.user.is_authenticated:
            return redirect("index")

        referral_code = request.GET.get("ref")

        if request.method == "POST":
            first_name = request.POST.get("f_name")
            last_name = request.POST.get("l_name")
            username = request.POST.get("username")
            email = request.POST.get("email")
            password1 = request.POST.get("pass1")
            password2 = request.POST.get("pass2")
            referral_code_manual = request.POST.get("referral_code")

            if referral_code_manual:
                referral_code = referral_code_manual

            if referral_code:
                if not Customer.objects.filter(referral_code=referral_code).exists():
                    return JsonResponse({'success': False, 'message': 'Invalid Referral Code'})
                else:
                    request.session["referral_code"] = referral_code

            if not all([first_name, last_name, username, email, password1, password2]):
                return JsonResponse({'success': False, 'message': 'Please fill up all the fields.'})

            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'message': 'The username is already taken'})

            if len(password1) < 6:
                return JsonResponse({'success': False, 'message': 'The password should be at least 6 characters'})

            if password1 != password2:
                return JsonResponse({'success': False, 'message': 'The passwords do not match'})

            if not first_name.isalpha():
                return JsonResponse({'success': False, 'message': 'First name must contain only letters'})

            if not last_name.isalpha():
                return JsonResponse({'success': False, 'message': 'Last name must contain only letters'})

            try:
                validate_password(password1, user=User)
            except ValidationError as e:
                return JsonResponse({'success': False, 'message': str(e)})

            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'This email is already registered'})

            with transaction.atomic():
                user = User.objects.create_user(
                    first_name=first_name, 
                    last_name=last_name, 
                    username=username, 
                    email=email, 
                    password=password1
                )
                user.save()

                user_profile = User_profile.objects.create(user=user, is_verified=False)
                user_profile.user.is_active = False
                user_profile.save()
                user_id = user_profile.user.pk 
                otp = generate_otp()
                otp_generated_at = timezone.now().isoformat()
                print(otp, otp_generated_at)
                send_otp_email(email, otp)
                store_user_data_in_session(request, user_id, otp, otp_generated_at)

            return JsonResponse({'success': True, 'message': f'Welcome {first_name}'})
        else:
            form_data = request.session.get("form_data", {})
            return render(request, "register.html", {"form_data": form_data})

    except ValidationError as e:
        return JsonResponse({'success': False, 'message': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def generate_otp():
    return random.randint(1000, 9999)

def send_otp_email(email, otp):
    send_mail(
        subject="Your OTP for verification",
        message=f"Your OTP for verification is: {otp}",
        from_email=EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=True,
    )

def store_user_data_in_session(request, user_id, otp, otp_generated_at):
    request.session["user_data"] = {
        "user_id": user_id,
        "otp": otp,
        "otp_generated_at": otp_generated_at,
    }



@never_cache
def otp(request):
    try:
        if request.user.is_authenticated:
            return redirect("index")

        email = request.session.get("user_data", {}).get("email", "")
        if request.method == "POST":
            otp_digits = [request.POST.get(f"digit{i}") for i in range(1, 5)]
            if None in otp_digits:
                messages.error(request, "Invalid OTP format, please try again.")
                return redirect("my_otp")

            entered_otp = int("".join(otp_digits))
            stored_otp = request.session.get("user_data", {}).get("otp")
            user_data = request.session.get("user_data", {})
            otp_generated_at = user_data.get("otp_generated_at", "")
            user_id = user_data.get("user_id", "")
            print(f"this is user id {user_id}")
            referral_code = request.session.get("referral_code", "")

            try:
                otp_generated_at_datetime = datetime.fromisoformat(otp_generated_at)
            except ValueError:
                otp_generated_at_datetime = None

            if otp_generated_at_datetime and otp_generated_at_datetime + timedelta(minutes=5) < timezone.now():
                messages.error(request, "OTP has expired. Please try again.")
                return redirect("register")

            if str(entered_otp) == str(stored_otp):
                user = User.objects.get(id=user_id)
                user_profile = User_profile.objects.get(user=user)
                user_profile.is_verified = True
                user_profile.user.is_active = True
                user_profile.save()

                del request.session["user_data"]
                
                
                backend = get_backends()[0]
                user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

                # Referral code handling
                if referral_code:
                    referred_customer = Customer.objects.get(referral_code=referral_code)
                    referred_customer.referral_count += 1
                    referred_customer.save()

                    referred_customer_user = referred_customer.user
                    referred_customer_credit, created = Wallet.objects.get_or_create(user=referred_customer_user)
                    referred_customer_credit.balance += 100
                    referred_customer_credit.referral_deposit += 100
                    referred_customer_credit.save()

                    referred_transaction_id = "REFERRAL_" + get_random_string(4, "MOZ0123456789")
                    while Wallet_transaction.objects.filter(transaction_id=referred_transaction_id).exists():
                        referred_transaction_id = "REFERRAL_" + get_random_string(4, "MOZ0123456789")

                    Wallet_transaction.objects.create(
                        wallet=referred_customer_credit,
                        transaction_id=referred_transaction_id,
                        money_deposit=100,
                    )

                    customer = Customer.objects.get(user=user)
                    customer.referred_person = referred_customer_user.username
                    customer.save()

                    referring_customer_credit, created = Wallet.objects.get_or_create(user=customer.user)
                    referring_customer_credit.balance += 50
                    referring_customer_credit.referral_deposit += 50
                    referring_customer_credit.save()

                    referring_transaction_id = "REFERRAL_" + get_random_string(4, "MOZ0123456789")
                    while Wallet_transaction.objects.filter(transaction_id=referring_transaction_id).exists():
                        referring_transaction_id = "REFERRAL_" + get_random_string(4, "MOZ0123456789")

                    Wallet_transaction.objects.create(
                        wallet=referring_customer_credit,
                        transaction_id=referring_transaction_id,
                        money_deposit=50,
                    )

                    messages.success(request, f"{user.username} created successfully.")
                    login(request, user)
                    return redirect("index")

                messages.success(request, f"{user.username} created successfully.")
                login(request, user)
                return redirect("index")
            else:
                messages.error(request, "Invalid OTP, try again.")
                return redirect("my_otp")

        return render(request, "otp.html", {"email": email})

    except Exception as e:
        messages.error(request, str(e))
        return redirect("register")
    
    
    

def generate_otp_and_send_email(email):
    otp = random.randint(1000, 9999)
    otp_generated_at = timezone.now().isoformat()

    send_mail(
        subject="Your OTP for verification",
        message=f"Your OTP for verification is: {otp}",
        from_email=EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=True,
    )
    return otp, otp_generated_at


@never_cache
def resend_otp(request):
    try:
        user_data = request.session.get("user_data", {})
        email = user_data.get("email", "")
        user_id = user_data.get("user_id", "")

        if not user_id or not isinstance(user_id, int):
            messages.error(request, "Invalid session data. Please register again.")
            return redirect("register")

        new_otp, otp_generated_now = generate_otp_and_send_email(email)
        user_data["otp"] = new_otp
        print(f"this is new otp {new_otp}")
        user_data["otp_generated_at"] = otp_generated_now
        request.session["user_data"] = user_data

        messages.success(request, "New OTP sent successfully")
        return redirect("my_otp")

    except Exception as e:
        messages.error(request, str(e))
        return redirect("my_otp")



@never_cache
def log_in(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect("index")
        else:
            messages.error(request, "The username or password is incorrect.")
            return redirect("login")

    return render(request, "log.html")


@never_cache
def verify_email(request):
    try:
        if request.user.is_authenticated:
            return redirect("index")

        if request.method == "POST":
            email = request.POST.get("email")

            if User.objects.filter(email=email).exists():
                otp, otp_generated_at = generate_otp_and_send_email(email)
                request.session["verifyotp"] = {
                    "otp": otp,
                    "email": email,
                    "otp_generated_at": otp_generated_at,
                }
                return redirect("verify_otp")
            else:
                messages.error(request, "Something went wrong")
                return redirect("verify_email")

    except Exception as e:
        messages.error(request, str(e))
    return render(request, "pass_reset/verify_email.html")


@never_cache
def verify_otp(request):
    try:
        email = request.session.get("verifyotp", {}).get("email", "")

        if request.method == "POST":
            otp_digits = [request.POST.get(f"otp{i}") for i in range(1, 5)]

            if None in otp_digits:
                messages.error(request, "Invalid OTP format, please try again.")
                return redirect("verify_email")

            entered_otp = int("".join(otp_digits))
            storedotp = request.session.get("verifyotp", {}).get("otp")
            user_data = request.session.get("user_data", {})
            otp_generated_at_str = request.session.get("verifyotp", {}).get(
                "otp_generated_at", ""
            )

            try:
                otp_generated_at_datetime = datetime.fromisoformat(otp_generated_at_str)
            except ValueError:
                otp_generated_at_datetime = None

            if (
                otp_generated_at_datetime
                and otp_generated_at_datetime + timedelta(minutes=2) < timezone.now()
            ):
                messages.error(request, "OTP has expired. Please try again.")
                return redirect("verify_email")

            if str(entered_otp) == str(storedotp):
                return redirect("reset_pass")

            else:
                messages.error(request, "Incorrect OTP, please try again.")
                return redirect("verify_otp")

        return render(request, "pass_reset/verify_otp.html", {"email": email})

    except Exception as e:
        messages.error(request, str(e))
        return redirect("verify_otp")


@never_cache
def reset_pass(request):
    email = request.session.get("verifyotp", {}).get("email", "")

    if request.method == "POST":
        new_password = request.POST.get("newpassword")
        confirm_password = request.POST.get("confirmpassword")

        if new_password != confirm_password:
            messages.error(request, "The passwords do not match")
            return redirect("reset_pass")

        try:
            validate_password(new_password)
        except ValidationError as e:
            messages.error(request, ", ".join(e))
            return redirect("reset_pass")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User does not exist")
            return redirect("reset_pass")

        user = User.objects.get(email=email)
        user.set_password(confirm_password)
        user.save()

        del request.session["verifyotp"]

        messages.success(request, "Password reset successfully")
        return redirect("login")

    return render(request, "pass_reset/reset_pass.html")


@never_cache
def log_out(request):
    logout(request)
    return redirect("index")


@never_cache
def index(request):
    banners = Banner.objects.filter(is_listed=True).order_by("-id")
    products_color = ProductColorImage.objects.filter(product__is_deleted=False)
    products = Product.objects.filter(is_listed=True)
    context = {
        "products_color": products_color,
        "products": products,
        "banners": banners,
    }
    if request.user.is_authenticated:
        banners = Banner.objects.filter(is_listed=True).order_by("-id")
        products_color = ProductColorImage.objects.filter(product__is_deleted=False)
        products = Product.objects.filter(is_listed=True)
        context = {
            "products_color": products_color,
            "products": products,
            "banners": banners,
        }
        return render(request, "index.html", context)
    return render(request, "index.html", context)


@never_cache
def product_detail(request, product_id):
    products_color = ProductColorImage.objects.get(id=product_id)
    product_category = products_color.product.category
    related_product = ProductColorImage.objects.filter(
        Q(product__category=product_category) & Q(is_listed=True)
    ).exclude(id=product_id)

    context = {"products_color": products_color, "related_product": related_product}
    return render(request, "product_detail.html", context)


@never_cache
def mens_page(request):
    ordering = request.GET.get("ordering", "name")
    products_color = ProductColorImage.objects.filter(
        Q(product__category__name="Men's")
        & Q(product__category__is_deleted=False)
        & Q(is_deleted=False)
    )

    # Filter by price range
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price is not None:
        min_price = int(min_price)
    if max_price is not None:
        max_price = int(max_price)

    if min_price is not None and max_price is not None:
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price")
                - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField(),
            )
        ).filter(
            calculated_offer_price__gte=min_price, calculated_offer_price__lte=max_price
        )

    # Filter by category
    categories_filter = request.GET.getlist("category")
    if categories_filter:
        products_color = products_color.filter(
            product__category__name__in=categories_filter
        )

    # Order products
    if ordering == "name":
        products_color = products_color.order_by("product__name")
    elif ordering == "-name":
        products_color = products_color.order_by("-product__name")
    elif ordering == "price":
        products_color = sorted(products_color, key=lambda x: x.product.offer_price)
    elif ordering == "-price":
        products_color = sorted(
            products_color, key=lambda x: x.product.offer_price, reverse=True
        )
    elif ordering == "created_at":
        products_color = products_color.order_by("product__created_at")

    # Paginate products
    page = request.GET.get("page", 1)
    product_paginator = Paginator(products_color, PRODUCT_PER_PAGE)

    try:
        products = product_paginator.page(page)
    except PageNotAnInteger:
        products = product_paginator.page(1)
    except EmptyPage:
        products = product_paginator.page(product_paginator.num_pages)

    # Retrieve categories
    categories = Category.objects.filter(is_listed=True, is_deleted=False)

    context = {
        "products_color": products,
        "categories": categories,
        "page_obj": products,
        "is_paginated": product_paginator.num_pages > 1,
        "paginator": product_paginator,
    }
    return render(request, "mens.html", context)


@never_cache
def womens_page(request):
    ordering = request.GET.get("ordering", "name")
    products_color = ProductColorImage.objects.filter(
        Q(product__category__name="Women's")
        & Q(product__category__is_deleted=False)
        & Q(is_deleted=False)
    )

    # Filter by price range
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price is not None:
        min_price = int(min_price)
    if max_price is not None:
        max_price = int(max_price)

    if min_price is not None and max_price is not None:
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price")
                - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField(),
            )
        ).filter(
            calculated_offer_price__gte=min_price, calculated_offer_price__lte=max_price
        )

    # Filter by category
    categories_filter = request.GET.getlist("category")
    if categories_filter:
        products_color = products_color.filter(
            product__category__name__in=categories_filter
        )

    # Order products
    if ordering == "name":
        products_color = products_color.order_by("product__name")
    elif ordering == "-name":
        products_color = products_color.order_by("-product__name")
    elif ordering == "price":
        products_color = sorted(products_color, key=lambda x: x.product.offer_price)
    elif ordering == "-price":
        products_color = sorted(
            products_color, key=lambda x: x.product.offer_price, reverse=True
        )
    elif ordering == "created_at":
        products_color = products_color.order_by("product__created_at")

    # Paginate products
    page = request.GET.get("page", 1)
    product_paginator = Paginator(products_color, PRODUCT_PER_PAGE)

    try:
        products = product_paginator.page(page)
    except PageNotAnInteger:
        products = product_paginator.page(1)
    except EmptyPage:
        products = product_paginator.page(product_paginator.num_pages)

    # Retrieve categories
    categories = Category.objects.filter(is_listed=True, is_deleted=False)

    context = {
        "products_color": products,
        "categories": categories,
        "page_obj": products,
        "is_paginated": product_paginator.num_pages > 1,
        "paginator": product_paginator,
    }
    return render(request, "womens.html", context)


@never_cache
def kids_page(request):
    ordering = request.GET.get("ordering", "name")
    products_color = ProductColorImage.objects.filter(
        Q(product__category__name="Kid's")
        & Q(product__category__is_deleted=False)
        & Q(is_deleted=False)
    )

    # Filter by price range
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price is not None:
        min_price = int(min_price)
    if max_price is not None:
        max_price = int(max_price)

    if min_price is not None and max_price is not None:
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price")
                - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField(),
            )
        ).filter(
            calculated_offer_price__gte=min_price, calculated_offer_price__lte=max_price
        )

    # Filter by category
    categories_filter = request.GET.getlist("category")
    if categories_filter:
        products_color = products_color.filter(
            product__category__name__in=categories_filter
        )

    # Order products
    if ordering == "name":
        products_color = products_color.order_by("product__name")
    elif ordering == "-name":
        products_color = products_color.order_by("-product__name")
    elif ordering == "price":
        products_color = sorted(products_color, key=lambda x: x.product.offer_price)
    elif ordering == "-price":
        products_color = sorted(
            products_color, key=lambda x: x.product.offer_price, reverse=True
        )
    elif ordering == "created_at":
        products_color = products_color.order_by("product__created_at")

    # Paginate products
    page = request.GET.get("page", 1)
    product_paginator = Paginator(products_color, PRODUCT_PER_PAGE)

    try:
        products = product_paginator.page(page)
    except PageNotAnInteger:
        products = product_paginator.page(1)
    except EmptyPage:
        products = product_paginator.page(product_paginator.num_pages)

    # Retrieve categories
    categories = Category.objects.filter(is_listed=True, is_deleted=False)

    context = {
        "products_color": products,
        "categories": categories,
        "page_obj": products,
        "is_paginated": product_paginator.num_pages > 1,
        "paginator": product_paginator,
    }
    return render(request, "kids.html", context)


@never_cache
def shop_page(request):
    ordering = request.GET.get("ordering", "name")
    products_color = ProductColorImage.objects.filter(is_listed=True, is_deleted=False)
    colors = ProductColorImage.objects.filter(
        is_listed=True, is_deleted=False
    ).distinct("color")
    brands = Brand.objects.filter(is_listed=True)

    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price is not None:
        min_price = int(min_price)
    if max_price is not None:
        max_price = int(max_price)

    if min_price is not None and max_price is not None:
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F("product__price")
                - (F("product__price") * F("product__percentage") / 100),
                output_field=DecimalField(),
            )
        ).filter(
            calculated_offer_price__gte=min_price, calculated_offer_price__lte=max_price
        )

    categories_filter = request.GET.getlist("category")
    if categories_filter:
        category_filters = Q()
        for category in categories_filter:
            category_filters |= Q(product__category__name=category)
        products_color = products_color.filter(category_filters)
        
    

    if ordering == "name":
        products_color = products_color.order_by("product__name")
    elif ordering == "-name":
        products_color = products_color.order_by("-product__name")
    elif ordering == "price":
        products_color = sorted(products_color, key=lambda x: x.product.offer_price)
    elif ordering == "-price":
        products_color = sorted(
            products_color, key=lambda x: x.product.offer_price, reverse=True
        )
    elif ordering == "created_at":
        products_color = products_color.order_by("product__created_at")

    page = request.GET.get("page", 1)
    product_Paginator = Paginator(products_color, PRODUCT_PER_PAGE)

    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)

    categories = Category.objects.filter(is_listed=True, is_deleted=False)

    context = {
        "products_color": products,
        "categories": categories,
        "page_obj": products,
        "is_paginated": product_Paginator.num_pages > 1,
        "paginator": product_Paginator,
        "brands": brands,
        "colors": colors,
    }
    return render(request, "shop.html", context)


# ___________________________________________________________________________________________________________________________________________________


def search_pro(request):
    try:
        if request.method == "POST":
            query = request.POST.get("query")
            products_color = ProductColorImage.objects.filter(
                product__is_deleted=False, product__name__icontains=query
            )

            context = {"products_color": products_color, "query": query}
            return render(request, "filter/search.html", context)
    except Exception as e:
        messages.error(request, "Something went wrong please try again.")
        return redirect("index")


@never_cache
def filtered_products_cat(request):
    print("Filtered products by category, brand, and color")
    print("Request:", request)
    selected_category_ids = request.GET.getlist("category")
    selected_brand_ids = request.GET.getlist("brand")
    selected_color_ids = request.GET.getlist("color")

    print("Selected category:", selected_category_ids)
    print("Selected brand:", selected_brand_ids)
    print("Selected color:", selected_color_ids)

    categories = Category.objects.filter(is_listed=True)
    brands = Brand.objects.filter(is_listed=True)
    colors = ProductColorImage.objects.filter(
        is_deleted=False, is_listed=True
    ).distinct("color")

    products = ProductColorImage.objects.filter(
        Q(product__category__in=selected_category_ids)
        | Q(product__brand__in=selected_brand_ids)
        | Q(color__in=selected_color_ids)
    ).distinct()
    
    if selected_category_ids and selected_color_ids:
        products = ProductColorImage.objects.filter(
            Q(product__category__in=selected_category_ids)
            & Q(color__in=selected_color_ids)
        ).distinct()
    if selected_category_ids and selected_brand_ids:
        products = ProductColorImage.objects.filter(
            Q(product__category__in=selected_category_ids)
            & Q(product__brand__in=selected_brand_ids)
        ).distinct()
    if selected_brand_ids and selected_color_ids and selected_category_ids:
        products = ProductColorImage.objects.filter(
            Q(product__category__in=selected_category_ids)
            & Q(product__brand__in=selected_brand_ids)
            & Q(color__in=selected_color_ids)
        ).distinct()
        

    selected_category_ids = [int(category_id) for category_id in selected_category_ids]
    selected_brand_ids = [int(brand_id) for brand_id in selected_brand_ids]
    selected_color_ids = [color for color in selected_color_ids]

    print("Products:", products)

    context = {
        "categories": categories,
        "brands": brands,
        "colors": colors,
        "products_color": products,
        "selected_category": selected_category_ids,
        "selected_brand": selected_brand_ids,
        "selected_color": selected_color_ids,
    }
    return render(request, "shop.html", context)


@never_cache
def filter_products_by_price(request):
    try:
        if request.method == "GET":
            min_price = request.GET.get("min", 500)[1:]
            max_price = request.GET.get("max", 50000)[1:]

            print("Minimum price:", min_price)
            print("Maximum price:", max_price)

            product_color_images = ProductColorImage.objects.filter(
                product__is_listed=True, product__is_deleted=False
            )
            categories = Category.objects.filter(is_listed=True)
            brands = Brand.objects.filter(is_listed=True)
            colors = ProductColorImage.objects.filter(
                is_deleted=False, is_listed=True
            ).distinct("color")

            # Annotate the queryset with the offer price
            product_color_images = product_color_images.annotate(
                calculated_offer_price=ExpressionWrapper(
                    F("product__price")
                    - (F("product__percentage") * F("product__price") / 100),
                    output_field=FloatField(),
                )
            )

            # Filter product color images based on the offer price
            if min_price is not None:
                product_color_images = product_color_images.filter(
                    calculated_offer_price__gte=min_price
                )
            if max_price is not None:
                product_color_images = product_color_images.filter(
                    calculated_offer_price__lte=max_price
                )

                print("Filtered products:", product_color_images)
            context = {
                "products_color": product_color_images,
                "categories": categories,
                "brands": brands,
                "colors": colors,
            }
            return render(request, "shop.html", context)
    except Exception as e:
        print("Exception:", e)
        messages.error(request, "Something went wrong please try again.")
        return redirect("index")


# _____________________________________________________________________________________________________________________________________________________________


def profile(request):
    if request.user.is_authenticated:
        user = request.user
        customer = Customer.objects.get(user=user.id)
        context = {"user": user, "customer": customer}
        return render(request, "personal_info.html", context)

    else:
        return redirect("login")


def edit_profile(request, info_id):
    if request.user.is_authenticated:
        user = request.user
        try:
            customer = Customer.objects.get(id=info_id)
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
            return redirect("profile")

        if request.method == "POST":
            try:
                first_name = request.POST.get("first_name")
                last_name = request.POST.get("last_name")
                email = request.POST.get("email")
                dob = request.POST.get("dob")
                gender = request.POST.get("gender")
                phone_number = request.POST.get("phone_number")

                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    messages.error(request, "Email already in use.")
                    return redirect("edit_profile", info_id=customer.id)

                dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
                today = timezone.now().date()
                age = (
                    today.year
                    - dob_date.year
                    - ((today.month, today.day) < (dob_date.month, dob_date.day))
                )

                if age < 18:
                    messages.error(
                        request,
                        "You must be at least 18 years old to update your profile.",
                    )
                    return redirect("edit_profile", info_id=customer.id)

                if not phone_number or len(phone_number) < 10:
                    messages.error(request, "Invalid mobile number.")
                    return redirect("edit_profile", info_id=customer.id)

                customer.user.first_name = first_name
                customer.user.last_name = last_name
                customer.user.email = email
                customer.dob = dob
                customer.gender = gender
                customer.phone_number = phone_number
                customer.user.save()
                customer.save()

                messages.success(request, "Profile updated successfully.")
                return redirect(profile)
            except Exception as e:
                messages.error(
                    request, "An error occurred while updating your profile."
                )
                return redirect("edit_profile", info_id=customer.id)

        context = {"user": user, "customer": customer}
        return render(request, "edit_personalinfo.html", context)


def change_password(request, pass_id):
    if request.user.is_authenticated:
        user = User.objects.get(id=pass_id)
        if request.method == "POST":
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not check_password(current_password, user.password):
                messages.error(request, "Current password is incorrect.")
                return redirect("change_password", pass_id=user.id)

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect("change_password", pass_id=user.id)
            if len(new_password) < 8:
                messages.error(
                    request, "New password must be at least 8 characters long."
                )
                return redirect("change_password", pass_id=user.id)

            user.set_password(new_password)
            user.save()
            messages.success(request, "Your password was successfully updated!")
            return redirect("profile")
        context = {"user": user, "customer": Customer.objects.get(user=user)}
    return render(request, "personal_info.html", context)


def address(request):
    try:
        if request.user.is_authenticated:
            address = Address.objects.filter(user=request.user.pk, is_deleted = False)
            next_page = request.GET.get("next", "")
            context = {"address": address, "next_page": next_page}
            return render(request, "address.html", context)
        else:
            return redirect("login")
    except:
        return render(request, "address.html")


def add_address(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            user = User.objects.get(pk=request.user.pk)
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            city = request.POST.get("city")
            state = request.POST.get("state")
            country = request.POST.get("country")
            postal_code = request.POST.get("postal_code")
            house_name = request.POST.get("house_name")
            mobile_number = request.POST.get("mobile_number")

            if not all(
                [
                    first_name,
                    last_name,
                    email,
                    city,
                    state,
                    country,
                    postal_code,
                    house_name,
                    mobile_number,
                ]
            ):
                messages.error(request, "Please fill up all the fields.")
                return redirect("add_address")

            # Name validation: only letters and single spaces between words
            name_pattern = r"^[a-zA-Z]+(?:\s[a-zA-Z]+)*$"
            if not re.match(name_pattern, first_name):
                messages.error(
                    request, "First name must contain only letters and single spaces."
                )
                return redirect("add_address")

            if not re.match(name_pattern, last_name):
                messages.error(
                    request, "Last name must contain only letters and single spaces."
                )
                return redirect("add_address")

            # Mobile number length validation
            if len(mobile_number) < 10 or len(mobile_number) > 12:
                messages.error(request, "Mobile number is not valid.")
                return redirect("add_address")

            location_pattern = r"^[a-zA-Z\s]+$"
            if not re.match(location_pattern, city):
                messages.error(
                    request, "City name must contain only letters and spaces."
                )
                return redirect("add_address")

            if not re.match(location_pattern, state):
                messages.error(
                    request, "State name must contain only letters and spaces."
                )
                return redirect("add_address")

            if not re.match(location_pattern, country):
                messages.error(
                    request, "Country name must contain only letters and spaces."
                )
                return redirect("add_address")

            if not re.match(location_pattern, house_name):
                messages.error(
                    request, "House name must contain only letters and spaces."
                )
                return redirect("add_address")

            # Postal code validation: only digits
            if not postal_code.isdigit():
                messages.error(request, "Postal code must contain only digits.")
                return redirect("add_address")
            address = Address.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                city=city,
                state=state,
                country=country,
                postal_code=postal_code,
                house_name=house_name,
                phone_number=mobile_number,
            )
            messages.success(request, "user address created successfully.")
            return redirect("address")
    return render(request, "add_address.html")


def edit_address(request, address_id):
    if request.user.is_authenticated:
        user = request.user
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            messages.error(request, "Address not found.")
            return redirect("address")

        context = {"address": address, "user": user}
        if request.method == "POST":
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            city = request.POST.get("city")
            state = request.POST.get("state")
            country = request.POST.get("country")
            postal_code = request.POST.get("postal_code")
            house_name = request.POST.get("house_name")
            mobile_number = request.POST.get("mobile_number")

            if not all(
                [
                    first_name,
                    last_name,
                    city,
                    email,
                    state,
                    country,
                    postal_code,
                    house_name,
                    mobile_number,
                ]
            ):
                messages.error(request, "Please fill up all the fields.")
                return redirect("edit_address")
            if len(mobile_number) < 10 and len(mobile_number) > 12:
                messages.error(request, "Moblie number is not valid.")
                return redirect("edit_address")

            address.first_name = first_name
            address.last_name = last_name
            address.email = email
            address.city = city
            address.state = state
            address.country = country
            address.postal_code = postal_code
            address.house_name = house_name
            address.phone_number = mobile_number
            address.save()

            messages.success(request, "Address updated successfully.")
            return redirect("address")
    return render(request, "edit_address.html", context)


def delete_address(request, address_id):
    # try:
    if request.user.is_authenticated:
        data = Address.objects.get(id=address_id)
        data.is_deleted = True
        data.save()
        messages.success(request, "Address deleted successfully.")
        return redirect("address")
    else:
        return redirect("login")


# except:
#     return redirect("address")


# _______________________________________________X_________________________X__________________________


# _____________________________________________________________________________________________________________________


def wallet_view(request):
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        wallet_transactions = Wallet_transaction.objects.filter(wallet=wallet).order_by(
            "-transaction_time"
        )
        context = {"wallet": wallet, "wallet_transactions": wallet_transactions}
        return render(request, "wallet.html", context)
    else:
        return redirect("login")


def invoice(request, product_id):
    if request.user.is_authenticated:
        user = Customer.objects.get(user=request.user)
        order_items = OrderItem.objects.get(id=product_id, order__customer=user)
        total = order_items.product.product.offer_price * order_items.qty
        context = {"order_items": order_items, "total": total}
        html_string = render_to_string("invoice.html", context)

        # Define the configuration for pdfkit
        config = pdfkit.configuration(
            wkhtmltopdf="C:\\Users\\DELL\\OneDrive\\Desktop\\Python\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
        )

        pdf = pdfkit.from_string(html_string, False, configuration=config)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'filename="invoice.pdf"'

        return response
    else:
        return redirect("login")


def referral(request):
    if request.user.is_authenticated:
        user = request.user
        customer = Customer.objects.get(user=user)
        referral_code = customer.referral_code
        amount = customer.referral_count * 100
        sign_up_url = reverse("register")

        referral_link = request.build_absolute_uri(
            sign_up_url + f"?ref={referral_code}"
        )
        return render(
            request,
            "referral.html",
            {"customer": customer, "amount": amount, "referral_link": referral_link},
        )
    else:
        return redirect("login")

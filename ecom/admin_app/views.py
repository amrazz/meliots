from PIL import Image
from django.http import HttpResponseRedirect
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
from django.urls import reverse
from cart_app.models import *
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, F, Count
from django.utils.crypto import get_random_string
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from io import BytesIO
import xlsxwriter
from django.utils import timezone
from .forms import CategoryOfferForm, BannerForm
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.db.models.functions import TruncDate


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
    if request.user.is_superuser:
        month = request.GET.get("month")
        if month:
            year, month = map(int, month.split("-"))
            ordered_items = OrderItem.objects.filter(
                status="Delivered", created_at__year=year, created_at__month=month
            )
        else:
            ordered_items = OrderItem.objects.filter(status="Delivered")

        delivered_orders_per_day = (
            ordered_items.annotate(delivery_date=TruncDate("created_at"))
            .values("delivery_date")
            .annotate(total_orders=Count("id"))
            .order_by("delivery_date")
        )

        delivery_data = list(
            delivered_orders_per_day.values("delivery_date", "total_orders")
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            response_data = {
                "labels": [
                    item["delivery_date"].strftime("%Y-%m-%d") for item in delivery_data
                ],
                "data": [item["total_orders"] for item in delivery_data],
            }
            return JsonResponse(response_data)

        best_seller = (
            ProductColorImage.objects.filter(
                is_deleted=False,
                product_order__in=ordered_items,
            )
            .annotate(order_count=Count("product_order"))
            .order_by("-order_count")
        )
        top_10_products = best_seller.distinct()[:10]

        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2024-12-31", "%Y-%m-%d")
        orders_per_year = OrderItem.objects.filter(
            status="Delivered", created_at__range=(start_date, end_date)
        )
        orders_per_month = OrderItem.objects.filter(
            status="Delivered", created_at__range=("2024-05-01", "2024-05-31")
        )
        total_sum_per_year = orders_per_year.aggregate(total_price=Sum("order__total"))[
            "total_price"
        ]
        total_sum_per_month = orders_per_month.aggregate(
            total_price=Sum("order__total")
        )["total_price"]

        top_3_category = (
            Product.objects.filter(
                color_image__in=top_10_products,
                is_deleted=False,
                color_image__product_order__in=ordered_items,
            )
            .values("category__name", "category__cat_image")
            .annotate(category_count=Count("category"))
            .order_by("-category_count")[:3]
        )

        category_count = [item["category_count"] for item in top_3_category]
        category_sum = sum(category_count)
        top_5_brand = (
            best_seller.values("product__brand__name")
            .annotate(brand_count=Count("product__brand__id"))
            .order_by("-brand_count")
            .distinct()[:5]
        )
        brand_count = top_5_brand.count()
        brand_sum = sum(brand_count for brand in top_5_brand)

        context = {
            "delivered_orders_per_day": delivery_data,
            "total_sum_per_month": total_sum_per_month,
            "top_10_products": top_10_products,
            "top_3_category": top_3_category,
            "total_sum": total_sum_per_year,
            "category_count": category_count,
            "category_sum": category_sum,
            "top_5_brand": top_5_brand,
            "brand_count": brand_count,
            "brand_sum": brand_sum,
        }
        return render(request, "dashboard.html", context)
    else:
        messages.error(request, "Only admins are allowed.")
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
            users = User.objects.all().order_by("-id")
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

            if not name.strip():
                messages.error(request, "Name cannot be empty.")
                return redirect("add_category")
            elif len(description) < 10:
                messages.error(
                    request, "Description must be at least 10 characters long."
                )
                return redirect("add_category")
            elif not all([name, description, image]):
                messages.error(request, "All fields are required.")
                return redirect("add_category")
            elif Category.objects.filter(name=name).exists():
                messages.error(request, "Category with this name already exists.")
                return redirect("add_category")
            else:
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
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_category", cat_id=cat_id)
                if len(description) < 10:
                    messages.error(
                        request, "Description must be at least 10 characters long."
                    )
                    return redirect("edit_category", cat_id=cat_id)

                elif not all([name, description]):
                    messages.error(request, "Name and description are required.")
                    return redirect("edit_category", cat_id=cat_id)
                elif Category.objects.filter(name=name).exclude(id=cat_id).exists():
                    messages.error(request, "Category with this name already exists.")
                    return redirect("edit_category", cat_id=cat_id)
                elif not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_category", cat_id=cat_id)

                if image:
                    category.cat_image = image
                    category.save()





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


def banner(request):
    if request.user.is_superuser:
        banner = Banner.objects.all().order_by("-id")
        return render(request, "view_banner.html", {"banner": banner})


def add_banner(request):
    if request.user.is_superuser:
        if request.method == "POST":
            form = BannerForm(request.POST, request.FILES)
            print(form)
            if form.is_valid():
                print(form)
                banner = form.save(commit=False)
                product_color_image = form.cleaned_data["product_color_image"]
                product = product_color_image.product
                if product.percentage < 5:
                    messages.error(
                        request,
                        "The product percentage is less than 5%. Please enter a valid percentage.",
                    )
                    return redirect("add_banner")
                elif not form.cleaned_data["name"].strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("add_banner")
                else:
                    banner.price = product.offer_price
                    banner.save()
                    messages.success(request, "Banner added successfully.")
                    return redirect("banner")
            else:
                messages.error(request, "Form is not valid. Please check the data.")
        else:
            form = BannerForm()
        return render(request, "add_banner.html", {"form": form})


def edit_banner(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            return redirect("banner")
    else:
        form = BannerForm(instance=banner)
    return render(request, "edit_banner.html", {"form": form, "banner": banner})


def delete_banner(request, banner_id):
    if request.user.is_superuser:
        banner = get_object_or_404(Banner, id=banner_id)
        banner.delete()
        return redirect("banner")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def category_offer(request):
    if request.user.is_superuser:
        category_off = CategoryOffer.objects.filter(
            category__is_listed=True, category__is_deleted=False
        )
        return render(
            request, "category/cat_offer.html", {"category_off": category_off}
        )


def add_category_offer(request):
    if request.user.is_superuser:
        form = CategoryOfferForm()

        if request.method == "POST":
            form = CategoryOfferForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data.get("category")
                name = form.cleaned_data.get("offer_name")
                if not name.strip():
                    messages.error(request, "Offer name cannot be empty.")
                    return redirect("add_category_offer")
                discount_percentage = form.cleaned_data.get("discount_percentage")
                is_active = form.cleaned_data.get("is_active")
                end_date = form.cleaned_data.get("end_date")
                print(category, name, discount_percentage, is_active, end_date)
                today = timezone.now().date()
                if not all([category, name, discount_percentage, is_active, end_date]):
                    messages.error(request, "All fields are required.")
                elif discount_percentage < 5 or discount_percentage > 90:
                    messages.error(
                        request, "Discount percentage must be between 5 and 90."
                    )
                elif not Category.objects.filter(name=category).exists():
                    messages.error(request, "Category does not exist.")
                elif str(end_date) < str(today):
                    messages.error(
                        request, "End date must be greater than today's date."
                    )
                elif str(end_date) and str(end_date) == str(today):
                    messages.error(
                        request, "End date must be greater than today's date."
                    )
                elif CategoryOffer.objects.filter(category__name=category).exists():
                    messages.error(
                        request, "Category offer already exists for this category."
                    )
                else:
                    CategoryOffer.objects.create(
                        category=category,
                        offer_name=name,
                        discount_percentage=discount_percentage,
                        is_active=is_active,
                        end_date=end_date,
                    )
                    messages.success(request, "Category offer added successfully.")
                    return redirect("category_offer")

        return render(request, "category/add_cat_offer.html", {"form": form})


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
            next_url = request.GET.get("next", "/")
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
        sizes = ProductSize.objects.filter(productcolor_id=color_image.pk)
        brands = Brand.objects.all()

        if request.method == "POST":
            name = request.POST.get("name")
            category_id = request.POST.get("category")
            type = request.POST.get("type")
            price = request.POST.get("price")
            percentage = request.POST.get("percentage")
            brand = request.POST.get("brand")

            if (
                not name.strip()
                or not type.strip()
                or not price.strip()
                or not percentage.strip()
                or not brand.strip()
            ):
                messages.error(request, "All fields should contain valid data.")
            if int(percentage) < 5 or int(percentage) > 100:
                messages.error(request, "The percentage must be between 5 and 100.")
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

            today = timezone.now()

            if str(exp_date) and str(exp_date) < str(today):
                messages.error(request, "Expiry date cannot be in the past.")
                return redirect(edit_product, product_id)
            elif str(exp_date) and str(exp_date) == str(today):
                messages.error(request, "Expiry date cannot be today.")
                return redirect(edit_product, product_id)

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
            if brand:
                brand = Brand.objects.get(id=brand)

            color_image.product.name = name
            color_image.product.per_expiry_date = exp_date
            color_image.product.description = description
            color_image.product.type = type
            color_image.product.price = price
            color_image.product.percentage = percentage
            color_image.product.category = category
            if brand:
                color_image.product.brand = brand
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

            for size in sizes:
                size_quantity = request.POST.get(size.size)
                if size_quantity is not None:
                    size.quantity = size_quantity
                    size.save()

            messages.success(request, "Product updated successfully.")
            page = request.GET.get("page", 1)
            return HttpResponseRedirect(reverse("product") + "?page=" + str(page))
        else:
            available_sizes = [size.size for size in sizes]
            return render(
                request,
                "product/edit_product.html",
                {
                    "color_image": color_image,
                    "sizes": sizes,
                    "brands": brands,
                    "available_sizes": available_sizes,
                },
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
            brands = Brand.objects.all()
            print(categories, brands)
            if request.method == "POST":
                name = request.POST.get("name")
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("add_product")
                category = request.POST.get("category")
                type = request.POST.get("type")
                if not type.strip():
                    messages.error(request, "Type cannot be empty.")
                    return redirect("add_product")
                price = request.POST.get("price")

                percentage = request.POST.get("percentage")
                exp_date = request.POST.get("exp_date")
                brand = request.POST.get("brand")
<<<<<<< HEAD

=======
>>>>>>> d9813d87f1d478fddffde01cbd39d46a863c6cc9

                description = request.POST.get("description")
                if len(description) < 10:
                    messages.error(
                        request, "Description must be at least 10 characters long."
                    )
                    return redirect("add_product")
                if not all([name, type, price, description]):
                    messages.error(request, "All fields are required.")
                    return redirect("add_product")
                if brand:
                    if not Brand.objects.filter(id=brand).exists():
                        messages.error(request, "Invalid brand.")
                        return redirect("add_product")
                    else:
                        brand = Brand.objects.filter(id=brand).first()
                if Product.objects.filter(name=name).exists():
                    messages.error(request, "Product with this name already exists.")
                    return redirect("add_product")
                try:
                    price = float(price)
                    if price <= 100:
                        raise ValueError
                except ValueError:
                    messages.error(request, "Please enter a valid positive price.")
                    return redirect("add_product")
                try:
                    if percentage:
                        percentage = float(percentage)
                        if percentage < 5:
                            messages.error(request, "Percentage must be at least 5.")
                            return redirect("add_product")
                    else:
                        percentage = 0
                except ValueError:
                    messages.error(request, "Please enter a valid percentage.")
                    return redirect("add_product")

<<<<<<< HEAD

=======
>>>>>>> d9813d87f1d478fddffde01cbd39d46a863c6cc9
                add_product = Product.objects.create(
                    name=name,
                    category_id=category,
                    type=type,
                    price=price,
                    percentage=percentage,
                    description=description,
                )

                if exp_date:
                    add_product.per_expiry_date = exp_date
                add_product.save()
                if brand:
                    add_product.brand = (brand,)
                add_product.save()

                print("product added successfully")
                return redirect("product_image")
            return render(
                request,
                "product/add_product.html",
                {"categories": categories, "brands": brands},
            )
    except Exception as e:
        messages.error(request, str(e))
    return redirect("admin_login")


@never_cache
def product_image(request):
    try:
        if request.user.is_superuser:
            products = Product.objects.all().order_by("id")
            if request.method == "POST":
                product_id = request.POST.get("product")
                color = request.POST.get("color")
                image1 = request.FILES.get("image1")
                image2 = request.FILES.get("image2")
                image3 = request.FILES.get("image3")
                image4 = request.FILES.get("image4")

                if not all([product_id, color, image1, image2, image3, image4]):
                    messages.error(request, "All fields are required.")
                    return redirect("product_image")
                if not color.strip():
                    messages.error(request, "Color cannot be empty.")
                    return redirect("product_image")
                if not color.isalpha():
                    messages.error(request, "Color must contain only letters.")
                    return redirect("product_image")
                if not all(
                    [is_valid_image(img) for img in [image1, image2, image3, image4]]
                ):
                    messages.error(request, "All images must be valid image files.")
                    return redirect("product_image")

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
                print(f"this is the size {size} and quantity {quantity}")
                product_color = get_object_or_404(
                    ProductColorImage, id=product_color_id
                )

                if ProductSize.objects.filter(
                    productcolor=product_color, size=size
                ).exists():
                    messages.error(
                        request,
                        "This size already exists for the selected product color.",
                    )
                    return redirect("product_size")
                if not all([product_color_id, size, quantity]):
                    messages.error(request, "All fields are required.")
                    return redirect("product_size")
                if float(quantity) < 1:
                    messages.error(request, "Quantity must be atleast 1.")
                    return redirect("product_size")
                if size not in ["S", "M", "L"]:
                    messages.error(request, "Size must be S, M or L.")
                    return redirect("product_size")
                if not size.strip():
                    messages.error(request, "Size cannot be empty.")
                    return redirect("product_size")
                product_size = ProductSize.objects.create(
                    productcolor=product_color, size=size, quantity=quantity
                )
                print(f"{product_size} created successfully")

                messages.success(request, "Product size created successfully.")
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


# _____________________________________________________________________________________________________________________________________________________


@never_cache
def view_brand(request):
    if request.user.is_superuser:
        brands = Brand.objects.filter(is_deleted=False, is_listed=True)
        return render(request, "view_brand.html", {"brands": brands})
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def add_brand(request):
    if request.user.is_superuser:
        if request.method == "POST":
            name = request.POST.get("brand_name")
            description = request.POST.get("description")

            if not name:
                messages.error(request, "Brand name is required.")
                return redirect(add_brand)
            if not name.strip():
                messages.error(request, "Brand name cannot contain only spaces.")
                return redirect(add_brand)
            if len(description) < 10:
                messages.error(
                    request, "Description must be at least 10 characters long."
                )
                return redirect(add_brand)
            else:
                create_brand = Brand.objects.create(name=name, description=description)
                messages.success(request, "Brand added successfully.")
                return redirect(view_brand)

        return render(request, "add_brand.html")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


@never_cache
def edit_brand(request, brand_id):
    if request.user.is_superuser:
        brand = get_object_or_404(Brand, id=brand_id)

        if request.method == "POST":
            name = request.POST.get("name")
            description = request.POST.get("description")

            if name:
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_brand", brand_id=brand_id)
                brand.name = name
            if description:
                if len(description) < 10:
                    messages.error(
                        request, "Description must be at least 10 characters long."
                    )
                    return redirect("edit_brand", brand_id=brand_id)
                elif not description.strip():
                    messages.error(request, "Description cannot be empty.")
                    return redirect("edit_brand", brand_id=brand_id)
                brand.description = description
            brand.save()
            messages.success(request, "Brand updated successfully.")
            return redirect("view_brand")

<<<<<<< HEAD
        return render(request, 'edit_brand.html', {"brand": brand})
=======
        return render(request, "edit_brand.html", {"brand": brand})

>>>>>>> d9813d87f1d478fddffde01cbd39d46a863c6cc9

@never_cache
def delete_brand(request, brand_id):
    if request.user.is_superuser:
        brand = get_object_or_404(Brand, id=brand_id)
        brand.is_deleted = True
        brand.save()
        messages.success(request, "Brand deleted successfully.")
        return redirect("view_brand")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


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
        page = request.GET.get("page", 1)
        return HttpResponseRedirect(reverse("product") + "?page=" + str(page))
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
    page = request.GET.get("page", 1)
    return HttpResponseRedirect(reverse("product") + "?page=" + str(page))


@never_cache
def product_is_unlisted(request, product_id):
    product_color = ProductColorImage.objects.get(id=product_id)
    product_color.is_listed = False
    product_color.save()
    page = request.GET.get("page", 1)
    return HttpResponseRedirect(reverse("product") + "?page=" + str(page))


# ____________________________________________________________________________________________________________________________________________________


def order(request):
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")
    search = request.GET.get("search")
    sort_by = request.GET.get("sort_by")
    print(f"{from_date} and {to_date}")
    if request.user.is_superuser:
        if not sort_by:
            sort_by = "-created_at"
        if from_date:
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
            from_date = timezone.make_aware(
                from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        if to_date:
            to_date = datetime.strptime(to_date, "%Y-%m-%d")
            to_date = timezone.make_aware(
                to_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            )

        order_details = Order.objects.all().order_by(sort_by)

        if from_date and to_date:
            order_details = Order.objects.filter(
                created_at__range=[from_date, to_date]
            ).order_by(sort_by)
        elif from_date:
            order_details = Order.objects.filter(created_at__gte=from_date).order_by(
                sort_by
            )
        elif to_date:
            order_details = Order.objects.filter(created_at__lte=to_date).order_by(
                sort_by
            )
        elif search:
            order_details = Order.objects.filter(
                Q(tracking_id__icontains=search) | Q(payment_method__icontains=search)
            ).order_by(sort_by)

        context = {
            "order_details": order_details,
        }
        return render(request, "order/order.html", context)
    else:
        print("Redirecting to admin login")
        return redirect("admin_login")


def admin_order(request, order_id):
    if request.user.is_superuser:
        order = Order.objects.get(id=order_id)
        item = OrderItem.objects.filter(order=order).order_by("id")
        print(item)
        status_choices = dict(OrderItem.STATUS_CHOICES)
        order_address = Shipping_address.objects.get(order=order)

        context = {
            "item": item,
            "order": order,
            "status_choices": status_choices,
            "address": order_address,
        }
        return render(request, "order/order_detail.html", context)
    else:
        return redirect("admin_login")


def update_status(request):
    if request.user.is_superuser and request.method == "POST":
        order_item_id = request.POST.get("order_item_id")
        new_status = request.POST.get("new_status")

        try:
            order_item = OrderItem.objects.get(id=order_item_id)
            previous_status = order_item.status  
            order_item.status = new_status
            order_item.save()

            if new_status == "Cancelled" or new_status == "Returned":
                if previous_status != new_status:
                    product_size = ProductSize.objects.get(
                        productcolor=order_item.product, size=order_item.size
                    )
                    product_size.quantity = F("quantity") + order_item.qty
                    product_size.save()

            return JsonResponse({"status": "success"})
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "message": "Order item not found."})
        except ProductSize.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Product size not found."}
            )

    return JsonResponse(
        {"status": "error", "message": "Unauthorized or invalid request."}
    )


@transaction.atomic
def cancel_order(request, order_id):
    if request.user.is_superuser:
        try:
            print("Starting cancel_order function")
            cancel = OrderItem.objects.get(id=order_id)

            main_order_id = cancel.order.id
            print(cancel)

            if cancel.order.payment_method != "COD" and cancel.order.paid:
                print("Payment method is not COD and order is paid")
                total_discount = cancel.order.discounted_price
                total_quantity = OrderItem.objects.filter(id=order_id).aggregate(
                    total_quantity=Sum("qty")
                )["total_quantity"]
                print(total_quantity)
                discount_per_item = float(total_discount) / float(total_quantity)
                original_price = cancel.product.product.offer_price
                cancelled_amount = (
                    float(original_price) - float(discount_per_item)
                ) * int(cancel.qty)

                user = cancel.order.customer.user
                print(f"this is the uusr {user}")
                wallet, created = Wallet.objects.get_or_create(user=user)
                wallet.balance += float(cancelled_amount)
                wallet.save()

                tranc_id = "CANCEL_" + get_random_string(3, "ABCDEFGHIJKLMOZ0123456789")
                while Wallet_transaction.objects.filter(
                    transaction_id=tranc_id
                ).exists():
                    tranc_id += get_random_string(3, "ABCDEFGHIJKLMOZ0123456789")

                wallet_transaction_create = Wallet_transaction.objects.create(
                    wallet=wallet,
                    order_item=cancel,
                    money_deposit=abs(cancelled_amount),
                    transaction_id=tranc_id,
                )
                if cancel and not cancel.cancel:
                    print("Cancel condition satisfied")
                    cancel.request_cancel = True
                    cancel.status = "Cancelled"
                    cancel.save()
                    messages.success(
                        request,
                        f"Amount of ₹{cancelled_amount} added to {cancel.order.customer.user.username}'s Wallet.",
                    )
                    product_size = ProductSize.objects.get(
                        productcolor=cancel.product, size=cancel.size
                    )
                    product_size.quantity += cancel.qty
                    product_size.save()
                print("Redirecting to admin_order")
                return redirect("admin_order", main_order_id)
            elif cancel.order.payment_method == "COD":
                messages.error(request, "COD orders cannot be cancelled.")
                return redirect("order")
            else:
                print("Order item does not exist or has already been cancelled.")
                messages.info(
                    request, "Order item does not exist or has already been cancelled."
                )
                return redirect("order")

        except OrderItem.DoesNotExist:
            print("Order item does not exist.")
            messages.info(request, "Order item does not exist.")
            return redirect("order")

    else:
        print("User is not superuser")
        return redirect("admin_login")


def return_order(request, return_id):
    if request.user.is_superuser:
        print("Starting return_order function")
        return_order = OrderItem.objects.get(id=return_id)
        ord_id = return_order.order.id
        print("Return order details:", return_order)
        print(return_order.status, return_order.request_return)
        if return_order.request_return == True and return_order.status == "Delivered":

            total_discount = return_order.order.discounted_price
            total_quantity = OrderItem.objects.filter(id=return_id).aggregate(
                total_quantity=Sum("qty")
            )["total_quantity"]
            print("Total quantity:", total_quantity)
            discount_per_item = float(total_discount) / float(total_quantity)
            original_price = return_order.product.product.offer_price
            refund_amount = (float(original_price) - float(discount_per_item)) * int(
                return_order.qty
            )
            print("Refund amount:", refund_amount)

            user = return_order.order.customer.user
            wallet, created = Wallet.objects.get_or_create(user=user)
            wallet.balance += float(refund_amount)
            wallet.save()

            tranc_id = "REFUND_" + get_random_string(3, "ABCLMOZ456789")
            while Wallet_transaction.objects.filter(transaction_id=tranc_id).exists():
                tranc_id += get_random_string(3, "ABCDEFGHIJ456789")
            print("Transaction ID:", tranc_id)

            wallet_transaction_create = Wallet_transaction.objects.create(
                wallet=wallet,
                order_item=return_order,
                money_deposit=abs(refund_amount),
                transaction_id=tranc_id,
            )
            if return_order and not return_order.cancel:
                return_order.return_product = True
                return_order.status = "Returned"
                return_order.request_return = False
                return_order.return_product = True
                return_order.save()
                messages.success(
                    request,
                    f"Amount of ₹{refund_amount} added to {return_order.order.customer.user.username} Wallet.",
                )
                product_size = ProductSize.objects.get(
                    productcolor=return_order.product, size=return_order.size
                )
                product_size.quantity += return_order.qty
                product_size.save()
                print("Order returned successfully")
                return redirect("admin_order", ord_id)
        messages.info(request, "Order has already been returned")
        return redirect("admin_order")
    else:
        print("User is not superuser")
        return redirect("admin_login")


# _________________________________________________________________________________________________


def admin_coupon(request):
    if request.user.is_superuser:
        coupons = Coupon.objects.filter(is_active=True).order_by("id")
        context = {"coupons": coupons}
        return render(request, "coupon/admin_coupon.html", context)
    else:
        return redirect("admin_login")


@never_cache
def add_coupon(request):
    try:
        if request.user.is_superuser:
            today = timezone.now().date()
            if request.method == "POST":
                code = request.POST.get("coupon_code", "").strip()
                name = request.POST.get("name", "").strip()
                dis = request.POST.get("discount_percentage", "").strip()
                minimum_amount = request.POST.get("minimum_amount", "").strip()
                maximum_amount = request.POST.get("maximum_amount", "").strip()
                end_date = request.POST.get("end_date", "").strip()
                usage_limit = request.POST.get("usage_limit", "").strip()

                # Validate that all fields are provided
                if not all(
                    [
                        code,
                        name,
                        dis,
                        minimum_amount,
                        maximum_amount,
                        end_date,
                        usage_limit,
                    ]
                ):
                    messages.error(
                        request, "All fields are required for adding the coupon."
                    )
                    return redirect("add_coupon")

                # Validate the coupon code
                if not code:
                    messages.error(request, "Coupon code cannot be empty.")
                    return redirect("add_coupon")
                if Coupon.objects.filter(coupon_code=code).exists():
                    messages.error(
                        request, "This coupon already exists. Please add a new one."
                    )
                    return redirect("add_coupon")

                # Validate the coupon name
                if not name:
                    messages.error(request, "Coupon name cannot be empty.")
                    return redirect("add_coupon")

                # Validate the discount percentage
                try:
                    dis = float(dis)
                    if dis < 5 or dis > 100:
                        messages.error(
                            request,
                            "Please provide a valid discount between 5 and 100.",
                        )
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(request, "Please enter a valid discount percentage.")
                    return redirect("add_coupon")

                # Validate the minimum and maximum amounts
                try:
                    minimum_amount = float(minimum_amount)
                    maximum_amount = float(maximum_amount)
                    if minimum_amount < 100 or maximum_amount < 100:
                        messages.error(
                            request, "Price must be a positive value and at least 100."
                        )
                        return redirect("add_coupon")
                    if minimum_amount > maximum_amount:
                        messages.error(
                            request,
                            "Minimum amount cannot be greater than maximum amount.",
                        )
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(
                        request,
                        "Please enter valid amounts for minimum and maximum values.",
                    )
                    return redirect("add_coupon")

                # Validate the end date
                try:
                    end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
                    if str(end_date) < str(today):
                        messages.error(request, "End date cannot be in the past.")
                        return redirect("add_coupon")
                    elif str(end_date) and str(end_date) == str(today):
                        messages.error(request, "End date cannot be today.")
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(
                        request, "Please enter a valid date in YYYY-MM-DD format."
                    )
                    return redirect("add_coupon")

                # Validate the usage limit
                try:
                    usage_limit = int(usage_limit)
                    if usage_limit < 1:
                        messages.error(request, "Usage limit cannot be less than 1.")
                        return redirect("add_coupon")
                except ValueError:
                    messages.error(request, "Please enter a valid usage limit.")
                    return redirect("add_coupon")

                # Create the coupon
                coupon = Coupon.objects.create(
                    coupon_code=code,
                    coupon_name=name,
                    discount_percentage=dis,
                    minimum_amount=minimum_amount,
                    maximum_amount=maximum_amount,
                    expiry_date=end_date,
                    usage_limit=usage_limit,
                )
                messages.success(request, "Coupon added successfully.")
                return redirect("admin_coupon")

            return render(request, "coupon/add_coupon.html")
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    except Exception as e:
        messages.error(request, str(e))
        return render(request, "coupon/add_coupon.html")


def edit_coupon(request, coupon_id):
    if request.user.is_superuser:
        today = timezone.now()
        coupon = get_object_or_404(Coupon, id=coupon_id)
        if request.method == "POST":
            code = request.POST.get("coupon_code")
            name = request.POST.get("name")
            dis = request.POST.get("discount_percentage")
            min_amount = request.POST.get("minimum_amount")
            max_amount = request.POST.get("maximum_amount")
            end_date = request.POST.get("end_date")
            usage_limit = request.POST.get("usage_limit")

            if name:
                if not name.strip():
                    messages.error(request, "Name cannot be empty.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.coupon_name = name
            if dis:
                if float(dis) < 5 or float(dis) > 100:
                    messages.error(
                        request,
                        "Please provide a valid discount percentage between 5 and 100.",
                    )
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.discount_percentage = dis

            if min_amount:
                if float(min_amount) < 100:
                    messages.error(request, "Minimum amount must be a valid value.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.minimum_amount = min_amount
            if max_amount:
                if float(max_amount) < 1000:
                    messages.error(
                        request, "Maximum amount must be a greater than 1000."
                    )
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.maximum_amount = max_amount

            if code:
                if not code.strip():
                    messages.error(request, "Coupon code cannot be empty.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.coupon_code = code
            if end_date:
                if str(end_date) < str(today):
                    messages.error(request, "End date cannot be in the past.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                elif str(end_date) and str(end_date) == str(today):
                    messages.error(request, "End date cannot be today.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
                coupon.expiry_date = end_date
            if usage_limit:
                if int(usage_limit) < 1:
                    messages.error(request, "Usage limit cannot be less than 1.")
                    return redirect("edit_coupon", coupon_id=coupon_id)
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
        if request.method == "GET":
            from_date = request.GET.get("from")
            to_date = request.GET.get("to")
            month = request.GET.get("month")
            year = request.GET.get("year")

            order = OrderItem.objects.filter(
                cancel=False,
                return_product=False,
                status="Delivered",
            ).order_by("created_at")

            filters = {}
            if from_date:
                filters["from_date"] = from_date
                order = order.filter(created_at__gte=from_date)
            if to_date:
                filters["to_date"] = to_date
                order = order.filter(created_at__lte=to_date)
            if month:
                filters["month"] = month
                year, month = map(int, month.split("-"))
                order = order.filter(created_at__year=year, created_at__month=month)
            if year:
                filters["year"] = year
                order = order.filter(created_at__year=year)

            # Store filters in session
            request.session["filters"] = filters

            count = order.count()
            total = order.aggregate(total=Sum("order__total"))["total"]
            total_discount = order.aggregate(
                total_discount=Sum("order__discounted_price")
            )["total_discount"]

            context = {
                "order": order,
                "count": count,
                "total": total,
                "total_discount": total_discount,
            }
            request.session["overall_sales_count"] = count
            request.session["overall_order_amount"] = total
            request.session["overall_discount"] = total_discount

            return render(request, "sales_report.html", context)
        else:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("admin_login")
    else:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("admin_login")


def download_sales_report(request):
    if request.user.is_superuser:
        if request.method == "GET":
            filters = request.session.get("filters", {})
            sales_data = OrderItem.objects.filter(
                Q(cancel=False) & Q(return_product=False) & Q(status="Delivered")
            )

            if "from_date" in filters:
                sales_data = sales_data.filter(created_at__gte=filters["from_date"])
            if "to_date" in filters:
                sales_data = sales_data.filter(created_at__lte=filters["to_date"])
            if "month" in filters:
                year, month = map(int, filters["month"].split("-"))
                sales_data = sales_data.filter(
                    created_at__year=year, created_at__month=month
                )
            if "year" in filters:
                sales_data = sales_data.filter(created_at__year=filters["year"])
            if "from" in filters and "to_date" in filters:
                sales_data = sales_data.filter(
                    created_at__range=[filters["from"], filters["to"]]
                )

            overall_sales_count = request.session.get("overall_sales_count")
            overall_order_amount = request.session.get("overall_order_amount")
            overall_discount = request.session.get("overall_discount")

            if "format" in request.GET and request.GET["format"] == "pdf":
                buffer = BytesIO()

                doc = SimpleDocTemplate(buffer, pagesize=letter)

                styles = getSampleStyleSheet()
                centered_style = ParagraphStyle(
                    name="Centered", parent=styles["Heading1"], alignment=1
                )

                today_date = datetime.now().strftime("%Y-%m-%d")

                content = []

                company_details = f"<b>MELIOTIS</b><br/>Email: meliotis100@email.com<br/>Date: {today_date}"
                content.append(Paragraph(company_details, styles["Normal"]))
                content.append(Spacer(1, 0.5 * inch))

                content.append(Paragraph("<b>SALES REPORT</b><hr>", centered_style))
                content.append(Spacer(1, 0.5 * inch))

                data = [["Order ID", "Product", "Quantity", "Total Price", "Date"]]
                for sale in sales_data:
                    formatted_date = sale.order.created_at.strftime("%a, %d %b %Y")
                    data.append(
                        [
                            sale.order.tracking_id,
                            sale.product.product.name,
                            sale.qty,
                            sale.product.product.offer_price,
                            formatted_date,
                        ]
                    )

                table = Table(data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("TOPPADDING", (0, 0), (-1, 0), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )

                content.append(table)

                content.append(Spacer(1, 0.5 * inch))

                overall_sales_count_text = (
                    f"<b>Overall Sales Count:</b> {overall_sales_count}"
                )
                overall_order_amount_text = (
                    f"<b>Overall Order Amount:</b> {overall_order_amount}"
                )
                overall_discount_amount_text = (
                    f"<b>Overall Discount:</b> {overall_discount}"
                )

                content.append(Paragraph(overall_sales_count_text, styles["Normal"]))
                content.append(Paragraph(overall_order_amount_text, styles["Normal"]))
                content.append(
                    Paragraph(overall_discount_amount_text, styles["Normal"])
                )

                doc.build(content)

                current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                file_name = f"Sales_Report_{current_time}.pdf"

                response = HttpResponse(
                    buffer.getvalue(), content_type="application/pdf"
                )
                response["Content-Disposition"] = f'attachment; filename="{file_name}"'

                return response

            elif "format" in request.GET and request.GET["format"] == "excel":
                output = BytesIO()
                workbook = xlsxwriter.Workbook(output, {"in_memory": True})
                worksheet = workbook.add_worksheet("Sales Report")

                headings = ["Product", "Quantity", "Total Price", "Date"]
                header_format = workbook.add_format({"bold": True})
                for col, heading in enumerate(headings):
                    worksheet.write(0, col, heading, header_format)

                for row, sale in enumerate(sales_data, start=1):
                    formatted_date = sale.order.created_at.strftime("%a, %d %b %Y")
                    worksheet.write(row, 0, sale.product.product.name)
                    worksheet.write(row, 1, sale.qty)
                    worksheet.write(row, 2, sale.product.product.offer_price)
                    worksheet.write(row, 3, formatted_date)

                workbook.close()

                output.seek(0)
                response = HttpResponse(
                    output.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                file_name = f"Sales_Report_{current_time}.xlsx"
                response["Content-Disposition"] = f'attachment; filename="{file_name}"'

                return response

        else:
            return redirect("dashboard")
    else:
        return redirect("admin_login")

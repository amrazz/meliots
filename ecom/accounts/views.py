import re
import random
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages, auth
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db.models import F, ExpressionWrapper, DecimalField
from django.conf import settings
from ecom.settings import EMAIL_HOST_USER
from validate_email_address import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from admin_app.models import *
from .models import *
PRODUCT_PER_PAGE = 9

@never_cache
def register(request):
    try:
        if request.user.is_authenticated:
            return redirect('index')
        
        if request.method == 'POST':
            first_name = request.POST.get('f_name')
            last_name = request.POST.get('l_name')
            username = request.POST.get('username') 
            email = request.POST.get('email')
            password1 = request.POST.get('pass1')
            password2 = request.POST.get('pass2')

            if not all([first_name, last_name, username, email, password1, password2]):
                messages.error(request, 'Please fill up all the fields.')
                return redirect('register')
            
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'The username is already taken')
                return redirect('register')
            
            if not username.strip():
                messages.error(request, 'The username is not valid')
                return redirect('register')
            
            if len(password1) < 6:
                messages.error(request, 'The password should be at least 6 characters')
                return redirect('register')
            
            elif password1 != password2:
                messages.error(request, 'The passwords do not match')
                return redirect('register')
            
            try:
                validate_password(password1, user=User)
            except ValidationError as e:
                messages.error(request, ', '.join(e))
                return redirect('register')
            
            if not any(char.isupper() for char in password1):
                messages.error(request, 'Password must contain at least one uppercase letter')
                return redirect('register')
            
            if not any(char.islower() for char in password1):
                messages.error(request, 'Password must contain at least one lowercase letter')
                return redirect('register')
            
            if not any(char.isdigit() for char in password1):
                messages.error(request, 'Password must contain at least one digit')
                return redirect('register')
            
            elif not re.match(r"^[\w\.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email): 
                messages.error(request, 'Please enter a valid email address')
                return redirect('register')
            

            
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'This email is already registered')
                return redirect('register')
            
            otp, otp_generated_at = generate_otp_and_send_email(email)
            store_user_data_in_session(request, first_name, last_name, username, email, password1, otp, otp_generated_at)
            print(otp)
            messages.success(request, f'Welcome {first_name}')
            
            return redirect('my_otp')
        
        else:
            return render(request, 'register.html')
    
    except ValidationError as e:
        messages.error(request, ', '.join(e))
        return redirect('register')
    except Exception as e:
        messages.error(request, str(e))
        return redirect('register')

def generate_otp_and_send_email(email):
    otp = random.randint(1000, 9999)
    otp_generated_at = timezone.now().isoformat()

    send_mail(
        subject='Your OTP for verification',
        message=f'Your OTP for verification is: {otp}',
        from_email=EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=True
    )
    return otp, otp_generated_at

def store_user_data_in_session(request, first_name, last_name, username, email, password, otp, otp_generated_at):
    request.session['user_data'] = {
        'first_name': first_name,
        'last_name': last_name,
        'username': username,
        'email': email,
        'password': password,
        'otp': otp,
        'otp_generated_at': otp_generated_at
    }

@never_cache
def otp(request):
    try:
        if request.user.is_authenticated:
            return redirect('index')

        email = request.session.get('user_data', {}).get('email', '')
        print(email)
        if request.method == 'POST':
            otp_digits = [request.POST.get(f'digit{i}') for i in range(1, 5)]
            print( 'top digits are ',otp_digits)
            if None in otp_digits:
                messages.error(request, 'Invalid OTP format, please try again.')
                return redirect('my_otp')
            
            entered_otp = int(''.join(otp_digits))
            stored_otp = request.session.get('user_data', {}).get('otp')
            user_data = request.session.get('user_data', {})
            otp_generated_at = user_data.get('otp_generated_at', '')  
            
            try:
                otp_generated_at_datetime = datetime.fromisoformat(otp_generated_at)
            except ValueError:
                otp_generated_at_datetime = None

            if otp_generated_at_datetime and otp_generated_at_datetime + timedelta(minutes=5) < timezone.now():
                messages.error(request, 'OTP has expired. Please try again.')
                return redirect('register')
            print(f" entered otp:{entered_otp} == stored_otp{stored_otp}")
            if str(entered_otp) == str(stored_otp):
                user = User.objects.create_user(username=user_data['username'], first_name=user_data['first_name'], last_name=user_data['last_name'], email=user_data['email'], password=user_data['password'])
                user.save()
                del request.session['user_data']
                messages.success(request, f'{user.username} created successfully.')
                return redirect('login')
            else:
                messages.error(request, 'Invalid OTP, try again.')
                return redirect('my_otp')
            
        return render(request, 'otp.html', {'email': email})
    
    except Exception as e:
        messages.error(request, str(e))
        return redirect('register')
@never_cache
def resend_otp(request):
    try:
        user_data = request.session.get('user_data', {})
        email = user_data.get('email', '')
        
        new_otp, otp_generated_now = generate_otp_and_send_email(email)
        user_data['otp'] = new_otp
        user_data['otp_generated_at'] = otp_generated_now
        request.session['user_data'] = user_data
        print("new_otp : ", new_otp)
        print('session :', user_data)
        messages.success(request, 'New OTP sent successfully')
        return redirect('my_otp')
    
    except Exception as e:
        messages.error(request, str(e))
        return redirect('my_otp')


@never_cache
def log_in(request):
    try:
        if request.user.is_authenticated:
            return redirect('index')
        
        if request.method == "POST":
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            ext_user = authenticate(request, username=username, password=password)
            
            if ext_user is not None:
                auth.login(request, ext_user)
                return redirect('index')
            else:
                messages.error(request, 'The username or password is incorrect.')
                return redirect('login')
        else:
            return render(request, 'log.html')
    
    except Exception as e:
        messages.error(request, str(e))
        return redirect('login')

@never_cache
def verify_email(request):
    try:
        if request.user.is_authenticated:
            return redirect('index')
        
        if request.method == 'POST':
            email = request.POST.get('email')
            
            if User.objects.filter(email=email).exists():
                otp, otp_generated_at = generate_otp_and_send_email(email)
                request.session['verifyotp'] = {'otp': otp, 'email': email, 'otp_generated_at': otp_generated_at}
                return redirect('verify_otp')
            else:
                messages.error(request, 'Something went wrong')
                return redirect('verify_email')
    
    except Exception as e:
        messages.error(request, str(e))
    return render(request, 'pass_reset/verify_email.html')

@never_cache
def verify_otp(request):
    try:
        email = request.session.get('verifyotp', {}).get('email', '')

        if request.method == 'POST':
            otp_digits = [request.POST.get(f'otp{i}') for i in range(1, 5)]
            
            if None in otp_digits:
                messages.error(request, 'Invalid OTP format, please try again.')
                return redirect('verify_email')
                 
            entered_otp = int(''.join(otp_digits))
            storedotp = request.session.get('verifyotp', {}).get('otp')
            user_data = request.session.get('user_data', {})
            otp_generated_at_str = request.session.get('verifyotp', {}).get('otp_generated_at', '')
            
            try:
                otp_generated_at_datetime = datetime.fromisoformat(otp_generated_at_str)
            except ValueError:
                otp_generated_at_datetime = None
                
            if otp_generated_at_datetime and otp_generated_at_datetime + timedelta(minutes=2) < timezone.now():
                messages.error(request, 'OTP has expired. Please try again.')
                return redirect('verify_email')
                        
            if str(entered_otp) == str(storedotp):
                return redirect('reset_pass')
            
            else:
                messages.error(request, 'Incorrect OTP, please try again.')
                return redirect('verify_otp')

        return render(request, 'pass_reset/verify_otp.html', {'email': email})
    
    except Exception as e:
        messages.error(request, str(e))
        return redirect('verify_otp')

@never_cache
def reset_pass(request):
    email = request.session.get('verifyotp', {}).get('email', '')

    if request.method == 'POST':
        new_password = request.POST.get('newpassword')
        confirm_password = request.POST.get('confirmpassword')
        
        if new_password != confirm_password:
            messages.error(request, 'The passwords do not match')
            return redirect('reset_pass')
        
        try:
            validate_password(new_password)
        except ValidationError as e:
            messages.error(request, ', '.join(e))
            return redirect('reset_pass')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
            return redirect('reset_pass')
        
        user = User.objects.get(email=email)
        user.set_password(confirm_password)
        user.save()
        
        del request.session['verifyotp']

        messages.success(request, 'Password reset successfully')
        return redirect('login')
        
    return render(request, 'pass_reset/reset_pass.html')


@never_cache
def log_out(request):
    logout(request)
    return redirect('index')

@never_cache
def index(request):
    if request.user.is_authenticated:
        first_name_capitalized = request.user.first_name.title()
        products_color = ProductColorImage.objects.filter(product__is_deleted = False)
        products = Product.objects.filter(is_listed =True)
        context = {'username': first_name_capitalized,'products_color': products_color, 'products' : products}
        return render(request, 'index.html', context)
    return render(request, 'index.html')

@never_cache
def product_detail(request,product_id):
    products_color = ProductColorImage.objects.get(id = product_id)
    product_category = products_color.product.category
    related_product = ProductColorImage.objects.filter(Q(product__category=product_category) & Q(is_listed = True)).exclude(id = product_id)
    
    context = {
        'products_color' : products_color,
        'related_product' : related_product
    }
    return render(request, 'product_detail.html', context)


@never_cache
def mens_page(request):
    product = ProductColorImage.objects.all()
    products_color = ProductColorImage.objects.filter(
        Q(product__category__name="Men's") &
        Q(product__category__is_deleted = False) &
        Q(is_deleted=False))
    
    page = request.GET.get('page', 1)
    product_Paginator = Paginator(products_color, PRODUCT_PER_PAGE)
    
    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)
    
    context = {
        'products_color': products_color,
        'product' : product,
        'page_obj': products,
        'is_paginated': product_Paginator.num_pages > 1,
        'paginator': product_Paginator,
        }
    return render(request, 'mens.html', context)

@never_cache
def womens_page(request):
    product = Category.objects.all()
    products_color = ProductColorImage.objects.filter(
        Q(product__category__name="Women's") &
        Q(product__category__is_deleted = False) &
        Q(is_deleted=False))
    
    page = request.GET.get('page', 1)
    product_Paginator = Paginator(products_color, PRODUCT_PER_PAGE)
    
    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)
    
    context = {
        'products_color': products_color,
        'product' : product,
        'page_obj': products,
        'is_paginated': product_Paginator.num_pages > 1,
        'paginator': product_Paginator,
        }
    return render(request, 'womens.html', context)

@never_cache
def kids_page(request):
    product = Category.objects.all()
    products_color = ProductColorImage.objects.filter(
        Q(product__category__name="Kid's") &
        Q(product__category__is_deleted = False) &
        Q(is_deleted=False))
    
    page = request.GET.get('page', 1)
    product_Paginator = Paginator(products_color, PRODUCT_PER_PAGE)
    
    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)
    
    context = {
        'products_color': products_color,
        'product' : product,
        'page_obj': products,
        'is_paginated': product_Paginator.num_pages > 1,
        'paginator': product_Paginator,}
    return render(request, 'kids.html', context)

@never_cache
def shop_page(request):
    ordering = request.GET.get('ordering', 'name') 
    products_color = ProductColorImage.objects.filter(is_listed=True, is_deleted=False)

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    
    if min_price is not None:
        min_price = int(min_price)
    if max_price is not None:
        max_price = int(max_price)

    if min_price is not None and max_price is not None:
        products_color = products_color.annotate(
            calculated_offer_price=ExpressionWrapper(
                F('product__price') - (F('product__price') * F('product__percentage') / 100),
                output_field=DecimalField()
            )
        ).filter(calculated_offer_price__gte=min_price, calculated_offer_price__lte=max_price)
    
    categories_filter = request.GET.getlist('category')
    if categories_filter:
        products_color = products_color.filter(product__category__name__in=categories_filter)


    if ordering == 'name':
        products_color = products_color.order_by('product__name')
    elif ordering == '-name':
        products_color = products_color.order_by('-product__name')
    elif ordering == 'price':
        products_color = sorted(products_color, key=lambda x: x.product.offer_price())
    elif ordering == '-price':
        products_color = sorted(products_color, key=lambda x: x.product.offer_price(), reverse=True)
    elif ordering == 'created_at':
        products_color = products_color.order_by('product__created_at')

    page = request.GET.get('page', 1)
    product_Paginator = Paginator(products_color, PRODUCT_PER_PAGE)

    try:
        products = product_Paginator.page(page)
    except PageNotAnInteger:
        products = product_Paginator.page(1)
    except EmptyPage:
        products = product_Paginator.page(product_Paginator.num_pages)

    categories = Category.objects.filter(is_listed=True, is_deleted=False)

    context = {
        'products_color': products,
        'categories': categories,
        'page_obj': products,
        'is_paginated': product_Paginator.num_pages > 1,
        'paginator': product_Paginator,
    }
    return render(request, 'shop.html', context)



def profile(request):
    if request.user.is_authenticated:
        user = request.user
        customer = Customer.objects.get(user = user.id)
        context = {
            'user' : user,
            'customer' : customer
        }     
        return render(request, 'personal_info.html', context)

    else:
        return redirect('login')

def edit_profile(request, info_id):
    if request.user.is_authenticated:
        user = request.user
        try:
            customer = Customer.objects.get(id=info_id)
        except Customer.DoesNotExist:
            messages.error(request, 'Customer not found.')
            return redirect('profile')
        
        if request.method == 'POST':
            try:
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email = request.POST.get('email')
                dob = request.POST.get('dob')
                gender = request.POST.get('gender')
                phone_number = request.POST.get('phone_number')
                
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    messages.error(request, 'Email already in use.')
                    return redirect('edit_profile', info_id=customer.id)
                
                dob_date = datetime.strptime(dob, '%Y-%m-%d').date() 
                today = timezone.now().date()
                age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                
                if age < 18:
                    messages.error(request, 'You must be at least 18 years old to update your profile.')
                    return redirect('edit_profile', info_id=customer.id)
                
                if not phone_number or len(phone_number) < 10:
                    messages.error(request, 'Invalid mobile number.')
                    return redirect('edit_profile', info_id=customer.id)
                
                customer.user.first_name = first_name
                customer.user.last_name = last_name
                customer.user.email = email
                customer.dob = dob
                customer.gender = gender
                customer.phone_number = phone_number
                customer.user.save()
                customer.save()
                
                messages.success(request, 'Profile updated successfully.')
                return redirect(profile)
            except Exception as e:
                messages.error(request, 'An error occurred while updating your profile.')
                return redirect('edit_profile', info_id=customer.id)
        
        context = {
            'user': user,
            'customer': customer
        }
        return render(request, 'edit_personalinfo.html', context)

def change_password(request, pass_id):
    if request.user.is_authenticated:
        user = User.objects.get(id=pass_id)
        if request.method == 'POST':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not check_password(current_password, user.password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('change_password', pass_id=user.id)
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return redirect('change_password', pass_id=user.id)
            if len(new_password) < 8: 
                messages.error(request, 'New password must be at least 8 characters long.')
                return redirect('change_password', pass_id=user.id)
            
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')        
        context = {
            'user': user,
            'customer': Customer.objects.get(user=user)
        }
    return render(request, 'personal_info.html', context)


def address(request):
    try:
        
        address = Address.objects.filter(user=request.user.pk)
        context = {
            'address' : address
        }
        return render(request, 'address.html',context)
    except:
         return render(request, 'address.html')
        

def add_address(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            user = User.objects.get(pk=request.user.pk)
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            postal_code = request.POST.get('postal_code')
            house_name = request.POST.get('house_name')
            mobile_number = request.POST.get('mobile_number')

            
            if not all([first_name, last_name, city, email, state, country,postal_code, house_name, mobile_number]):
                messages.error(request, 'Please fill up all the fields.')
                print('not all')
                return redirect('add_address')
            if len(mobile_number) < 10 and len(mobile_number) > 12:
                messages.error(request, 'Moblie number is not valid.')
                print('moblie')
                return redirect('add_address')
            address = Address.objects.create(
                user = user,
                first_name = first_name,
                last_name = last_name,
                email=email,
                city = city,
                state = state,
                country = country,
                postal_code = postal_code,
                house_name = house_name, 
                phone_number = mobile_number
                )
            messages.success(request,'user address created successfully.')
            return redirect('address')
    return render(request, 'add_address.html')

def edit_address(request, address_id):
    if request.user.is_authenticated:
        user = request.user
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            messages.error(request, 'Address not found.')
            return redirect('address')
        
        
        context = {
            'address' :address,
            'user' : user
        }
        if request.method == 'POST':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            postal_code = request.POST.get('postal_code')
            house_name = request.POST.get('house_name')
            mobile_number = request.POST.get('mobile_number')
            
            if not all([first_name, last_name, city, email, state, country,postal_code, house_name, mobile_number]):
                messages.error(request, 'Please fill up all the fields.')
                return redirect('edit_address')
            if len(mobile_number) < 10 and len(mobile_number) > 12:
                messages.error(request, 'Moblie number is not valid.')
                return redirect('edit_address')
            
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
            
            messages.success(request, 'Address updated successfully.')
            return redirect('address')            
    return render(request, 'edit_address.html',context)

def delete_address(request,address_id):
    try:
        data=Address.objects.get(id=address_id)
        data.delete()
        return redirect('address')
    except:
        return redirect('address')
        
        
#_______________________________________________X_________________________X__________________________


def search_pro(request):
    try:
        if request.method == 'POST':
            query = request.POST.get('query')
            products_color = ProductColorImage.objects.filter(product__is_deleted=False, product__name__icontains=query)
            print(query)
            print(products_color)

            context = {
                'products_color': products_color,
                'query': query
            }
            return render(request, 'filter/search.html', context)
    except Exception as e:
        messages.error(request, 'Something went wrong please try again.')
        return redirect('index')
    
@never_cache
def filter_products_by_price(request):
    try:
        min_price = request.GET.get('min', 500)
        max_price = request.GET.get('max', 50000)
        
        products = ProductColorImage.objects.filter(product__offer_price__gte=min_price, product__offer_price__lte=max_price)
        return render(request, 'shop.html', {'products_color': products})
    except Exception as e:
            messages.error(request, 'Something went wrong please try again.')
            return redirect('index')
        
        

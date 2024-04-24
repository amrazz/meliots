from django.shortcuts import render,redirect
from django.http import JsonResponse
from .models import *
from django.contrib import messages,auth
from admin_app.models import *
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils.crypto import get_random_string
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))


# Create your views here.


@never_cache
@login_required(login_url = 'login')
def shop_cart(request):
    if request.user.is_authenticated:
        user = Customer.objects.get(user = request.user.pk)
        customer = User_Cart.objects.get(customer = user)
        cart_items = CartItem.objects.filter(user_cart = customer,product__product__is_listed = True,product__product__is_deleted = False).distinct()
        
        sub_total = sum(item.total_price() for item in cart_items)
        total = sub_total
        
        total_quantity = sum(i.quantity for i in cart_items)
        if total_quantity >= 5:
            shipping_fee = 'Free'
        else:
            shipping_fee = 99
        if shipping_fee == 99:
            total += shipping_fee
        

        context = {
            'cart_items' : cart_items,
            'sub_total': sub_total,
            'total' :total,
            'shipping_fee':shipping_fee
          
            
        }
        
        return render(request, 'shop_cart.html', context)
    else:
        return redirect('login')

@never_cache
def add_to_cart(request, pro_id):
    if request.user.is_authenticated:
        if request.method == 'POST':
            print('reached here at post')
            product = ProductColorImage.objects.get(id = pro_id)
            
            
            if CartItem.objects.filter(product = product).exists():
                messages.error(request, 'Product already exists in the Cart.')
                return redirect('product_detail', pro_id)
            
            
            quantity = int(request.POST.get('quantity'))
            if int(quantity) <= 0:
                messages.error(request, 'Invalid quantity.')
                return redirect('product_detail', pro_id)
            # size = ProductSize.objects.get(productcolor__id = pro_id)
            # if size.quantity < quantity:
            #     messages.error(request, 'Selected quantity exceeds available stock.')
            #     return redirect('product_detail', pro_id)
            product_size = request.POST.get('size')
            print(product_size, quantity)
            if not product_size:
                messages.error(request, 'Please select a size for the product.')
                return redirect('product_detail', pro_id)
            user = Customer.objects.get(user=request.user.pk)
            user_cart = User_Cart.objects.get(customer=user) 
            cart_item = CartItem.objects.create(user_cart=user_cart, product=product, quantity=quantity, product_size = product_size)
            cart_item.save()
            print(cart_item)
            print('successfully added')
            messages.success(request, 'Product added to Cart.')
            return redirect('shop_cart')
        return redirect('shop_cart')
    else:
        return redirect('login')
    
    
def delete_cart_items(request, pro_id):
        cart_items = CartItem.objects.get(id = pro_id)
        print(pro_id)
        cart_items.delete()
        messages.success(request, 'Product removed from Cart')
        return redirect('shop_cart')
    


                
@never_cache                
def update_total_price(request):
    if request.method == 'POST':
        cart_item_id = request.POST.get('cart_item_id')
        new_quantity = int(request.POST.get('new_quantity'))
        cart_item = CartItem.objects.get(id = cart_item_id)
        cart_item.quantity = new_quantity
        cart_item.save()
        new_total_price = cart_item.total_price()
        
        user = Customer.objects.get(user = request.user.pk)
        customer = User_Cart.objects.get(customer = user)
        cart_items = CartItem.objects.filter(user_cart = customer).distinct()
        
        sub_total = sum(item.total_price() for item in cart_items)
        total_quantity = sum(i.quantity for i in cart_items)
        if total_quantity > 5:
            shipping_fee = 'Free'
        else:
            shipping_fee = 99
            
        if shipping_fee == 'Free':
            total = sub_total
        else:
            total = sub_total + shipping_fee
            
        return JsonResponse({
            'new_total_price' : new_total_price,
            'subtotal' : sub_total,
            'total' : total,
            'shipping_fee' : shipping_fee
            })
    return JsonResponse({'error': 'Invalid request'}, status=400)

def checkout(request):
    try:
        if request.user.is_authenticated:
            user = Customer.objects.get(user=request.user.pk)
            cart = CartItem.objects.filter(user_cart__customer=user)
            
            if not cart.exists():
                messages.error(request, 'Your cart is empty.')
                return redirect('shop_cart')
            
            for item in cart:
                for i in item.product.size.all():
                    if item.quantity > i.quantity:
                        CartItem.objects.get(id=item.id).delete()
            
            sub_total = sum(price.total_price() for price in cart)
            total = sub_total
            
            cart_qty = sum(item.quantity for item in cart)
            if cart_qty > 5:
                shipping_fee = "Free"
                total = sub_total
            elif cart_qty <= 5:
                shipping_fee = 99
                total = sub_total + shipping_fee            
        
            custom = Customer.objects.get(user=request.user.pk)
            user_cart = User_Cart.objects.get(customer=custom)
            cart_items = CartItem.objects.filter(user_cart=user_cart)
            addresses = Address.objects.filter(user=request.user)

            if not addresses.exists():
                messages.warning(request, 'You have no saved address. Please add an address first.')
                return redirect('address')
            
            context = {
                'cartitems': cart_items, 
                'addresses': addresses,
                'total': total,
                'sub_total': sub_total,
                'shipping_fee': shipping_fee
            }
                
            return render(request, 'checkout.html', context)
        else:
            return redirect('login')
    except Exception as e:
        messages.error(request, 'Something went wrong please try again.')
        return redirect('checkout')

    
    
def place_order(request):
    try:
        if request.user.is_authenticated:
            if request.method == 'POST':
                address_id = request.POST.get('select_address')
                address = Address.objects.get(id=address_id)
                pm = request.POST.get('payment_method')
                
                if not address_id:
                    messages.error(request, 'Please select an address.')
                    return redirect('checkout')
                if not pm:
                    messages.error(request, 'Please select a Payment Method.')
                    return redirect('checkout')
                
                customer = Customer.objects.get(user=request.user.pk)
                cart = CartItem.objects.filter(user_cart__customer=customer)
                
                if not cart.exists():
                    messages.error(request, 'The Cart is empty.')
                    return redirect('shop_cart')
                
                
                subtotal = sum(total.total_price() for total in cart)
                qty = sum(qty.quantity for qty in cart)
                if qty > 5:
                    total = subtotal
                else:
                    total = 99 + subtotal
                    
                tk_id = get_random_string(10, 'ABCDEFGHIJKLMOZ0123456789')
                while Order.objects.filter(tracking_id=tk_id).exists():
                    tk_id = get_random_string(10, 'ABCDEFGHIJKLMOZ0123456789')


                order = Order.objects.create(
                    customer=customer,
                    address=address,
                    payment_method=pm,
                    status='Order Placed',
                    total=total,
                    tracking_id=tk_id
                )
                
                for cart_item in cart:
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=cart_item.product, 
                        qty = cart_item.quantity,
                        size = cart_item.product_size
                    )
                product_size = ProductSize.objects.get(productcolor=cart_item.product, size=cart_item.product_size)
                product_size.quantity -= cart_item.quantity
                product_size.save()
                
                    
                cart.delete()

                messages.success(request, 'Order placed successfully.')
                return redirect('order_detail')  
                
            else:
                return redirect('checkout')
            
        else:
            return redirect('login')
    except Exception as e:
        messages.error(request, 'Something went wrong please try again.')
        return redirect('checkout')
    

def order_detail(request):
    return render(request, 'op.html')



def view_order(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        items=OrderItem.objects.filter(order__customer=customer)       
        context = {
            'items' : items
        }
        return render(request, 'view_order.html', context)
    
    
def view_status(request, order_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        order_items = OrderItem.objects.get(pk = order_id)
        print(order_items)
        status_info = {
        'Order Placed': {'color': '#009608', 'label': 'Order Placed'},
        'Shipped': {'color': '#009608', 'label': 'Shipped'},
        'Out for Delivery': {'color': '#009608', 'label': 'Out for Delivery'},
        'Delivered': {'color': '#009608', 'label': 'Delivered'}
        }
        context = {
            'order_items' : order_items,
            'status_info' : status_info
        }
        return render(request, 'view_status.html', context)
    
def cancel_order(request,order_id):
    print(order_id)
    if request.user.is_authenticated:
        order_item = OrderItem.objects.get(pk = order_id)
        order = order_item.order
        if order.customer.user == request.user:
            order.status = 'Cancelled'
            order.save()
            return render(request, 'view_status.html',{'order_items' : order_item})
    return redirect('login')
    
    
def wishlist_view(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user.pk)
        wished_products = WishList.objects.filter(customer=customer)
        context = {
            'wished_products': wished_products,
        }
        return render(request, 'wishlist.html', context)
    else:
        return redirect('login')


    
    
def wishlist_add(request, pro_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user)
        product = ProductColorImage.objects.get(id=pro_id)

        wishlist_item, created = WishList.objects.get_or_create(
            customer=customer, 
            product=product,
            size='S',
            qty=1
        )
        wishlist_item.save()
            
        if created:
            messages.success(request, 'Product added to wishlist.')
        else:
            messages.info(request, 'Product already in wishlist.')
                
        return redirect('product_detail', product_id=pro_id)

    else:
        return redirect('login')
    

def wishlist_del(request, pro_id):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user = request.user.pk)
        WishList.objects.filter(id=pro_id, customer=customer).delete()
        messages.success(request, 'Product removed from wishlist.')
        return redirect('wishlist_view')
    else:
        return redirect('login')
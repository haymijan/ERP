# pos/views.py (চূড়ান্ত এবং সম্পূর্ণ নির্ভুল সংস্করণ)

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from decimal import Decimal

# মডেল ইম্পোর্ট
from products.models import Product
from sales.models import SalesOrder, SalesOrderItem
from stock.models import Stock, Warehouse, LotSerialNumber
from stock.services import StockService
from partners.models import Customer


DEFAULT_CURRENCY_SYMBOL = 'QAR'

@login_required
def pos_view(request):
    # --- POST অনুরোধ হ্যান্ডলিং (নতুন সেলস তৈরি) ---
    # এই অংশটি আপনার POS ফ্রন্টএন্ড থেকে সেলস ডেটা গ্রহণ এবং প্রসেস করবে।
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart = data.get('cart', [])
            customer_id = data.get('customer_id')
            
            if not cart:
                return JsonResponse({'status': 'error', 'message': 'Cart is empty.'}, status=400)

            # ব্যবহারকারীর জন্য সঠিক ওয়্যারহাউস নির্ধারণ
            warehouse = None
            if not request.user.is_superuser and hasattr(request.user, 'warehouse'):
                warehouse = request.user.warehouse
            
            # যদি অ্যাডমিন হন এবং কোনো নির্দিষ্ট ওয়্যারহাউস না থাকে, তাহলে প্রথমটি ডিফল্ট হিসেবে নিন
            if not warehouse:
                warehouse = Warehouse.objects.first()
            
            if not warehouse:
                return JsonResponse({'status': 'error', 'message': 'No warehouse available for this transaction.'}, status=400)

            customer = get_object_or_404(Customer, id=customer_id) if customer_id else None

            with transaction.atomic():
                sales_order = SalesOrder.objects.create(
                    customer=customer,
                    user=request.user,
                    status='delivered', # POS সেলস সবসময় ডেলিভারড
                    warehouse=warehouse # <-- স্বয়ংক্রিয়ভাবে নির্ধারিত ওয়্যারহাউস
                )
                
                total_amount = Decimal('0.0')
                
                for item_data in cart:
                    product = get_object_or_404(Product, id=item_data['id'])
                    quantity = Decimal(item_data['quantity'])
                    unit_price = Decimal(item_data['sale_price']) # আপনার JS থেকে 'sale_price' আসছে
                    
                    order_item = SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        cost_price=product.cost_price
                    )
                    
                    # আপনার StockService ব্যবহার করে স্টক আপডেট
                    StockService.change_stock(
                        product=product,
                        warehouse=warehouse,
                        quantity_change=-quantity,
                        transaction_type='sale',
                        user=request.user,
                        content_object=sales_order,
                        notes=f"POS Sale - SO-{sales_order.id}"
                    )
                    
                    total_amount += order_item.subtotal

                sales_order.total_amount = total_amount
                sales_order.save()

            receipt_html = render_to_string('pos/pos_receipt.html', {'sales_order': sales_order})
            
            return JsonResponse({
                'status': 'success', 
                'order_id': sales_order.id,
                'receipt_html': receipt_html
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # --- AJAX GET অনুরোধ (প্রোডাক্ট লোড করার জন্য) ---
    # আপনার পুরোনো এবং সঠিক লজিকটি এখানে অক্ষুণ্ণ রাখা হয়েছে।
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user_warehouse = getattr(request.user, 'warehouse', None)
        products_qs = Product.objects.filter(is_active=True)

        if not request.user.is_superuser:
            if not user_warehouse:
                return JsonResponse({'products': [], 'error': 'No warehouse assigned.'}, status=400)
            products_qs = products_qs.filter(stocks__warehouse=user_warehouse, stocks__quantity__gt=0).distinct()
            products_qs = products_qs.annotate(
                current_stock=Coalesce(Sum('stocks__quantity', filter=Q(stocks__warehouse=user_warehouse)), 0)
            )
        else:
            products_qs = products_qs.annotate(
                current_stock=Coalesce(Sum('stocks__quantity'), 0)
            )

        products_data = []
        for product in products_qs.order_by('name'):
            if product.current_stock > 0:
                image_url = ''
                try:
                    if product.image and hasattr(product.image, 'url'):
                        image_url = product.image.url
                except Exception:
                    image_url = '/static/images/placeholder.png' # একটি ডিফল্ট ইমেজ পাথ
                
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'code': product.product_code,
                    'sale_price': float(product.sale_price), # 'price' এর পরিবর্তে 'sale_price'
                    'image_url': image_url,
                    'current_stock': product.current_stock,
                })
        return JsonResponse({'products': products_data})
    
    # --- সাধারণ GET অনুরোধ (POS পেজ লোড) ---
    context = {
        'title': 'Point of Sale',
        'DEFAULT_CURRENCY_SYMBOL': DEFAULT_CURRENCY_SYMBOL,
        'customers': Customer.objects.filter(is_active=True) # কাস্টমারদের লিস্ট যোগ করা হলো
    }
    return render(request, 'pos/pos.html', context)


@csrf_protect
@login_required
def pos_checkout_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_data = data.get('cart')
            user_warehouse = getattr(request.user, 'warehouse', None)

            if not user_warehouse:
                return JsonResponse({'status': 'error', 'message': 'No warehouse assigned.'}, status=400)

            with transaction.atomic():
                sales_order = SalesOrder.objects.create(
                    status='delivered', user=request.user, warehouse=user_warehouse,
                    payment_method=data.get('payment_method'), amount_tendered=data.get('amount_tendered'),
                    change_due=data.get('change_due')
                )
                
                total_amount = 0
                for item in cart_data:
                    product = get_object_or_404(Product, id=item['id'])
                    quantity_sold = Decimal(item['quantity'])
                    
                    available_lots = LotSerialNumber.objects.filter(
                        product=product, location__warehouse=user_warehouse, quantity__gt=0
                    ).order_by('expiration_date', 'created_at')

                    if (available_lots.aggregate(total=Sum('quantity'))['total'] or 0) < quantity_sold:
                        raise ValueError(f"Insufficient stock for {product.name}.")

                    remaining_qty_to_sell = quantity_sold
                    for lot in available_lots:
                        if remaining_qty_to_sell <= 0: break
                        
                        qty_from_this_lot = min(lot.quantity, remaining_qty_to_sell)

                        # --- মূল পরিবর্তন: SalesOrderItem-এর সাথে লট এবং cost_price সেভ করা ---
                        SalesOrderItem.objects.create(
                            sales_order=sales_order, 
                            product=product, 
                            quantity=qty_from_this_lot,
                            unit_price=item['sale_price'],
                            cost_price=product.cost_price,  # <-- এই লাইনটি যোগ করা হয়েছে
                            lot_serial=lot
                        )

                        StockService.change_stock(
                            product=product, warehouse=user_warehouse, quantity_change=-qty_from_this_lot,
                            transaction_type='sale', user=request.user, content_object=sales_order,
                            location=lot.location, lot_serial=lot, notes=f"POS Sale SO-{sales_order.id}"
                        )
                        remaining_qty_to_sell -= qty_from_this_lot
                
                total_amount = sum(Decimal(i['quantity']) * Decimal(i['sale_price']) for i in cart_data)
                sales_order.total_amount = total_amount
                sales_order.save()
                
                request.session['pos_cart'] = {}
                receipt_url = reverse('pos:pos_receipt_view', args=[sales_order.id])
                return JsonResponse({'status': 'success', 'message': 'Sale completed!', 'receipt_url': receipt_url})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def pos_add_to_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            quantity_to_add = int(request.POST.get('quantity', 1))
            product = get_object_or_404(Product, id=product_id)
            cart = request.session.get('pos_cart', {})
            
            if str(product_id) not in cart:
                cart[str(product_id)] = {'id': product.id, 'name': product.name, 'sale_price': float(product.sale_price), 'quantity': 0}
            cart[str(product_id)]['quantity'] += quantity_to_add
            
            request.session['pos_cart'] = cart
            request.session.modified = True
            return JsonResponse({'status': 'success', 'message': f'{product.name} updated in cart.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
def pos_remove_from_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        cart = request.session.get('pos_cart', {})
        if str(product_id) in cart:
            if cart[str(product_id)]['quantity'] > 1:
                cart[str(product_id)]['quantity'] -= 1
            else:
                del cart[str(product_id)]
        request.session['pos_cart'] = cart
        request.session.modified = True
        return JsonResponse({'status': 'success', 'message': 'Cart updated.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
def pos_get_cart(request):
    cart = request.session.get('pos_cart', {})
    cart_items = list(cart.values())
    total_amount = sum(item['quantity'] * item['sale_price'] for item in cart_items)
    for item in cart_items:
        item['item_total'] = item['quantity'] * item['sale_price']
    return JsonResponse({'cart_items': cart_items, 'total_amount': total_amount})


@login_required
def pos_receipt_view(request, order_id):
    order = get_object_or_404(SalesOrder, id=order_id)
    context = {'order': order, 'DEFAULT_CURRENCY_SYMBOL': DEFAULT_CURRENCY_SYMBOL}
    return render(request, 'pos/pos_receipt.html', context)
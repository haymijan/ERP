# inventory_system/views.py (ফিল্টার লজিক সংশোধিত)

import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, Value, IntegerField, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime
from collections import OrderedDict

# Local Application Imports
from products.models import Product
from sales.models import SalesOrder, SalesOrderItem, SalesReturn, SalesReturnItem
from partners.models import Supplier, Customer
from stock.models import Stock, LotSerialNumber

DEFAULT_CURRENCY_SYMBOL = 'QAR '

@login_required
def dashboard(request):
    user = request.user
    user_warehouse = getattr(user, 'warehouse', None)

    if user.groups.filter(name='POS Sales Staff').exists():
        return redirect('pos:pos_view')

    # --- নতুন এবং উন্নত তারিখ ফিল্টার লজিক ---
    today = timezone.now().date()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    period = request.GET.get('period')

    # ডেটাবেস কোয়েরির জন্য তারিখ
    query_start_date, query_end_date = None, None
    # ইনপুট ফিল্ডে দেখানোর জন্য তারিখ
    form_start_date, form_end_date = None, None

    if period:
        if period == 'today':
            query_start_date = query_end_date = today
        elif period == 'week':
            query_start_date = today - timedelta(days=today.weekday())
            query_end_date = today
        elif period == 'month':
            query_start_date = today.replace(day=1)
            query_end_date = today
    elif start_date_str and end_date_str:
        try:
            query_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query_end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            # কাস্টম তারিখ দিলে, সেটি ইনপুট ফিল্ডে দেখাবে
            form_start_date, form_end_date = query_start_date, query_end_date
            period = None  # কাস্টম তারিখ থাকলে period আনসেট হবে
        except (ValueError, TypeError):
            # ভুল তারিখ ফরম্যাট দিলে ডিফল্ট ভিউতে ফিরে যাবে
            query_start_date = query_end_date = today
            period = 'today'
    else:
        # ডিফল্ট ভিউ (কোনো ফিল্টার ছাড়া): আজকের ডেটা দেখাবে
        query_start_date = query_end_date = today
        period = 'today'
        # ... কিন্তু ইনপুট ফিল্ড খালি থাকবে

    # --- (বাকি কোড অপরিবর্তিত) ---
    sales_base_qs = SalesOrder.objects.filter(status='delivered')
    returns_base_qs = SalesReturn.objects.all()
    products_with_stock = Product.objects.filter(stocks__isnull=False).distinct()
    stock_qs_user_specific = Stock.objects.all()

    if not user.is_superuser and user_warehouse:
        sales_base_qs = sales_base_qs.filter(warehouse=user_warehouse)
        returns_base_qs = returns_base_qs.filter(warehouse=user_warehouse)
        products_with_stock = Product.objects.filter(stocks__warehouse=user_warehouse).distinct()
        stock_qs_user_specific = stock_qs_user_specific.filter(warehouse=user_warehouse)

    # তারিখ অনুযায়ী ফিল্টার (query_start_date এবং query_end_date ব্যবহার করে)
    if query_start_date:
        sales_base_qs = sales_base_qs.filter(order_date__gte=query_start_date)
        returns_base_qs = returns_base_qs.filter(return_date__gte=query_start_date)
    if query_end_date:
        end_date_plus_one = query_end_date + timedelta(days=1)
        sales_base_qs = sales_base_qs.filter(order_date__lt=end_date_plus_one)
        returns_base_qs = returns_base_qs.filter(return_date__lt=end_date_plus_one)

    # ... (আপনার পুরোনো লাভ, ইনভেনটরি টার্নওভার, ইত্যাদি সকল গণনা অপরিবর্তিত থাকবে)
    total_profit = 0
    if user.is_superuser and query_start_date and query_end_date:
        sales_items_qs = SalesOrderItem.objects.filter(sales_order__in=sales_base_qs)
        profit_agg = sales_items_qs.aggregate(
            total_profit=Sum(F('quantity') * (F('unit_price') - F('cost_price')), output_field=DecimalField())
        )
        gross_profit = profit_agg.get('total_profit') or 0

        returned_items_qs = SalesReturnItem.objects.filter(sales_return__in=returns_base_qs)
        lost_profit_agg = returned_items_qs.aggregate(
            total_lost_profit=Sum(F('quantity') * (F('unit_price') - F('product__cost_price')), output_field=DecimalField())
        )
        lost_profit = lost_profit_agg.get('total_lost_profit') or 0
        total_profit = gross_profit - lost_profit


    inventory_turnover_ratio = 0
    avg_days_to_sell = 0
    if query_start_date and query_end_date:
        number_of_days = (query_end_date - query_start_date).days + 1
        sales_items_qs_period = SalesOrderItem.objects.filter(sales_order__in=sales_base_qs)

        cogs_agg = sales_items_qs_period.aggregate(total_cogs=Sum(F('quantity') * F('cost_price'), output_field=DecimalField()))
        gross_cogs = cogs_agg.get('total_cogs') or 0

        returned_items_qs_period = SalesReturnItem.objects.filter(sales_return__in=returns_base_qs)
        returned_cogs_agg = returned_items_qs_period.aggregate(
            total_returned_cogs=Sum(F('quantity') * F('product__cost_price'), output_field=DecimalField())
        )
        returned_cogs = returned_cogs_agg.get('total_returned_cogs') or 0

        net_cogs = gross_cogs - returned_cogs

        avg_inventory_value_agg = stock_qs_user_specific.aggregate(total_value=Sum(F('quantity') * F('product__cost_price'), output_field=DecimalField()))
        avg_inventory_value = avg_inventory_value_agg.get('total_value') or 0

        if net_cogs > 0 and avg_inventory_value > 0 and number_of_days > 0:
            turnover_for_period = net_cogs / avg_inventory_value
            annualized_turnover = turnover_for_period * (Decimal(365) / Decimal(number_of_days))
            if user.is_superuser:
                inventory_turnover_ratio = annualized_turnover
            if annualized_turnover > 0:
                avg_days_to_sell = 365 / annualized_turnover

    stock_aggregation = products_with_stock.annotate(total_quantity=Sum('stocks__quantity', filter=Q(stocks__warehouse=user_warehouse) if not user.is_superuser and user_warehouse else Q())).aggregate(
        in_stock_count=Count('pk', filter=Q(total_quantity__gt=F('min_stock_level'))),
        low_stock_count=Count('pk', filter=Q(total_quantity__lte=F('min_stock_level'), total_quantity__gt=0)),
        out_of_stock_count=Count('pk', filter=Q(total_quantity__lte=0)),
    )
    in_stock_count = stock_aggregation.get('in_stock_count', 0)
    low_stock_count = stock_aggregation.get('low_stock_count', 0)
    out_of_stock_count = stock_aggregation.get('out_of_stock_count', 0)
    total_products = products_with_stock.count()
    total_customers = Customer.objects.count()
    total_suppliers = Supplier.objects.count()
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    # Today's and This month's data should be based on current date, not filtered date range
    todays_sales_qs_unfiltered = SalesOrder.objects.filter(status='delivered', order_date__date=today)
    this_months_sales_qs_unfiltered = SalesOrder.objects.filter(status='delivered', order_date__gte=start_of_month)
    todays_returns_qs_unfiltered = SalesReturn.objects.filter(return_date__date=today)
    this_months_returns_qs_unfiltered = SalesReturn.objects.filter(return_date__gte=start_of_month)

    if not user.is_superuser and user_warehouse:
        todays_sales_qs_unfiltered = todays_sales_qs_unfiltered.filter(warehouse=user_warehouse)
        this_months_sales_qs_unfiltered = this_months_sales_qs_unfiltered.filter(warehouse=user_warehouse)
        todays_returns_qs_unfiltered = todays_returns_qs_unfiltered.filter(warehouse=user_warehouse)
        this_months_returns_qs_unfiltered = this_months_returns_qs_unfiltered.filter(warehouse=user_warehouse)

    todays_gross_sales = todays_sales_qs_unfiltered.aggregate(total=Sum('total_amount'))['total'] or 0
    this_months_gross_sales = this_months_sales_qs_unfiltered.aggregate(total=Sum('total_amount'))['total'] or 0
    
    todays_returns_total = todays_returns_qs_unfiltered.aggregate(
        total=Coalesce(Sum(F('items__quantity') * F('items__unit_price')), Decimal('0.0'), output_field=DecimalField())
    )['total']
    this_months_returns_total = this_months_returns_qs_unfiltered.aggregate(
        total=Coalesce(Sum(F('items__quantity') * F('items__unit_price')), Decimal('0.0'), output_field=DecimalField())
    )['total']
    
    todays_net_sales = todays_gross_sales - todays_returns_total
    this_months_net_sales = this_months_gross_sales - this_months_returns_total

    unfulfilled_orders_query = SalesOrder.objects.filter(Q(status='confirmed') | Q(status__iexact='partially_delivered'))
    if not user.is_superuser and user_warehouse:
        unfulfilled_orders_query = unfulfilled_orders_query.filter(warehouse=user_warehouse)
    unfulfilled_orders_count = unfulfilled_orders_query.count()
    thirty_days_later = today + timedelta(days=30)
    expiring_lots_qs = LotSerialNumber.objects.filter(expiration_date__isnull=False, expiration_date__gte=today, expiration_date__lte=thirty_days_later, quantity__gt=0)
    if not user.is_superuser and user_warehouse:
        expiring_lots_qs = expiring_lots_qs.filter(location__warehouse=user_warehouse)
    expiring_lots_count = expiring_lots_qs.count()
    ninety_days_ago = today - timedelta(days=90)
    sold_product_ids = SalesOrderItem.objects.filter(sales_order__order_date__gte=ninety_days_ago).values_list('product_id', flat=True).distinct()
    dead_stock_products_qs = stock_qs_user_specific.filter(quantity__gt=0).exclude(product_id__in=sold_product_ids)
    dead_stock_count = dead_stock_products_qs.values('product_id').distinct().count()
    thirty_days_ago = today - timedelta(days=30)
    purchase_suggestion_count = 0
    products_in_stock = stock_qs_user_specific.filter(quantity__gt=0).values('product_id').annotate(current_stock=Sum('quantity'))
    product_stock_map = {item['product_id']: item['current_stock'] for item in products_in_stock}
    sales_qs = SalesOrderItem.objects.filter(sales_order__order_date__gte=thirty_days_ago, product_id__in=product_stock_map.keys())
    if not user.is_superuser and user_warehouse:
        sales_qs = sales_qs.filter(sales_order__warehouse=user_warehouse)
    sales_last_30_days_agg = sales_qs.values('product_id').annotate(total_sold=Sum('quantity'))
    sales_map = {item['product_id']: item['total_sold'] for item in sales_last_30_days_agg}
    returns_qs = SalesReturnItem.objects.filter(sales_return__return_date__gte=thirty_days_ago, product_id__in=product_stock_map.keys())
    if not user.is_superuser and user_warehouse:
        returns_qs = returns_qs.filter(sales_return__warehouse=user_warehouse)
    returns_last_30_days_agg = returns_qs.values('product_id').annotate(total_returned=Sum('quantity'))
    returns_map = {item['product_id']: item['total_returned'] for item in returns_last_30_days_agg}
    all_product_ids = set(sales_map.keys()) | set(returns_map.keys())
    for product_id in all_product_ids:
        sold_qty = sales_map.get(product_id, 0)
        returned_qty = returns_map.get(product_id, 0)
        net_sold = sold_qty - returned_qty
        if product_stock_map.get(product_id, 0) < net_sold:
            purchase_suggestion_count += 1
    category_data_query = products_with_stock.values('category__name').annotate(count=Count('id')).order_by('-count')
    category_labels = [item['category__name'] or "Uncategorized" for item in category_data_query]
    category_data = [item['count'] for item in category_data_query]
    status_labels = ['In Stock', 'Low Stock', 'Out of Stock']
    status_data = [in_stock_count, low_stock_count, out_of_stock_count]
    twelve_months_ago = (timezone.now() - timedelta(days=365)).date().replace(day=1)
    months_data = OrderedDict()
    current_month_start = twelve_months_ago
    while current_month_start <= today.replace(day=1):
        month_key = current_month_start.strftime('%b %Y')
        months_data[month_key] = {'sales': 0, 'returns': 0}
        next_month = (current_month_start.replace(day=28) + timedelta(days=4))
        current_month_start = next_month.replace(day=1)
    monthly_sales_base_qs = SalesOrder.objects.filter(status='delivered', order_date__gte=twelve_months_ago)
    if not user.is_superuser and user_warehouse:
        monthly_sales_base_qs = monthly_sales_base_qs.filter(warehouse=user_warehouse)
    monthly_sales_query = monthly_sales_base_qs.annotate(month=TruncMonth('order_date')).values('month').annotate(total_sales=Sum('total_amount')).order_by('month')
    for data in monthly_sales_query:
        if data['month']:
            month_key = data['month'].strftime('%b %Y')
            if month_key in months_data:
                months_data[month_key]['sales'] = float(data['total_sales'])
    monthly_returns_base_qs = SalesReturn.objects.filter(return_date__gte=twelve_months_ago)
    if not user.is_superuser and user_warehouse:
        monthly_returns_base_qs = monthly_returns_base_qs.filter(warehouse=user_warehouse)
    monthly_returns_query = monthly_returns_base_qs.annotate(month=TruncMonth('return_date')).values('month').annotate(
        total_returns=Sum(F('items__quantity') * F('items__unit_price'))
    ).order_by('month')
    for data in monthly_returns_query:
        if data['month']:
            month_key = data['month'].strftime('%b %Y')
            if month_key in months_data and data['total_returns']:
                months_data[month_key]['returns'] = float(data['total_returns'])
    monthly_sales_labels = list(months_data.keys())
    monthly_sales_data = [d['sales'] for d in months_data.values()]
    monthly_returns_data = [d['returns'] for d in months_data.values()]
    monthly_orders_query = monthly_sales_base_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(order_count=Count('id')).order_by('month')
    monthly_orders_labels = [data['month'].strftime('%b %Y') for data in monthly_orders_query]
    monthly_orders_data = [int(data['order_count']) for data in monthly_orders_query]


    context = {
        'period': period,
        'start_date': form_start_date,
        'end_date': form_end_date,
        'todays_sales': todays_gross_sales,
        'this_months_sales': this_months_gross_sales,
        'todays_gross_sales': todays_gross_sales,
        'todays_returns_total': todays_returns_total,
        'todays_net_sales': todays_net_sales,
        'this_months_gross_sales': this_months_gross_sales,
        'this_months_returns_total': this_months_returns_total,
        'this_months_net_sales': this_months_net_sales,
        'purchase_suggestion_count': purchase_suggestion_count,
        'dead_stock_count': dead_stock_count,
        'expiring_lots_count': expiring_lots_count,
        'total_profit': total_profit,
        'inventory_turnover_ratio': inventory_turnover_ratio,
        'avg_days_to_sell': avg_days_to_sell,
        'total_products': total_products,
        'in_stock_products': in_stock_count,
        'low_stock_products_count': low_stock_count,
        'out_of_stock_products': out_of_stock_count,
        'unfulfilled_orders_count': unfulfilled_orders_count,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'monthly_sales_labels': json.dumps(monthly_sales_labels),
        'monthly_sales_data': json.dumps(monthly_sales_data),
        'monthly_returns_data': json.dumps(monthly_returns_data),
        'monthly_orders_labels': json.dumps(monthly_orders_labels),
        'monthly_orders_data': json.dumps(monthly_orders_data),
        'DEFAULT_CURRENCY_SYMBOL': DEFAULT_CURRENCY_SYMBOL,
        'title': 'Dashboard'
    }
    return render(request, 'dashboard.html', context)

@login_required
def home(request):
    return redirect('dashboard')
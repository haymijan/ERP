# sales/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Sum, Q, F, Count
from django.core.paginator import Paginator
from django.contrib import messages
from django.forms import formset_factory, inlineformset_factory
from datetime import timedelta
import json
from io import BytesIO
import os
from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from reportlab.pdfgen import canvas

from .forms import SalesOrderFilterForm
from .models import SalesOrder, SalesOrderItem, SalesReturn, SalesReturnItem
from stock.models import InventoryTransaction, LotSerialNumber, Location, Stock
from .forms import (
    SalesOrderForm,
    SalesOrderItemFormSet,
    SalesOrderItemFulfillmentForm,
    SalesOrderItemFulfillmentFormSet,
    FindSalesOrderForm,
    SalesReturnForm,
    SalesReturnItemFormSet,
    SalesReturnItemForm
)
from products.models import Product
from partners.forms import CustomerForm
from partners.models import Customer
from stock.forms import DateRangeForm
from stock.services import StockService

DEFAULT_CURRENCY_SYMBOL = 'QAR '

def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.drawString(doc.leftMargin, inch / 2, text)


def apply_sales_order_filters(queryset, request):
    form = DateRangeForm(request.GET or None)
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        status = request.GET.get('status')
        order_number = request.GET.get('order_number')

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            end_date_inclusive = end_date + timedelta(days=1)
            queryset = queryset.filter(created_at__date__lt=end_date_inclusive)
        if status:
            queryset = queryset.filter(status=status)
        if order_number:
            queryset = queryset.filter(pk=order_number)
    return queryset, form

@login_required
@permission_required('sales.view_salesorder', login_url='/admin/')
def sales_order_list(request):
    sales_orders_list = SalesOrder.objects.select_related('customer', 'user', 'warehouse').order_by('-created_at')
    
    user = request.user
    if not user.is_superuser:
        user_warehouse = getattr(user, 'warehouse', None)
        if user_warehouse:
            sales_orders_list = sales_orders_list.filter(warehouse=user_warehouse)
    
    filter_param = request.GET.get('filter')
    if filter_param == 'unfulfilled':
        sales_orders_list = sales_orders_list.filter(
            Q(status='confirmed')
        )

    form = SalesOrderFilterForm(request.GET, user=user) 
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        order_number = form.cleaned_data.get('order_number')
        selected_user = form.cleaned_data.get('user')
        warehouse = form.cleaned_data.get('warehouse')

        if start_date:
            sales_orders_list = sales_orders_list.filter(created_at__date__gte=start_date)
        if end_date:
            sales_orders_list = sales_orders_list.filter(created_at__date__lte=end_date)
        if order_number and order_number.isdigit():
            sales_orders_list = sales_orders_list.filter(pk=order_number)
        if selected_user:
            sales_orders_list = sales_orders_list.filter(user=selected_user)
        if warehouse and user.is_superuser:
            sales_orders_list = sales_orders_list.filter(warehouse=warehouse)
    
    paginator = Paginator(sales_orders_list, 15)
    page_number = request.GET.get('page')
    sales_orders = paginator.get_page(page_number)

    context = {
        'title': 'Sales Orders',
        'sales_orders': sales_orders,
        'form': form,
    }
    return render(request, 'sales/sales_order_list.html', context)

@login_required
@permission_required('sales.view_salesorder', login_url='/admin/')
def sales_order_detail(request, pk):
    sales_order = get_object_or_404(
        SalesOrder.objects.prefetch_related(
            'salesreturn_set__items__product'
        ), 
        pk=pk
    )
    
    associated_returns = sales_order.salesreturn_set.all()

    context = {
        'title': f'Sales Order #{sales_order.pk}',
        'sales_order': sales_order,
        'associated_returns': associated_returns,
    }
    return render(request, 'sales/sales_order_detail.html', context)

@login_required
@permission_required('sales.add_salesorder', login_url='/admin/')
def create_sales_order(request):
    user_warehouse = getattr(request.user, 'warehouse', None)
    
    sales_order_form = SalesOrderForm(request.POST or None, user=request.user)
    item_formset = SalesOrderItemFormSet(
        request.POST or None,
        prefix='items',
        form_kwargs={'user': request.user, 'warehouse': user_warehouse}
    )
    customer_form = CustomerForm()

    if request.method == 'POST':
        if sales_order_form.is_valid() and item_formset.is_valid():
            try:
                with transaction.atomic():
                    sales_order = sales_order_form.save(commit=False)
                    sales_order.user = request.user
                    
                    # --- শুধুমাত্র এই অংশটি যোগ করা হয়েছে ---
                    # যদি ব্যবহারকারী সুপারইউজার না হন, তাহলে স্বয়ংক্রিয়ভাবে তার ব্রাঞ্চ যুক্ত হবে।
                    # আপনার কোডে এটি আগে থেকেই ছিল, আমি শুধু নিশ্চিত করছি এটি সঠিক জায়গায় আছে।
                    if not request.user.is_superuser:
                        sales_order.warehouse = user_warehouse
                    # --- পরিবর্তন শেষ ---

                    sales_order.save()

                    items = item_formset.save(commit=False)
                    total_amount = 0
                    for item in items:
                        item.sales_order = sales_order
                        item.cost_price = item.product.cost_price
                        item.save()
                        total_amount += item.subtotal

                    sales_order.total_amount = total_amount
                    sales_order.save(update_fields=['total_amount'])

                    # আপনার স্টক ডেলিভারির লজিক
                    if sales_order.status in ['delivered', 'partially_delivered']:
                        if not sales_order.warehouse:
                                raise ValidationError("Cannot fulfill order: No warehouse assigned to the order.")

                        for item in sales_order.items.all():
                            product = item.product
                            quantity_to_sell = item.quantity
                            
                            available_lots = LotSerialNumber.objects.filter(
                                product=product,
                                location__warehouse=sales_order.warehouse,
                                quantity__gt=0
                            ).order_by('expiration_date', 'created_at')

                            if (available_lots.aggregate(total=Sum('quantity'))['total'] or 0) < quantity_to_sell:
                                raise ValidationError(f"Insufficient stock for {product.name} in {sales_order.warehouse.name}. Cannot complete delivery.")

                            remaining_qty_to_sell = quantity_to_sell
                            for lot in available_lots:
                                if remaining_qty_to_sell <= 0: break
                                
                                qty_from_this_lot = min(lot.quantity, remaining_qty_to_sell)

                                StockService.change_stock(
                                    product=product,
                                    warehouse=sales_order.warehouse,
                                    quantity_change=-qty_from_this_lot,
                                    transaction_type='sale',
                                    user=request.user,
                                    content_object=sales_order,
                                    location=lot.location,
                                    lot_serial=lot,
                                    notes=f"Direct Sale from SO-{sales_order.id}"
                                )
                                remaining_qty_to_sell -= qty_from_this_lot
                            
                            first_lot_sold = available_lots.first()
                            if first_lot_sold:
                                item.lot_serial = first_lot_sold
                            
                            item.quantity_fulfilled = item.quantity
                            item.save()

                messages.success(request, f"Sales Order #{sales_order.pk} created and delivered successfully!")
                return redirect('sales:sales_order_detail', pk=sales_order.pk)
            except ValidationError as e:
                messages.error(request, e.message)
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
    
    context = {
        'title': 'Create Sales Order',
        'sales_order_form': sales_order_form,
        'item_formset': item_formset,
        'customer_form': customer_form,
    }
    return render(request, 'sales/create_sales_order.html', context)

@login_required
@permission_required('sales.change_salesorder', login_url='/admin/')
def edit_sales_order(request, pk):
    sales_order = get_object_or_404(SalesOrder, pk=pk)
    original_status = sales_order.status
    
    sales_order_form = SalesOrderForm(request.POST or None, instance=sales_order)
    item_formset = SalesOrderItemFormSet(
        request.POST or None,
        instance=sales_order,
        prefix='items',
        form_kwargs={'user': request.user}
    )
    
    if request.method == 'POST':
        if sales_order_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                sales_order = sales_order_form.save()
                item_formset.save()
                
                total_amount = sum(item.subtotal for item in sales_order.items.all())
                sales_order.total_amount = total_amount
                sales_order.save(update_fields=['total_amount'])
                
                if sales_order.status == 'delivered' and original_status != 'delivered':
                    user_warehouse = sales_order.warehouse
                    if not user_warehouse:
                        raise Exception("Cannot fulfill order: No warehouse assigned.")

                    for item in sales_order.items.all():
                        if item.quantity_fulfilled < item.quantity:
                            product = item.product
                            quantity_to_fulfill = item.quantity - item.quantity_fulfilled
                            
                            if product.tracking_method in ['lot', 'serial']:
                                available_lots = LotSerialNumber.objects.filter(
                                    product=product,
                                    location__warehouse=user_warehouse,
                                    quantity__gt=0
                                ).order_by('created_at')

                                for lot in available_lots:
                                    if quantity_to_fulfill <= 0: break
                                    quantity_from_this_lot = min(lot.quantity, quantity_to_fulfill)
                                    InventoryTransaction.objects.create(
                                        user=request.user,
                                        product=product, transaction_type='sale',
                                        quantity=quantity_from_this_lot,
                                        source_location=lot.location, lot_serial=lot,
                                        notes=f"Sale from updated SO-{sales_order.id}"
                                    )
                                    quantity_to_fulfill -= quantity_from_this_lot
                            else:
                                stock_record = Stock.objects.filter(product=product, location__warehouse=user_warehouse, quantity__gte=quantity_to_fulfill).first()
                                if not stock_record:
                                    raise Exception(f"Insufficient stock for {product.name}.")
                                InventoryTransaction.objects.create(
                                    user=request.user,
                                    product=product, transaction_type='sale',
                                    quantity=quantity_to_fulfill,
                                    source_location=stock_record.location,
                                    notes=f"Sale from updated SO-{sales_order.id}"
                                )
                            
                            item.quantity_fulfilled = item.quantity
                            item.save()

            messages.success(request, f"Sales Order #{sales_order.pk} updated successfully!")
            return redirect('sales:sales_order_detail', pk=sales_order.pk)

    context = {
        'title': f'Edit Sales Order #{sales_order.pk}',
        'sales_order_form': sales_order_form,
        'formset': item_formset,
    }
    return render(request, 'sales/edit_sales_order.html', context)


@login_required
@permission_required('sales.delete_salesorder', login_url='/admin/')
def delete_sales_order(request, pk):
    sales_order = get_object_or_404(SalesOrder, pk=pk)
    if request.method == 'POST':
        sales_order.delete()
        messages.success(request, f"Sales Order {pk} deleted successfully!")
        return redirect('sales:sales_order_list')
    context = {'sales_order': sales_order}
    return render(request, 'sales/confirm_delete.html', context)


@login_required
@permission_required('sales.change_salesorder', login_url='/admin/')
def fulfill_sales_order(request, pk):
    sales_order = get_object_or_404(SalesOrder.objects.prefetch_related('items__product'), pk=pk)
    sales_order_items = sales_order.items.filter(quantity__gt=F('quantity_fulfilled'))

    if not sales_order_items.exists() or sales_order.status == 'delivered':
        messages.info(request, "This order is already fulfilled or has no items to fulfill.")
        return redirect('sales:sales_order_detail', pk=pk)

    SalesOrderItemFulfillmentFormSet = formset_factory(SalesOrderItemFulfillmentForm, extra=0)

    if request.method == 'POST':
        formset = SalesOrderItemFulfillmentFormSet(request.POST, prefix='form')

        # --- আপনার পুরোনো কোডের গুরুত্বপূর্ণ অংশটি এখানে অপরিবর্তিত আছে ---
        for i, form in enumerate(formset.forms):
            item_id = form.data.get(f'form-{i}-sales_order_item_id')
            if item_id:
                try:
                    item = sales_order.items.get(id=item_id)
                    product = item.product
                    
                    warehouses_with_stock_ids = Stock.objects.filter(
                        product=product, quantity__gt=0
                    ).values_list('warehouse_id', flat=True)
                    locations_queryset = Location.objects.filter(warehouse_id__in=warehouses_with_stock_ids)

                    if not request.user.is_superuser:
                        user_warehouse = getattr(request.user, 'warehouse', None)
                        locations_queryset = locations_queryset.filter(warehouse=user_warehouse) if user_warehouse else Location.objects.none()
                    
                    form.fields['source_location'].queryset = locations_queryset.distinct()
                    
                    if product.tracking_method in ['lot', 'serial']:
                        location_id = form.data.get(f'form-{i}-source_location')
                        if location_id:
                            lot_queryset = LotSerialNumber.objects.filter(
                                product=product, location_id=location_id, quantity__gt=0
                            ).order_by('created_at')
                            form.fields['lot_serial'].queryset = lot_queryset
                except SalesOrderItem.DoesNotExist:
                    continue
        # --- পুরোনো কোডের অংশ শেষ ---

        if formset.is_valid():
            try:
                with transaction.atomic():
                    for form in formset:
                        cleaned_data = form.cleaned_data
                        quantity_to_fulfill = cleaned_data.get('quantity_fulfilled', 0)
                        
                        if quantity_to_fulfill > 0:
                            item = SalesOrderItem.objects.get(id=cleaned_data['sales_order_item_id'])
                            source_loc = cleaned_data['source_location']
                            lot_serial_obj = cleaned_data.get('lot_serial')

                            item.lot_serial = lot_serial_obj
                            item.quantity_fulfilled = F('quantity_fulfilled') + quantity_to_fulfill
                            item.save()

                            StockService.change_stock(
                                product=item.product,
                                warehouse=source_loc.warehouse,
                                quantity_change=-quantity_to_fulfill,
                                transaction_type='sale',
                                user=request.user,
                                content_object=sales_order,
                                location=source_loc,
                                lot_serial=lot_serial_obj
                            )
                    
                    sales_order.refresh_from_db()
                    total_ordered = sales_order.items.aggregate(total=Sum('quantity'))['total'] or 0
                    total_fulfilled = sales_order.items.aggregate(total=Sum('quantity_fulfilled'))['total'] or 0
                    
                    # --- পরিবর্তন: স্ট্যাটাস আপডেটের লজিক ---
                    if total_fulfilled >= total_ordered:
                        sales_order.status = 'delivered'
                        messages.success(request, "Order fulfilled successfully!")
                    # 'partially_delivered' এর 'elif' ব্লকটি এখান থেকে মুছে ফেলা হয়েছে।
                    # যদি অর্ডার পুরোপুরি ডেলিভারি না হয়, স্ট্যাটাস আগের মতোই ('confirmed') থাকবে।
                    
                    sales_order.save(update_fields=['status'])
                    # --- পরিবর্তন শেষ ---
                    return redirect('sales:sales_order_detail', pk=sales_order.pk)

            except (ValidationError, ValueError, Exception) as e:
                messages.error(request, f"An error occurred: {e}")
    
    else:  # GET Request
        initial_data = [{'sales_order_item_id': i.id, 'quantity_fulfilled': i.quantity - (i.quantity_fulfilled or 0)} for i in sales_order_items]
        formset = SalesOrderItemFulfillmentFormSet(initial=initial_data, prefix='form')
        for form, item in zip(formset.forms, sales_order_items):
            product = item.product
            
            warehouses_with_stock_ids = Stock.objects.filter(
                product=product, quantity__gt=0
            ).values_list('warehouse_id', flat=True)
            locations_queryset = Location.objects.filter(warehouse_id__in=warehouses_with_stock_ids)

            if not request.user.is_superuser:
                user_warehouse = getattr(request.user, 'warehouse', None)
                locations_queryset = locations_queryset.filter(warehouse=user_warehouse) if user_warehouse else Location.objects.none()
            
            form.fields['source_location'].queryset = locations_queryset.distinct()
            
            if not product.tracking_method in ['lot', 'serial']:
                form.fields['lot_serial'].widget = forms.HiddenInput()

    form_and_items = zip(formset.forms, sales_order_items)
    context = {'sales_order': sales_order, 'form_and_items': form_and_items, 'formset': formset, 'title': f'Fulfill Sales Order #{sales_order.pk}'}
    return render(request, 'sales/fulfill_sales_order.html', context)

@login_required
def get_lots_by_location_and_product(request):
    product_id = request.GET.get('product_id')
    location_id = request.GET.get('location_id')
    
    if not product_id or not location_id:
        return JsonResponse([], safe=False)

    lots_queryset = LotSerialNumber.objects.filter(product_id=product_id, location_id=location_id, quantity__gt=0)
    
    if not request.user.is_superuser:
        user_warehouse = getattr(request.user, 'warehouse', None)
        if user_warehouse:
            try:
                selected_location = Location.objects.get(id=location_id, warehouse=user_warehouse)
                lots_queryset = lots_queryset.filter(location=selected_location)
            except Location.DoesNotExist:
                return JsonResponse([], safe=False)
        else:
            return JsonResponse([], safe=False)
            
    lots_data = list(lots_queryset.values('id', 'lot_number', 'quantity'))
    return JsonResponse(lots_data, safe=False)

@login_required
def get_product_sale_price_ajax(request):
    """
    AJAX endpoint to get the sale price of a product.
    """
    product_id = request.GET.get('product_id')
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
            return JsonResponse({'sale_price': product.sale_price})
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


# --- পিডিএফ তৈরির জন্য একটি Helper Class (ঐচ্ছিক কিন্তু পরিচ্ছন্ন কোডের জন্য ভালো) ---
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.drawRightString(200*mm, 20*mm, f"Page {self._pageNumber} of {page_count}")


@login_required
@permission_required('sales.view_salesorder', raise_exception=True)
def export_sales_order_pdf(request, pk):
    sales_order = get_object_or_404(SalesOrder, pk=pk)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="SO-{sales_order.pk}_{sales_order.customer.name if sales_order.customer else "Walk-in"}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    # --- কাস্টম স্টাইল তৈরি ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=22, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.HexColor("#444444")))
    styles.add(ParagraphStyle(name='CompanyInfo', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT, leading=12))
    styles.add(ParagraphStyle(name='CustomerInfo', fontSize=10, fontName='Helvetica', leading=14)) # leading বাড়ানো হয়েছে
    styles.add(ParagraphStyle(name='HeaderStyle', fontSize=10, fontName='Helvetica-Bold', alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='TotalHeaderStyle', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='SignatureStyle', fontSize=10, fontName='Helvetica', alignment=TA_CENTER))
    # --- নতুন বোল্ড স্টাইল যোগ করা হলো ---
    styles.add(ParagraphStyle(name='BoldText', fontName='Helvetica-Bold'))


    # --- ১. হেডার: লোগো এবং কোম্পানির তথ্য ---
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'logo.png')
    logo = Image(logo_path, width=1.8*inch, height=0.5*inch)
    
    company_info = """
    <b>NOVO ERP Solutions</b><br/>
    Doha, Qatar<br/>
    Email: haymijan@gmail.com<br/>
    Phone: +974 502 902 83
    """
    
    header_data = [[logo, Paragraph("SALES ORDER", styles['TitleStyle'])]]
    header_table = Table(header_data, colWidths=[4*inch, 3.5*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(company_info, styles['CompanyInfo']))

    story.append(Spacer(1, 0.5*inch))

    # --- ২. গ্রাহকের তথ্য এবং অর্ডারের বিবরণ ---
    customer_name = sales_order.customer.name if sales_order.customer else "Walk-in Customer"
    # --- AttributeError সমাধান: getattr ব্যবহার করে ফোন নম্বর নিরাপদে আনা হয়েছে ---
    customer_phone = getattr(sales_order.customer, 'phone_number', '') or getattr(sales_order.customer, 'phone', '')
    
    customer_details = f"""
    <b>BILLED TO:</b><br/>
    {customer_name}<br/>
    {sales_order.customer.address if sales_order.customer and sales_order.customer.address else ''}<br/>
    {sales_order.customer.email if sales_order.customer and sales_order.customer.email else ''}<br/>
    {customer_phone}
    """
    
    order_details_data = [
        ['Order #:', f'SO-{sales_order.pk}'],
        ['Order Date:', sales_order.order_date.strftime('%d %b, %Y')],
        # --- PDF গঠন সমাধান: Paragraph এবং নতুন স্টাইল ব্যবহার করা হলো ---
        [Paragraph('Status:', styles['Normal']), Paragraph(sales_order.get_status_display(), styles['BoldText'])],
    ]
    order_details_table = Table(order_details_data, colWidths=[0.8*inch, 1.5*inch], style=[('ALIGN', (0,0), (-1,-1), 'LEFT')])

    customer_table_data = [[Paragraph(customer_details, styles['CustomerInfo']), order_details_table]]
    customer_table = Table(customer_table_data, colWidths=[4*inch, 3*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    story.append(customer_table)

    story.append(Spacer(1, 0.4*inch))

    # --- ৩. আইটেম টেবিল ---
    items_header = ['#', 'ITEM DESCRIPTION', 'QTY', 'UNIT PRICE', 'TOTAL']
    items_data = [items_header]
    
    for i, item in enumerate(sales_order.items.all(), 1):
        items_data.append([
            i,
            Paragraph(item.product.name, styles['Normal']),
            item.quantity,
            f"{item.unit_price:,.2f}",
            f"{item.subtotal:,.2f}"
        ])

    # --- PDF গঠন সমাধান: Paragraph এবং নতুন স্টাইল ব্যবহার করা হলো ---
    grand_total_text = f"{DEFAULT_CURRENCY_SYMBOL} {sales_order.total_amount:,.2f}"
    items_data.append(['', '', '', Paragraph('Subtotal', styles['TotalHeaderStyle']), f"{sales_order.total_amount:,.2f}"])
    items_data.append(['', '', '', Paragraph('Grand Total', styles['TotalHeaderStyle']), Paragraph(grand_total_text, styles['BoldText'])])

    items_table = Table(items_data, colWidths=[0.4*inch, 3.6*inch, 0.7*inch, 1.1*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E0E5F2")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2B3674")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-3), 1, colors.HexColor("#E0E5F2")),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (3,-2), (-1,-1), 1, colors.HexColor("#E0E5F2")),
        ('ALIGN', (4,-1), (4,-1), 'RIGHT'), # Grand Total ডানদিকে অ্যালাইন করা হয়েছে
        ('SPAN', (0, -2), (2, -2)),
        ('SPAN', (0, -1), (2, -1)),
    ]))
    story.append(items_table)

    story.append(Spacer(1, 0.8*inch))

    # --- ৪. নোট এবং শর্তাবলী ---
    story.append(Paragraph("<b>Notes / Terms & Conditions:</b>", styles['HeaderStyle']))
    story.append(Paragraph("1. Please check all items upon delivery. Goods once sold are not returnable unless there is a manufacturing defect.", styles['CustomerInfo']))
    story.append(Paragraph("2. Payment to be made within 15 days of the invoice date.", styles['CustomerInfo']))

    story.append(Spacer(1, 1.2*inch))

    # --- ৫. সিগনেচার সেকশন ---
    signature_data = [
        [Paragraph('--------------------------------<br/>Authorized Signature', styles['SignatureStyle']),
         Paragraph('--------------------------------<br/>Customer Signature', styles['SignatureStyle'])]
    ]
    signature_table = Table(signature_data, colWidths=[3.5*inch, 3.5*inch], hAlign='CENTER')
    story.append(signature_table)

    doc.build(story)
    return response


@login_required
@permission_required('sales.add_salesreturn', login_url='/admin/')
def create_sales_return(request):
    find_order_form = FindSalesOrderForm(request.GET or None)
    sales_order = None
    
    if 'order_id' in request.GET and find_order_form.is_valid():
        order_id = find_order_form.cleaned_data['order_id']
        try:
            query = SalesOrder.objects.select_related('customer', 'warehouse').prefetch_related('items__product', 'items__lot_serial')
            
            if not request.user.is_superuser:
                user_warehouse = getattr(request.user, 'warehouse', None)
                if user_warehouse:
                    query = query.filter(warehouse=user_warehouse)

            sales_order = query.get(pk=order_id, status='delivered')

        except SalesOrder.DoesNotExist:
            messages.error(request, f"Delivered Sales Order with ID #{order_id} not found in your branch.")

    if sales_order:
        sales_return_instance = SalesReturn(sales_order=sales_order)

        if request.method == 'POST':
            return_form = SalesReturnForm(request.POST, instance=sales_return_instance)
            item_formset = SalesReturnItemFormSet(request.POST, instance=sales_return_instance, prefix='items')
            
            # Formset-এর প্রতিটি ফর্মের সাথে মূল সেলস অর্ডার আইটেমটি যোগ করা হচ্ছে
            for i, form in enumerate(item_formset.forms):
                sales_items_list = list(sales_order.items.all())
                if i < len(sales_items_list):
                    form.sales_order_item = sales_items_list[i]
        
        else: # GET Request
            initial_data = []
            for item in sales_order.items.all():
                initial_data.append({'product': item.product, 'lot_serial': item.lot_serial, 'quantity': 0})
            
            SalesReturnItemFormSet_Initial = inlineformset_factory(SalesReturn, SalesReturnItem, form=SalesReturnItemForm, extra=len(initial_data), can_delete=False)
            item_formset = SalesReturnItemFormSet_Initial(instance=sales_return_instance, initial=initial_data, prefix='items')
            
            for i, form in enumerate(item_formset.forms):
                sales_items_list = list(sales_order.items.all())
                if i < len(sales_items_list):
                    form.sales_order_item = sales_items_list[i]
            
            return_form = SalesReturnForm(instance=sales_return_instance)

        if request.method == 'POST':
            if return_form.is_valid() and item_formset.is_valid():
                total_items_returned = sum(1 for form in item_formset if form.cleaned_data.get('quantity', 0) > 0)

                if total_items_returned == 0:
                    messages.error(request, "You must specify a return quantity for at least one item.")
                else:
                    try:
                        with transaction.atomic():
                            sales_return = return_form.save(commit=False)
                            sales_return.customer = sales_order.customer
                            sales_return.user = request.user
                            sales_return.warehouse = sales_order.warehouse
                            sales_return.save()

                            item_formset.instance = sales_return
                            returned_items = item_formset.save(commit=False)
                            
                            total_return_amount = 0
                            for item in returned_items:
                                if item.quantity > 0:
                                    # --- মূল পরিবর্তন: মূল সেলস আইটেম থেকে unit_price নেওয়া এবং যোগ করা ---
                                    original_item = SalesOrderItem.objects.get(product=item.product, sales_order=sales_order, lot_serial=item.lot_serial)
                                    item.unit_price = original_item.unit_price
                                    item.save()
                                    total_return_amount += item.subtotal
                                    # --- পরিবর্তন শেষ ---

                                    StockService.change_stock(
                                        product=item.product,
                                        warehouse=sales_return.warehouse,
                                        quantity_change=item.quantity,
                                        transaction_type='sale_return',
                                        user=request.user,
                                        content_object=sales_return,
                                        location=item.lot_serial.location if item.lot_serial else sales_return.warehouse.locations.first(), 
                                        lot_serial=item.lot_serial,
                                        notes=f"Return for SO-{sales_order.id}"
                                    )
                            
                            sales_return.total_amount = total_return_amount
                            sales_return.save()
                        
                        messages.success(request, f"Sales return for SO-{sales_order.id} has been processed successfully.")
                        return redirect('sales:sales_order_list')

                    except Exception as e:
                        messages.error(request, f"An error occurred: {e}")

        context = {
            'title': f'Process Return for SO-#{sales_order.id}',
            'sales_order': sales_order,
            'return_form': return_form,
            'item_formset': item_formset,
        }
        return render(request, 'sales/create_sales_return.html', context)
    
    context = {
        'title': 'Create Sales Return',
        'find_order_form': find_order_form,
    }
    return render(request, 'sales/create_sales_return.html', context)
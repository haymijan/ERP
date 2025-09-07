# purchase/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Sum, Q, F, Count
from django.core.paginator import Paginator
from django.contrib import messages
from django.forms import formset_factory
from datetime import timedelta
import json
from io import BytesIO
import os
from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model


from .models import PurchaseOrder, PurchaseOrderItem, ProductSupplier, StockTransferRequest
from stock.models import InventoryTransaction, LotSerialNumber, Location, Warehouse, Stock
from stock.services import StockService
from .forms import StockTransferFilterForm

from .forms import (
    PurchaseOrderForm, PurchaseOrderItemFormSet, DateRangeForm,
    PurchaseReceiveItemForm, ApproveForm, ApproveOrderItemFormSet,
    StockTransferRequestForm,
    ReceiveStockTransferForm,
    ProcessStockTransferForm
)
from products.models import Product
from partners.forms import SupplierForm
from partners.models import Supplier

User = get_user_model()

DEFAULT_CURRENCY_SYMBOL = 'QAR '

def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.drawString(doc.leftMargin, inch / 2, text)

def apply_purchase_order_filters(queryset, request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    status = request.GET.get('status')
    user_id = request.GET.get('user')  # <-- নতুন ফিল্টার
    warehouse_id = request.GET.get('warehouse')  # <-- নতুন ফিল্টার

    if start_date_str:
        start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d')
        queryset = queryset.filter(order_date__gte=start_date)
    if end_date_str:
        end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        queryset = queryset.filter(order_date__lt=end_date)
    if status:
        queryset = queryset.filter(status=status)
    if user_id:  # <-- নতুন ফিল্টারিং লজিক
        queryset = queryset.filter(user_id=user_id)
    if warehouse_id: # <-- নতুন ফিল্টারিং লজিক
        queryset = queryset.filter(warehouse_id=warehouse_id)
        
    return queryset

@login_required
@permission_required('purchase.view_purchaseorder', login_url='/admin/')
def purchase_order_list(request):
    purchase_orders_list = PurchaseOrder.objects.select_related('supplier', 'user', 'warehouse').all().order_by('-order_date')

    if not request.user.is_superuser:
        user_warehouse = getattr(request.user, 'warehouse', None)
        if user_warehouse:
            purchase_orders_list = purchase_orders_list.filter(warehouse=user_warehouse)
        else:
            purchase_orders_list = PurchaseOrder.objects.none()
    
    # এখানে ফিল্টার ফাংশনটি আপডেট করা হয়েছে
    purchase_orders_list = apply_purchase_order_filters(purchase_orders_list, request)

    paginator = Paginator(purchase_orders_list, 10)
    page_number = request.GET.get('page')
    purchase_orders = paginator.get_page(page_number)

    # এখানে context-এ ইউজার এবং ওয়্যারহাউজ যুক্ত করা হয়েছে
    context = {
        'purchase_orders': purchase_orders, 'title': 'All Purchase Orders',
        'DEFAULT_CURRENCY_SYMBOL': 'QAR',
        'users': User.objects.all(),
        'warehouses': Warehouse.objects.all(),
        'status_choices': PurchaseOrder.STATUS_CHOICES,
    }
    return render(request, 'purchase/purchase_order_list.html', context)

@login_required
@permission_required('purchase.add_purchaseorder', login_url='/admin/')
def create_purchase_order(request):
    po_form_class = PurchaseOrderForm
    if not request.user.is_superuser:
        class BranchPurchaseOrderForm(PurchaseOrderForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                del self.fields['supplier']
                self.fields['status'].initial = 'purchase_request'
        po_form_class = BranchPurchaseOrderForm
    
    po_form = po_form_class(request.POST or None)
    formset = PurchaseOrderItemFormSet(request.POST or None, prefix='items', queryset=PurchaseOrderItem.objects.none())
    supplier_form = SupplierForm(request.POST or None)  # <-- নতুন সাপ্লায়ার ফর্ম এখানে তৈরি করা হয়েছে

    if request.method == 'POST':
        if po_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                purchase_order = po_form.save(commit=False)
                purchase_order.user = request.user
                
                if not request.user.is_superuser:
                    purchase_order.warehouse = getattr(request.user, 'warehouse', None)
                    purchase_order.status = 'purchase_request'
                    purchase_order.supplier = None
                else:
                    purchase_order.status = 'draft'
                
                purchase_order.save()
                
                formset.instance = purchase_order
                formset.save()
            messages.success(request, f"Purchase Order PO-{purchase_order.pk} created successfully!")
            return redirect('purchase:purchase_order_detail', pk=purchase_order.pk)
    else:
        initial_data = {
            'user': request.user,
            'warehouse': getattr(request.user, 'warehouse', None),
        }
        po_form = po_form_class(initial=initial_data)
        formset = PurchaseOrderItemFormSet(prefix='items', queryset=PurchaseOrderItem.objects.none())

    context = {
        'po_form': po_form,
        'formset': formset,
        'supplier_form': supplier_form,  # <-- context-এ নতুন সাপ্লায়ার ফর্ম যোগ করা হয়েছে
        'title': 'Create New Purchase Order',
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'purchase/create_purchase_order.html', context)


@login_required
@permission_required('purchase.view_purchaseorder', login_url='/admin/')
def purchase_order_detail(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product'), pk=pk)
    
    items_qs = purchase_order.items.all().select_related('product').exclude(product__isnull=True)
    
    approve_form = ApproveForm(request.POST or None, initial={'supplier': purchase_order.supplier})
    approve_formset = ApproveOrderItemFormSet(request.POST or None, queryset=items_qs, prefix='items')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve_request' and request.user.is_superuser:
            if purchase_order.status == 'purchase_request' and approve_form.is_valid() and approve_formset.is_valid():
                supplier = approve_form.cleaned_data['supplier']
                with transaction.atomic():
                    purchase_order.supplier = supplier
                    purchase_order.status = 'confirmed'
                    approve_formset.save()
                    total_amount = sum(item.total_price for item in items_qs)
                    purchase_order.total_amount = total_amount
                    purchase_order.save(update_fields=['supplier', 'status', 'total_amount'])
                messages.success(request, f"Purchase Request PO-{purchase_order.pk} has been approved and confirmed.")
                return redirect('purchase:purchase_order_detail', pk=purchase_order.pk)
            else:
                 messages.error(request, "Please correct the errors below.")
                 if approve_form.errors:
                     messages.error(request, f"Supplier Form Error: {approve_form.errors}")
                 if approve_formset.errors:
                     for i, errors in enumerate(approve_formset.errors):
                         if errors:
                             messages.error(request, f"Item {i+1} Errors: {errors.as_text()}")
        
        elif action == 'confirm' and request.user.is_superuser:
            if purchase_order.status in ['draft']:
                purchase_order.status = 'confirmed'
                purchase_order.save()
                messages.success(request, f"Purchase Order PO-{purchase_order.pk} has been confirmed.")
                return redirect('purchase:purchase_order_detail', pk=purchase_order.pk)
        elif action == 'cancel':
            if purchase_order.status not in ['received', 'cancelled']:
                purchase_order.status = 'cancelled'
                purchase_order.save()
                messages.warning(request, f"Purchase Order PO-{purchase_order.pk} has been cancelled.")
                return redirect('purchase:purchase_order_detail', pk=purchase_order.pk)

    context = {
        'purchase_order': purchase_order, 
        'title': f'Purchase Order: PO-{purchase_order.id}', 
        'DEFAULT_CURRENCY_SYMBOL': DEFAULT_CURRENCY_SYMBOL,
        'approve_form': approve_form,
        'approve_formset': approve_formset,
    }
    return render(request, 'purchase/purchase_order_detail.html', context)

@login_required
@permission_required('purchase.change_purchaseorder', login_url='/admin/')
def edit_purchase_order(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if purchase_order.status not in ['draft', 'purchase_request']:
        messages.error(request, f"Cannot edit a {purchase_order.get_status_display()} purchase order.")
        return redirect('purchase:purchase_order_detail', pk=pk)
    
    if request.user.is_superuser:
        po_form = PurchaseOrderForm(request.POST or None, instance=purchase_order)
    else:
        # ব্রাঞ্চ ম্যানেজারের জন্য supplier ফিল্ডটি বাদ দেওয়া হয়েছে
        class BranchPurchaseOrderForm(PurchaseOrderForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                del self.fields['supplier']
        po_form = BranchPurchaseOrderForm(request.POST or None, instance=purchase_order)

    formset = PurchaseOrderItemFormSet(request.POST or None, instance=purchase_order, prefix='items')
    
    if request.method == 'POST':
        if po_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                po_form.save()
                formset.save()
            return redirect('purchase:purchase_order_detail', pk=pk)
    else:
        po_form = PurchaseOrderForm(instance=purchase_order)
        if not request.user.is_superuser:
            po_form = BranchPurchaseOrderForm(instance=purchase_order)

        formset = PurchaseOrderItemFormSet(instance=purchase_order, prefix='items')
        
    context = {
        'po_form': po_form, 
        'formset': formset, 
        'title': f'Edit Purchase Order: PO-{purchase_order.id}',
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'purchase/edit_purchase_order.html', context)


@login_required
@permission_required('purchase.view_purchaseorder', raise_exception=True)
def export_single_purchase_order_pdf(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder.objects.select_related('supplier', 'warehouse', 'user'), pk=pk)
    supplier_name_for_file = purchase_order.supplier.name if purchase_order.supplier else "No_Supplier"
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="PO-{purchase_order.pk}_{supplier_name_for_file}.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    # --- কাস্টম স্টাইল ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=22, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.HexColor("#2B3674")))
    styles.add(ParagraphStyle(name='CompanyInfo', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT, leading=12))
    styles.add(ParagraphStyle(name='SupplierInfo', fontSize=10, fontName='Helvetica', leading=14))
    styles.add(ParagraphStyle(name='HeaderStyle', fontSize=10, fontName='Helvetica-Bold', alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='TotalHeaderStyle', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='SignatureStyle', fontSize=10, fontName='Helvetica', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='BoldText', fontName='Helvetica-Bold'))

    # --- ১. হেডার: লোগো এবং কোম্পানির তথ্য ---
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'logo.png')
    logo = Image(logo_path, width=1.5*inch, height=0.5*inch)
    company_info = "<b>NOVO ERP Solutions</b><br/>Doha, Qatar"
    
    header_data = [[logo, Paragraph("PURCHASE ORDER", styles['TitleStyle'])]]
    # --- মূল পরিবর্তন: কলামের প্রস্থ ঠিক করা হলো ---
    header_table = Table(header_data, colWidths=[3*inch, 4.5*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(company_info, styles['CompanyInfo']))
    story.append(Spacer(1, 0.5*inch))

    # --- ২. সরবরাহকারীর তথ্য এবং অর্ডারের বিবরণ ---
    if purchase_order.supplier:
        supplier_phone = getattr(purchase_order.supplier, 'phone', '')
        supplier_details = f"""
        <b>SUPPLIER:</b><br/>
        {purchase_order.supplier.name}<br/>
        {purchase_order.supplier.address or ''}<br/>
        {purchase_order.supplier.email or ''}<br/>
        {supplier_phone}
        """
    else:
        supplier_details = "<b>SUPPLIER:</b><br/>N/A"
    
    order_details_data = [
        [Paragraph('PO Number:', styles['Normal']), Paragraph(f'PO-{purchase_order.pk}', styles['BoldText'])],
        [Paragraph('Order Date:', styles['Normal']), Paragraph(purchase_order.order_date.strftime('%d %b, %Y'), styles['BoldText'])],
        [Paragraph('Status:', styles['Normal']), Paragraph(purchase_order.get_status_display(), styles['BoldText'])],
        [Paragraph('Branch:', styles['Normal']), Paragraph(purchase_order.warehouse.name if purchase_order.warehouse else 'N/A', styles['BoldText'])],
    ]
    order_details_table = Table(order_details_data, colWidths=[1*inch, 1.8*inch])

    supplier_table_data = [[Paragraph(supplier_details, styles['SupplierInfo']), order_details_table]]
    supplier_table = Table(supplier_table_data, colWidths=[4.5*inch, 3*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    story.append(supplier_table)
    story.append(Spacer(1, 0.4*inch))

    # --- ৩. আইটেম টেবিল ---
    items_header = ['#', 'ITEM DESCRIPTION', 'QTY', 'UNIT PRICE', 'TOTAL']
    items_data = [items_header]
    
    for i, item in enumerate(purchase_order.items.all(), 1):
        subtotal = item.quantity * item.unit_price
        items_data.append([i, item.product.name, item.quantity, f"{item.unit_price:,.2f}", f"{subtotal:,.2f}"])

    grand_total_text = f"{settings.DEFAULT_CURRENCY_SYMBOL} {purchase_order.total_amount:,.2f}"
    items_data.append(['', '', '', Paragraph('Grand Total', styles['TotalHeaderStyle']), Paragraph(grand_total_text, styles['BoldText'])])

    items_table = Table(items_data, colWidths=[0.4*inch, 3.6*inch, 0.7*inch, 1.1*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E0E5F2")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2B3674")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-2), 1, colors.HexColor("#CCCCCC")),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (3,-1), (-1,-1), 1, colors.HexColor("#CCCCCC")),
        ('SPAN', (0, -1), (2, -1)),
        ('ALIGN', (4,-1), (4,-1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 1.2*inch))

    # --- ৪. সিগনেচার সেকশন ---
    signature_data = [
        [Paragraph('--------------------------------<br/>Prepared By', styles['SignatureStyle']),
         Paragraph('--------------------------------<br/>Approved By', styles['SignatureStyle'])]
    ]
    signature_table = Table(signature_data, colWidths=[3.5*inch, 3.5*inch], hAlign='CENTER')
    story.append(signature_table)

    doc.build(story)
    
    buffer.seek(0)
    response.write(buffer.getvalue())
    return response


@login_required
@permission_required('purchase.view_purchaseorder', raise_exception=True)
def export_single_purchase_receipt_pdf(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder.objects.select_related('supplier', 'warehouse'), pk=pk)
    related_transactions = InventoryTransaction.objects.filter(
        notes__startswith=f"Received PO-{purchase_order.id}"
    ).select_related('product', 'lot_serial', 'lot_serial__location', 'destination_location')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="GRN-{purchase_order.pk}.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    # --- স্টাইল ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=22, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.HexColor("#2B3674")))
    styles.add(ParagraphStyle(name='CompanyInfo', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT, leading=12))
    styles.add(ParagraphStyle(name='SupplierInfo', fontSize=10, fontName='Helvetica', leading=14))
    styles.add(ParagraphStyle(name='SignatureStyle', fontSize=10, fontName='Helvetica', alignment=TA_CENTER))

    # --- ১. হেডার সেকশন ---
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'logo.png')
    logo = Image(logo_path, width=1.5*inch, height=0.5*inch)
    company_info = "<b>NOVO ERP Solutions</b><br/>Doha, Qatar"
    
    header_data = [[logo, Paragraph("Goods Received Note (GRN)", styles['TitleStyle'])]]
    header_table = Table(header_data, colWidths=[3*inch, 4.5*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(company_info, styles['CompanyInfo']))
    story.append(Spacer(1, 0.5*inch))
    
    # --- ২. রিসিট বিবরণ ---
    receipt_details_data = [
        [Paragraph('<b>Receipt Date:</b>', styles['Normal']), Paragraph(timezone.now().strftime('%d %b, %Y'), styles['Normal'])],
        [Paragraph('<b>PO Number:</b>', styles['Normal']), Paragraph(f'PO-{purchase_order.pk}', styles['Normal'])],
        [Paragraph('<b>Supplier:</b>', styles['Normal']), Paragraph(purchase_order.supplier.name if purchase_order.supplier else 'N/A', styles['Normal'])],
        [Paragraph('<b>Received At:</b>', styles['Normal']), Paragraph(purchase_order.warehouse.name if purchase_order.warehouse else 'N/A', styles['Normal'])],
    ]
    receipt_details_table = Table(receipt_details_data, colWidths=[1.2*inch, 6.3*inch])
    story.append(receipt_details_table)
    story.append(Spacer(1, 0.4*inch))

    # --- ৩. আইটেম টেবিল ---
    items_header = ['#', 'ITEM DESCRIPTION', 'RECEIVED QTY', 'DESTINATION', 'LOT/SERIAL', 'EXPIRY']
    items_data = [items_header]

    # --- মূল পরিবর্তন এখানে ---
    table_style_commands = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E0E5F2")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2B3674")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#CCCCCC")),
        ('ALIGN', (2,1), (2,-1), 'CENTER'),
        ('ALIGN', (5,1), (5,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]

    if not related_transactions.exists():
        # Paragraph থেকে colSpan সরানো হয়েছে
        items_data.append([Paragraph("No items have been marked as received for this order yet.", styles['Normal'])])
        # TableStyle-এ SPAN কমান্ড যোগ করা হয়েছে
        table_style_commands.append(('SPAN', (0, 1), (-1, 1)))
    else:
        for i, transaction in enumerate(related_transactions, 1):
            items_data.append([
                i,
                transaction.product.name,
                transaction.quantity,
                str(transaction.destination_location),
                str(transaction.lot_serial.lot_number) if transaction.lot_serial else "N/A",
                transaction.lot_serial.expiration_date.strftime('%d %b, %Y') if transaction.lot_serial and transaction.lot_serial.expiration_date else "N/A"
            ])
    
    items_table = Table(items_data, colWidths=[0.4*inch, 2.6*inch, 1*inch, 1.2*inch, 1.3*inch, 1*inch])
    items_table.setStyle(TableStyle(table_style_commands)) # <-- এখানে আপডেট করা স্টাইল ব্যবহার করা হয়েছে
    story.append(items_table)
    story.append(Spacer(1, 1.2*inch))

    # --- ৪. সিগনেচার সেকশন ---
    signature_data = [
        [Paragraph('--------------------------------<br/>Received By', styles['SignatureStyle']),
         Paragraph('--------------------------------<br/>Store Keeper', styles['SignatureStyle'])]
    ]
    signature_table = Table(signature_data, colWidths=[3.5*inch, 3.5*inch], hAlign='CENTER')
    story.append(signature_table)

    doc.build(story)
    
    buffer.seek(0)
    response.write(buffer.getvalue())
    return response

@login_required
def get_products_by_supplier_ajax(request):
    supplier_id = request.GET.get('supplier_id')
    
    if not supplier_id:
        # If no supplier is selected, return all active products with their default price
        products_qs = Product.objects.filter(is_active=True).values('id', 'name', 'price').order_by('name')
        return JsonResponse({'products': list(products_qs)})

    # Get a list of all products for the selected supplier and their prices
    products_with_supplier_prices_qs = ProductSupplier.objects.filter(supplier_id=supplier_id).values('product_id', 'product__name', 'price')
    
    products_data = []
    for item in products_with_supplier_prices_qs:
        products_data.append({
            'id': item['product_id'],
            'name': item['product__name'],
            'price': item['price']
        })
    
    return JsonResponse({'products': products_data})

@login_required
def get_product_price_by_supplier_ajax(request):
    product_id = request.GET.get('product_id')
    supplier_id = request.GET.get('supplier_id')
    
    if not product_id:
        return JsonResponse({'error': 'Product ID is required'}, status=400)

    if not supplier_id:
        try:
            product = Product.objects.get(id=product_id)
            return JsonResponse({'purchase_price': product.price})
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

    try:
        product_supplier = ProductSupplier.objects.get(product_id=product_id, supplier_id=supplier_id)
        price = product_supplier.price
    except ObjectDoesNotExist:
        try:
            product = Product.objects.get(id=product_id)
            price = product.price
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

    return JsonResponse({'purchase_price': price})

@login_required
@permission_required('purchase.view_purchaseorder', login_url='/admin/')
def export_purchase_orders_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Purchase Orders"

    # --- Header Styling ---
    headers = ['PO #', 'Supplier', 'Order Date', 'Expected Delivery', 'Status', 'Total Amount']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="2B3674")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # --- Fetch Data ---
    purchase_orders = PurchaseOrder.objects.select_related('supplier', 'warehouse').all().order_by('-order_date')
    filtered_result = apply_purchase_order_filters(purchase_orders, request)

    # handle return type
    if isinstance(filtered_result, tuple):
        purchase_orders, _ = filtered_result
    else:
        purchase_orders = filtered_result

    if not hasattr(purchase_orders, "__iter__"):
        purchase_orders = [purchase_orders]

    for po in purchase_orders:
        order_date_naive = po.order_date.strftime('%Y-%m-%d %H:%M') if po.order_date else ''
        delivery_date_naive = po.expected_delivery_date.strftime('%Y-%m-%d') if po.expected_delivery_date else ''

        ws.append([
            f"PO-{po.id}",
            po.supplier.name if po.supplier else 'N/A',
            order_date_naive,
            delivery_date_naive,
            po.get_status_display(),
            po.total_amount
        ])

    # --- Auto Adjust Column Widths ---
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="purchase_orders.xlsx"'
    wb.save(response)
    return response


# -------------------------------
# PDF Export
# -------------------------------
@login_required
@permission_required('purchase.view_purchaseorder', login_url='/admin/')
def export_purchase_orders_pdf(request):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    # --- Styles ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=18, fontName='Helvetica-Bold',
                              alignment=TA_CENTER, textColor=colors.HexColor("#2B3674")))
    styles.add(ParagraphStyle(name='TableHeader', fontSize=9, fontName='Helvetica-Bold',
                              alignment=TA_CENTER, textColor=colors.HexColor("#2B3674")))
    styles.add(ParagraphStyle(name='TableCell', fontSize=8, fontName='Helvetica', alignment=TA_CENTER))

    # --- Header Section ---
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'logo.png') #যদি শপের লোগো ব্যবহার করতে চান তাহলে এখানে পরিবর্তন করুন
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.7*inch, height=0.4*inch)
        header_table = Table([[logo, Paragraph("Purchase Orders Report", styles['TitleStyle'])]],
                             colWidths=[2*inch, 4.5*inch])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(header_table)
    else:
        story.append(Paragraph("Purchase Orders Report", styles['TitleStyle']))

    story.append(Spacer(1, 0.4 * inch))

    # --- Table Header ---
    data = [[
        Paragraph(h, styles['TableHeader']) for h in
        ['PO #', 'Supplier', 'Order Date', 'Expected Delivery', 'Status', 'Total']
    ]]

    # --- Fetch Data ---
    purchase_orders = PurchaseOrder.objects.select_related('supplier', 'warehouse').all().order_by('-order_date')
    filtered_result = apply_purchase_order_filters(purchase_orders, request)

    if isinstance(filtered_result, tuple):
        purchase_orders, _ = filtered_result
    else:
        purchase_orders = filtered_result

    if not hasattr(purchase_orders, "__iter__"):
        purchase_orders = [purchase_orders]

    # --- Table Data ---
    if not purchase_orders:
        data.append([Paragraph("No purchase orders found for the selected filters.", styles['TableCell'])])
        table_style = [
            ('SPAN', (0, 1), (-1, 1)),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER')
        ]
        col_widths = [6.5*inch]
    else:
        for po in purchase_orders:
            data.append([
                Paragraph(f"PO-{po.id}", styles['TableCell']),
                Paragraph(po.supplier.name if po.supplier else 'N/A', styles['TableCell']),
                Paragraph(po.order_date.strftime('%d %b %Y') if po.order_date else 'N/A', styles['TableCell']),
                Paragraph(po.expected_delivery_date.strftime('%d %b %Y') if po.expected_delivery_date else 'N/A', styles['TableCell']),
                Paragraph(po.get_status_display(), styles['TableCell']),
                Paragraph(f"{DEFAULT_CURRENCY_SYMBOL}{po.total_amount:.2f}", styles['TableCell'])
            ])
        table_style = []
        col_widths = [0.8*inch, 2.0*inch, 1.2*inch, 1.2*inch, 1*inch, 1.2*inch]

    # --- Table Styling ---
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E5F2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2B3674")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ] + table_style))

    story.append(table)

    # --- Footer (Page Numbers) ---
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(200*mm, 15*mm, f"Page {page_num}")

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="purchase_orders.pdf"'
    return response

@login_required
@permission_required('purchase.change_purchaseorder', login_url='/admin/')
def receive_purchase_order(request, pk):
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)

    if purchase_order.status not in ['confirmed', 'partially_received']:
        messages.warning(request, f"Purchase order {purchase_order.id} is not ready to be received.")
        return redirect('purchase:purchase_order_detail', pk=pk)

    items_to_receive = purchase_order.items.all()

    initial_data = []
    for item in items_to_receive:
        quantity_remaining = item.quantity - (item.quantity_received or 0)
        if quantity_remaining > 0:
            initial_data.append({
                'purchase_order_item_id': item.id,
                'quantity_to_receive': quantity_remaining,
                'product_tracking_method': item.product.tracking_method,
            })

    PurchaseReceiveFormSet = formset_factory(PurchaseReceiveItemForm, extra=0)

    if request.method == 'POST':
        formset = PurchaseReceiveFormSet(request.POST)

        if formset.is_valid():
            try:
                with transaction.atomic():
                    received_items_count = 0
                    for form in formset:
                        if form.has_changed() and form.cleaned_data.get('quantity_to_receive', 0) > 0:
                            item_id = form.cleaned_data.get('purchase_order_item_id')
                            quantity_to_receive = form.cleaned_data.get('quantity_to_receive')
                            destination_location = form.cleaned_data.get('destination_location')
                            lot_number = form.cleaned_data.get('lot_number')
                            expiration_date = form.cleaned_data.get('expiration_date')

                            po_item = get_object_or_404(PurchaseOrderItem, pk=item_id)
                            product = po_item.product

                            if quantity_to_receive > po_item.quantity - (po_item.quantity_received or 0):
                                raise ValidationError(f"Received quantity for {product.name} exceeds remaining quantity.")

                            lot_serial_obj = None
                            if product.tracking_method in ['lot', 'serial'] and lot_number:
                                # get_or_create ব্যবহার করে নতুন লট তৈরি বা পুরনোটি খুঁজে বের করা
                                lot_serial_obj, created = LotSerialNumber.objects.get_or_create(
                                    product=product,
                                    lot_number=lot_number,
                                    location=destination_location,
                                    defaults={'expiration_date': expiration_date, 'quantity': 0}
                                )
                            
                            # ================== পরিবর্তিত অংশ শুরু ==================
                            # পুরনো InventoryTransaction তৈরির কোডটি StockService দিয়ে প্রতিস্থাপন করা হলো
                            # এটি পারমাণবিকভাবে স্টক এবং লট উভয়কেই আপডেট করবে
                            
                            StockService.change_stock(
                                product=product,
                                warehouse=destination_location.warehouse,
                                quantity_change=quantity_to_receive, # স্টক বাড়ছে
                                transaction_type='purchase',
                                user=request.user,
                                content_object=purchase_order,
                                location=destination_location,
                                lot_serial=lot_serial_obj,
                                notes=f"Received PO-{purchase_order.id}"
                            )
                            # ================== পরিবর্তিত অংশ শেষ ===================

                            # পারচেজ অর্ডারের আইটেমে প্রাপ্ত পরিমাণ আপডেট করুন
                            po_item.quantity_received = (po_item.quantity_received or 0) + quantity_to_receive
                            po_item.save()
                            received_items_count += 1

                    if received_items_count > 0:
                        # অর্ডারের স্ট্যাটাস আপডেট করুন
                        total_ordered = purchase_order.items.aggregate(total=Sum('quantity'))['total'] or 0
                        total_received = purchase_order.items.aggregate(total=Sum('quantity_received'))['total'] or 0

                        if total_received >= total_ordered:
                            purchase_order.status = 'received'
                        elif total_received > 0:
                            purchase_order.status = 'partially_received'
                        
                        purchase_order.save()

                        messages.success(request, f"Purchase order {purchase_order.id} received successfully and stock has been updated.")
                        return redirect('purchase:purchase_order_detail', pk=pk)
                    else:
                        messages.warning(request, "No items were marked as received.")
                        return redirect('purchase:receive_purchase_order', pk=pk)

            except (ValidationError, ValueError) as e: # ValueError যোগ করা হয়েছে
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")

        else: # formset is not valid
            messages.error(request, "Please correct the errors below.")
            context = {
                'purchase_order': purchase_order,
                'formset': formset, # এররসহ ফর্মসেটটি আবার পাস করা হলো
                'items_to_receive': items_to_receive,
                'title': f'Receive PO-{purchase_order.id}',
            }
            return render(request, 'purchase/receive_purchase_order.html', context)
    
    else: # GET request
        formset = PurchaseReceiveFormSet(initial=initial_data)

    context = {
        'purchase_order': purchase_order,
        'formset': formset,
        'items_to_receive': items_to_receive,
        'title': f'Receive PO-{purchase_order.id}'
    }
    return render(request, 'purchase/receive_purchase_order.html', context)

#স্টক ট্রান্সফার রিকোয়েস্ট ভিউগুলি।

@login_required
@permission_required('purchase.add_stocktransferrequest', login_url='/admin/')
def create_stock_transfer_request(request):
    form = StockTransferRequestForm(request.POST or None, user=request.user)

    if request.method == 'POST':
        if form.is_valid():
            with transaction.atomic():
                transfer_request = form.save(commit=False)
                transfer_request.user = request.user
                transfer_request.status = 'requested'
                requester_warehouse = getattr(request.user, 'warehouse', None)
                if requester_warehouse:
                    transfer_request.destination_warehouse = requester_warehouse
                    transfer_request.source_warehouse = form.cleaned_data['source_warehouse']
                transfer_request.save()
            messages.success(request, f"Stock transfer request #{transfer_request.pk} for {transfer_request.product.name} has been submitted.")
            return redirect('purchase:stock_transfer_request_list')
    
    context = {
        'form': form,
        'title': 'Create Stock Transfer Request',
    }
    return render(request, 'purchase/create_stock_transfer_request.html', context)

@login_required
@permission_required('purchase.view_stocktransferrequest', login_url='/admin/')
def stock_transfer_request_list(request):
    transfer_requests = StockTransferRequest.objects.all().select_related('user', 'product', 'source_warehouse', 'destination_warehouse').order_by('-requested_at')
    
    if not request.user.is_superuser:
        user_warehouse = getattr(request.user, 'warehouse', None)
        if user_warehouse:
            transfer_requests = transfer_requests.filter(
                Q(destination_warehouse=user_warehouse) | Q(source_warehouse=user_warehouse)
            )
        else:
            transfer_requests = StockTransferRequest.objects.none()

    # --- নতুন এবং উন্নত ফিল্টার লজিক ---
    filter_form = StockTransferFilterForm(request.GET or None, user=request.user)
    if filter_form.is_valid():
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')
        product = filter_form.cleaned_data.get('product')
        source_warehouse = filter_form.cleaned_data.get('source_warehouse')
        destination_warehouse = filter_form.cleaned_data.get('destination_warehouse')
        status = filter_form.cleaned_data.get('status')
        requested_by = filter_form.cleaned_data.get('requested_by') # <-- নতুন

        if start_date:
            transfer_requests = transfer_requests.filter(requested_at__date__gte=start_date)
        if end_date:
            transfer_requests = transfer_requests.filter(requested_at__date__lte=end_date)
        if product:
            transfer_requests = transfer_requests.filter(product=product)
        if source_warehouse:
            transfer_requests = transfer_requests.filter(source_warehouse=source_warehouse)
        if destination_warehouse:
            transfer_requests = transfer_requests.filter(destination_warehouse=destination_warehouse)
        if status:
            transfer_requests = transfer_requests.filter(status=status)
        if requested_by:
            transfer_requests = transfer_requests.filter(user=requested_by) # <-- নতুন
    # --- ফিল্টার লজিক শেষ ---
    
    context = {
        'transfer_requests': transfer_requests,
        'title': 'Stock Transfer Requests',
        'filter_form': filter_form,
    }
    return render(request, 'purchase/stock_transfer_request_list.html', context)

@login_required
@permission_required('purchase.view_stocktransferrequest', login_url='/admin/')
def stock_transfer_detail(request, pk):
    transfer_request = get_object_or_404(StockTransferRequest.objects.select_related('product', 'source_warehouse', 'destination_warehouse', 'user'), pk=pk)
    
    process_form = None
    receive_form = None
    user_warehouse = getattr(request.user, 'warehouse', None)

    is_source_manager = (transfer_request.source_warehouse == user_warehouse)
    is_destination_manager = (transfer_request.destination_warehouse == user_warehouse)
    
    # --- Dispatch (Process) Form Logic ---
    if transfer_request.status == 'approved' and is_source_manager:
        product = transfer_request.product
        
        if request.method == 'POST' and 'process_transfer' in request.POST:
            # POST request handling
            process_form = ProcessStockTransferForm(request.POST)
            
            # Dynamically set querysets for validation
            source_location_id = request.POST.get('source_location')
            process_form.fields['source_location'].queryset = Location.objects.filter(warehouse=user_warehouse)
            if source_location_id and product.tracking_method in ['lot', 'serial']:
                process_form.fields['lot_serial'].queryset = LotSerialNumber.objects.filter(
                    product=product, location_id=source_location_id, quantity__gt=0)

            if process_form.is_valid():
                quantity_to_transfer = process_form.cleaned_data['quantity_to_transfer']
                source_location = process_form.cleaned_data['source_location']
                lot_serial_obj = process_form.cleaned_data.get('lot_serial')

                if product.tracking_method in ['lot', 'serial'] and not lot_serial_obj:
                    messages.error(request, "For a lot-tracked product, you must select a Lot/Serial Number.")
                else:
                    try:
                        with transaction.atomic():
                            StockService.change_stock(
                                product=product,
                                warehouse=transfer_request.source_warehouse,
                                quantity_change=-quantity_to_transfer,
                                transaction_type='transfer_out',
                                user=request.user,
                                content_object=transfer_request,
                                location=source_location,
                                lot_serial=lot_serial_obj,
                                notes=f"Transfer OUT for request #{transfer_request.pk}"
                            )
                            
                            transfer_request.status = 'in_transit'
                            transfer_request.quantity_transferred = quantity_to_transfer
                            transfer_request.dispatched_lot = lot_serial_obj 
                            transfer_request.save()
                            messages.success(request, f"Stock transfer dispatched successfully.")
                        return redirect('purchase:stock_transfer_detail', pk=pk)
                    except (ValueError, ValidationError) as e:
                        messages.error(request, str(e))
            else:
                messages.error(request, "Please correct the errors in the dispatch form.")
        else:
            # GET request
            process_form = ProcessStockTransferForm()
            
            # --- এই লাইনটিতে ভুল ছিল এবং এটি এখন ঠিক করা হয়েছে ---
            locations_with_stock = Location.objects.filter(
                warehouse=user_warehouse, 
                lots__product=product, 
                lots__quantity__gt=0
            ).distinct()
            # --- stock__product এর পরিবর্তে lots__product ব্যবহার করা হয়েছে ---

            process_form.fields['source_location'].queryset = locations_with_stock

    # --- Receive Form Logic ---
    if transfer_request.status == 'in_transit' and is_destination_manager:
        initial_data = {}
        if transfer_request.dispatched_lot:
            initial_data['lot_number'] = transfer_request.dispatched_lot.lot_number
            initial_data['expiration_date'] = transfer_request.dispatched_lot.expiration_date
        
        receive_form = ReceiveStockTransferForm(initial=initial_data)
        receive_form.fields['destination_location'].queryset = Location.objects.filter(warehouse=user_warehouse)

    context = {
        'transfer_request': transfer_request,
        'title': f"Stock Transfer Request #{transfer_request.pk}",
        'process_form': process_form,
        'receive_form': receive_form,
        'product_is_tracked': transfer_request.product.tracking_method in ['lot', 'serial']
    }
    return render(request, 'purchase/stock_transfer_detail.html', context)

@login_required
@permission_required('purchase.approve_stocktransferrequest', login_url='/admin/')
def approve_stock_transfer(request, pk):
    transfer_request = get_object_or_404(StockTransferRequest, pk=pk)
    
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('purchase:stock_transfer_detail', pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        with transaction.atomic():
            if action == 'approve' and transfer_request.status == 'requested':
                transfer_request.status = 'approved'
                transfer_request.approved_at = timezone.now()
                transfer_request.save()
                messages.success(request, f"Stock transfer request #{transfer_request.pk} has been approved.")
            elif action == 'reject' and transfer_request.status == 'requested':
                transfer_request.status = 'rejected'
                transfer_request.save()
                messages.warning(request, f"Stock transfer request #{transfer_request.pk} has been rejected.")
            
    return redirect('purchase:stock_transfer_detail', pk=pk)

#@login_required
#@permission_required('purchase.change_stocktransferrequest', login_url='/admin/')
#def process_stock_transfer(request, pk):
#    transfer_request = get_object_or_404(StockTransferRequest, pk=pk)
#    user_warehouse = getattr(request.user, 'warehouse', None)
#
#    if transfer_request.source_warehouse != user_warehouse and not request.user.is_superuser:
#        messages.error(request, "You do not have permission to process this transfer.")
#        return redirect('purchase:stock_transfer_detail', pk=pk)
#
#    if request.method == 'POST':
#        form = ProcessStockTransferForm(request.POST)
#        
#        # --- সমাধান: ফর্ম ভ্যালিডেশনের আগেও queryset সেট করা ---
#        product = transfer_request.product
#        if product.tracking_method in ['lot', 'serial']:
#            form.fields['source_location'].queryset = Location.objects.filter(
#                warehouse=user_warehouse, 
#                lots__product=product, 
#                lots__quantity__gt=0
#            ).distinct()
#        else:
#            form.fields['source_location'].queryset = Location.objects.filter(warehouse=user_warehouse)
#
#        if form.is_valid():
#            quantity_to_transfer = form.cleaned_data['quantity_to_transfer']
#            source_location = form.cleaned_data['source_location']
#            lot_serial_obj = form.cleaned_data.get('lot_serial')
#            try:
#                with transaction.atomic():
#                    StockService.change_stock(
#                        product=product,
#                        warehouse=transfer_request.source_warehouse,
#                        quantity_change=-quantity_to_transfer,
#                        transaction_type='transfer_out',
#                        user=request.user,
#                        content_object=transfer_request,
#                        location=source_location,
#                        lot_serial=lot_serial_obj,
#                        notes=f"Transfer OUT for request #{transfer_request.pk}"
#                    )
#                    
#                    transfer_request.status = 'in_transit'
#                    transfer_request.quantity_transferred = quantity_to_transfer
#                    transfer_request.save()
#                    messages.success(request, f"Stock transfer dispatched successfully.")
#            
#            except (ValueError, ValidationError) as e:
#                messages.error(request, str(e))
#        else:
#            # ভ্যালিডেশন এররগুলো ব্যবহারকারীকে দেখানোর জন্য
#            for field, errors in form.errors.items():
#                for error in errors:
#                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
#
#    return redirect('purchase:stock_transfer_detail', pk=pk)

@login_required
@permission_required('purchase.change_stocktransferrequest', login_url='/admin/')
def receive_stock_transfer(request, pk):
    transfer_request = get_object_or_404(StockTransferRequest, pk=pk)
    user_warehouse = getattr(request.user, 'warehouse', None)

    if transfer_request.destination_warehouse != user_warehouse and not request.user.is_superuser:
        messages.error(request, "You do not have permission to receive this transfer.")
        return redirect('purchase:stock_transfer_detail', pk=pk)

    if request.method == 'POST':
        form = ReceiveStockTransferForm(request.POST)
        form.fields['destination_location'].queryset = Location.objects.filter(warehouse=user_warehouse)

        if form.is_valid():
            quantity_received = form.cleaned_data['quantity_received']
            destination_location = form.cleaned_data['destination_location']
            lot_number = form.cleaned_data.get('lot_number')
            expiration_date = form.cleaned_data.get('expiration_date')
            
            if quantity_received > transfer_request.quantity_transferred:
                messages.error(request, "Received quantity cannot exceed transferred quantity.")
                return redirect('purchase:stock_transfer_detail', pk=pk)
            try:
                with transaction.atomic():
                    lot_serial_obj = None
                    if transfer_request.product.tracking_method in ['lot', 'serial'] and lot_number:
                        lot_serial_obj, created = LotSerialNumber.objects.get_or_create(
                            product=transfer_request.product,
                            lot_number=lot_number,
                            location=destination_location,
                            defaults={'expiration_date': expiration_date, 'quantity': 0}
                        )

                    StockService.change_stock(
                        product=transfer_request.product,
                        warehouse=transfer_request.destination_warehouse,
                        quantity_change=quantity_received,
                        transaction_type='transfer_in',
                        user=request.user,
                        content_object=transfer_request,
                        location=destination_location,
                        lot_serial=lot_serial_obj,
                        notes=f"Transfer IN for request #{transfer_request.pk}"
                    )
                    
                    transfer_request.status = 'received'
                    transfer_request.quantity_received = quantity_received
                    transfer_request.save()
                    messages.success(request, f"Stock transfer received successfully.")
            except (ValueError, ValidationError) as e:
                messages.error(request, str(e))
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return redirect('purchase:stock_transfer_detail', pk=pk)

# --- নতুন AJAX ভিউ ---
@login_required
def get_lots_for_location_ajax(request):
    location_id = request.GET.get('location_id')
    product_id = request.GET.get('product_id')
    
    if not location_id or not product_id:
        return JsonResponse({'error': 'Location and Product ID are required.'}, status=400)
    
    lots = LotSerialNumber.objects.filter(
        location_id=location_id,
        product_id=product_id,
        quantity__gt=0
    ).values('id', 'lot_number', 'quantity', 'expiration_date')

    # প্রতিটি লটের জন্য একটি তথ্যপূর্ণ ডিসপ্লে টেক্সট তৈরি করা
    lots_data = []
    for lot in lots:
        exp_date_str = lot['expiration_date'].strftime('%d-%b-%Y') if lot['expiration_date'] else 'N/A'
        lots_data.append({
            'id': lot['id'],
            'text': f"Lot: {lot['lot_number']} (Qty: {lot['quantity']}, Exp: {exp_date_str})"
        })

    return JsonResponse({'lots': list(lots_data)})
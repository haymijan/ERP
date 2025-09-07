# costing/views.py

import os
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone # timezone ইম্পোর্ট করা হয়েছে

from .models import JobCost
from .forms import JobCostFilterForm
from inventory_system.settings import DEFAULT_CURRENCY_SYMBOL

from django.http import HttpResponse
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# --- পেজ নম্বর যোগ করার জন্য নতুন ফাংশন ---
def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.drawString(inch, 0.75 * inch, text)
    canvas.restoreState()

@login_required
def job_costing_report(request):
    # এই ভিউটি আগের মতোই থাকবে, কোনো পরিবর্তন প্রয়োজন নেই
    job_costs_list = JobCost.objects.select_related('sales_order', 'sales_order__user', 'sales_order__warehouse').order_by('-sales_order__created_at')
    
    filter_form = JobCostFilterForm(request.GET or None)

    if request.user.is_superuser and filter_form.is_valid():
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')
        warehouse = filter_form.cleaned_data.get('warehouse')
        user = filter_form.cleaned_data.get('user')

        if start_date:
            job_costs_list = job_costs_list.filter(sales_order__created_at__date__gte=start_date)
        if end_date:
            job_costs_list = job_costs_list.filter(sales_order__created_at__date__lte=end_date)
        if warehouse:
            job_costs_list = job_costs_list.filter(sales_order__warehouse=warehouse)
        if user:
            job_costs_list = job_costs_list.filter(sales_order__user=user)

    paginator = Paginator(job_costs_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Job Costing Report',
        'page_obj': page_obj,
        'filter_form': filter_form,
    }
    return render(request, 'costing/job_costing_report.html', context)

@login_required
def export_job_costing_pdf(request):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=401)

    job_costs_list = JobCost.objects.select_related('sales_order', 'sales_order__user', 'sales_order__warehouse').order_by('-sales_order__created_at')
    
    # --- ফিল্টারিং লজিক ---
    filter_form = JobCostFilterForm(request.GET or None)
    filter_details_list = []
    if filter_form.is_valid():
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')
        warehouse = filter_form.cleaned_data.get('warehouse')
        user = filter_form.cleaned_data.get('user')

        if start_date:
            job_costs_list = job_costs_list.filter(sales_order__created_at__date__gte=start_date)
            filter_details_list.append(f"<b>From:</b> {start_date.strftime('%d %b, %Y')}")
        if end_date:
            job_costs_list = job_costs_list.filter(sales_order__created_at__date__lte=end_date)
            filter_details_list.append(f"<b>To:</b> {end_date.strftime('%d %b, %Y')}")
        if warehouse:
            job_costs_list = job_costs_list.filter(sales_order__warehouse=warehouse)
            filter_details_list.append(f"<b>Branch:</b> {warehouse.name}")
        if user:
            job_costs_list = job_costs_list.filter(sales_order__user=user)
            filter_details_list.append(f"<b>User:</b> {user.username}")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
    story = []

    # --- কাস্টম স্টাইল তৈরি ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=22, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=colors.HexColor("#2B3674")))
    styles.add(ParagraphStyle(name='CompanyInfo', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT, leading=12))
    styles.add(ParagraphStyle(name='ReportInfo', fontSize=10, fontName='Helvetica', leading=14))
    styles.add(ParagraphStyle(name='TotalLabel', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='TotalValue', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='SignatureStyle', fontSize=10, fontName='Helvetica', alignment=TA_CENTER))

    # --- ১. হেডার সেকশন ---
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'logo.png')
    logo = Image(logo_path, width=1.5*inch, height=0.5*inch)
    company_info = "<b>NOVO ERP Solutions</b><br/>Doha, Qatar"
    
    header_data = [[logo, Paragraph("Job Costing Report", styles['TitleStyle'])]]
    header_table = Table(header_data, colWidths=[4.5*inch, 3*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
    story.append(header_table)
    story.append(Spacer(1, 0.05*inch))
    story.append(Paragraph(company_info, styles['CompanyInfo']))
    story.append(Spacer(1, 0.3*inch))

    # --- ২. রিপোর্টের তথ্য ---
    filter_details_text = " | ".join(filter_details_list)
    report_info_text = f"<b>Filters Applied:</b> {filter_details_text if filter_details_list else 'None'}<br/><b>Report Generated:</b> {timezone.now().strftime('%d %b, %Y %I:%M %p')}"
    story.append(Paragraph(report_info_text, styles['ReportInfo']))
    story.append(Spacer(1, 0.3*inch))

    # --- ৩. টেবিল ---
    table_header = ['Order #', 'Date', 'Branch', 'Revenue', 'Material Cost', 'Profit / Loss']
    table_data = [table_header]
    
    total_revenue = total_cost = total_profit = 0
    for job in job_costs_list:
        profit_style = ParagraphStyle(name='ProfitCellStyle', alignment=TA_RIGHT, textColor=colors.red if job.profit < 0 else colors.darkgreen)
        
        table_data.append([
            f"SO-{job.sales_order.pk}",
            job.sales_order.created_at.strftime("%d %b, %Y"),
            job.sales_order.warehouse.name if job.sales_order.warehouse else 'N/A',
            f"{job.total_revenue:,.2f}",
            f"{job.total_material_cost:,.2f}",
            Paragraph(f"{job.profit:,.2f}", profit_style)
        ])
        total_revenue += job.total_revenue
        total_cost += job.total_material_cost
        total_profit += job.profit

    table = Table(table_data, colWidths=[0.8*inch, 1*inch, 1.5*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E0E5F2")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#2B3674")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#CCCCCC")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,1), (2,-1), 'LEFT'),
        ('ALIGN', (3,1), (-1,-1), 'RIGHT'),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # --- ৪. মোট হিসাব সেকশন ---
    total_data = [
        [Paragraph('Total Revenue:', styles['TotalLabel']), Paragraph(f"{DEFAULT_CURRENCY_SYMBOL} {total_revenue:,.2f}", styles['TotalValue'])],
        [Paragraph('Total Material Cost:', styles['TotalLabel']), Paragraph(f"{DEFAULT_CURRENCY_SYMBOL} {total_cost:,.2f}", styles['TotalValue'])],
        [Paragraph('Total Profit / Loss:', styles['TotalLabel']), Paragraph(f"{DEFAULT_CURRENCY_SYMBOL} {total_profit:,.2f}", styles['TotalValue'])],
    ]
    total_table = Table(total_data, colWidths=[2*inch, 2*inch], hAlign='RIGHT')
    story.append(total_table)

    # --- ৫. সিগনেচার সেকশন ---
    story.append(Spacer(1, 0.7*inch))
    signature_data = [
        [Paragraph('--------------------------------<br/>Prepared By', styles['SignatureStyle']),
         Paragraph('--------------------------------<br/>Checked By', styles['SignatureStyle']),
         Paragraph('--------------------------------<br/>Approved By', styles['SignatureStyle'])]
    ]
    signature_table = Table(signature_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch], hAlign='CENTER')
    story.append(signature_table)

    doc.build(story)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Job_Costing_Report.pdf"'
    return response

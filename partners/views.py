# partners/views.py (সম্পূর্ণ সংশোধিত ফাইল)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q

# --- সঠিক import স্টেটমেন্টগুলো এখানে যোগ করা হয়েছে ---
from .models import Customer, Supplier
from .forms import CustomerForm, SupplierForm
from .forms import CustomerFilterForm
from django.core.paginator import Paginator

# --- Supplier CRUD Views ---
@login_required
@permission_required('partners.view_supplier', login_url='/admin/')
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'partners/supplier_list.html', {'suppliers': suppliers, 'title': 'All Suppliers'})

@login_required
@permission_required('partners.add_supplier', login_url='/admin/')
def add_supplier(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully!')
            return redirect('partners:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'partners/add_supplier.html', {'form': form, 'title': 'Add New Supplier'})

@login_required
@permission_required('partners.change_supplier', login_url='/admin/')
def edit_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Supplier "{supplier.name}" updated successfully!')
            return redirect('partners:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'partners/edit_supplier.html', {'form': form, 'title': f'Edit Supplier: {supplier.name}'})

@login_required
@permission_required('partners.delete_supplier', login_url='/admin/')
def delete_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'Supplier "{supplier_name}" deleted successfully!')
        return redirect('partners:supplier_list')
    # GET অনুরোধের জন্য confirm_delete.html ব্যবহার করা হয়েছে
    return render(request, 'confirm_delete.html', {'object': supplier, 'title': f'Confirm Delete: {supplier.name}'})


# --- Customer CRUD Views ---
@login_required
@permission_required('partners.view_customer', login_url='/admin/')
def customer_list(request):
    customers_list = Customer.objects.all().order_by('-created_at')
    
    # --- নতুন ফিল্টার এবং সার্চ লজিক ---
    filter_form = CustomerFilterForm(request.GET or None)
    if filter_form.is_valid():
        query = filter_form.cleaned_data.get('q')
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')

        if query:
            customers_list = customers_list.filter(
                Q(name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )
        if start_date:
            customers_list = customers_list.filter(created_at__date__gte=start_date)
        if end_date:
            customers_list = customers_list.filter(created_at__date__lte=end_date)
            
    # --- পেজিনেশন লজিক ---
    paginator = Paginator(customers_list, 15) # প্রতি পৃষ্ঠায় ১৫ জন কাস্টমার
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)

    context = {
        'customers': customers,
        'title': 'All Customers',
        'filter_form': filter_form # <-- فرمটিকে context-এ পাস করা হয়েছে
    }
    return render(request, 'partners/customer_list.html', context)

@login_required
@permission_required('partners.add_customer', login_url='/admin/')
def add_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer added successfully!')
            return redirect('partners:customer_list') 
    else:
        form = CustomerForm()
    return render(request, 'partners/add_customer.html', {'form': form, 'title': 'Add New Customer'})

@login_required
@permission_required('partners.change_customer', login_url='/admin/')
def edit_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully!')
            return redirect('partners:customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'partners/edit_customer.html', {'form': form, 'title': f'Edit Customer: {customer.name}'})

@login_required
@permission_required('partners.delete_customer', login_url='/admin/')
def delete_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'Customer "{customer_name}" deleted successfully!')
        return redirect('partners:customer_list')
    return render(request, 'confirm_delete.html', {'object': customer, 'title': f'Confirm Delete: {customer.name}'})


# --- AJAX Views ---
@login_required
@permission_required('partners.add_supplier', raise_exception=True)
def ajax_add_supplier(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            return JsonResponse({'success': True, 'id': supplier.id, 'name': supplier.name})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@login_required
@permission_required('partners.add_customer', raise_exception=True)
def ajax_add_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            return JsonResponse({'success': True, 'id': customer.id, 'name': customer.name})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
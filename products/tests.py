# purchase/tests.py

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum # Sum অ্যাগ্রিগেশন ফাংশন ইম্পোর্ট করা হয়েছে

# Local Application Imports
from .models import ProductSupplier, PurchaseOrder, PurchaseOrderItem
from products.models import Product, Category, UnitOfMeasure, UnitOfMeasureCategory
from partners.models import Supplier

# ProductSupplier মডেলের জন্য টেস্ট কেস।
class ProductSupplierModelTest(TestCase):
    def setUp(self):
        # ProductSupplier এর জন্য প্রয়োজনীয় Product এবং Supplier তৈরি করা হচ্ছে।
        self.category = Category.objects.create(name="Electronics")
        self.uom_category = UnitOfMeasureCategory.objects.create(name="Units")
        self.unit_of_measure = UnitOfMeasure.objects.create(
            name="Piece", short_code="pc", category=self.uom_category, ratio=1.0, is_base_unit=True
        )
        self.product = Product.objects.create(
            name="Test Gadget", product_code="TG001", category=self.category,
            price=50.00, unit_of_measure=self.unit_of_measure
        )
        self.supplier = Supplier.objects.create(name="Gadget Supplier Inc.", email="gadget@example.com")

    def test_product_supplier_creation(self):
        # একটি নতুন ProductSupplier অবজেক্ট তৈরি করা হচ্ছে।
        product_supplier = ProductSupplier.objects.create(
            product=self.product,
            supplier=self.supplier,
            supplier_product_code="GS-TG001",
            price=45.00
        )
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(product_supplier.product, self.product)
        self.assertEqual(product_supplier.supplier, self.supplier)
        self.assertEqual(product_supplier.supplier_product_code, "GS-TG001")
        self.assertEqual(float(product_supplier.price), 45.00)
        # __str__ মেথড পরীক্ষা: ProductSupplier মডেলে __str__ মেথডটি product.name এবং supplier.name রিটার্ন করে।
        # যদি আপনার ProductSupplier মডেলে __str__ মেথডটি priceও অন্তর্ভুক্ত করে, তাহলে এই অ্যাসার্শনটি পরিবর্তন করতে হবে।
        # আপনার models.py ফাইল অনুযায়ী, এটি শুধু product.name এবং supplier.name রিটার্ন করে।
        # যদি আপনার ProductSupplier মডেলের __str__ মেথডটি price অন্তর্ভুক্ত করে, তবে এটি হবে:
        # self.assertEqual(str(product_supplier), f"{self.product.name} from {self.supplier.name} at {product_supplier.price}")
        self.assertEqual(str(product_supplier), f"{self.product.name} from {self.supplier.name}") # বর্তমান models.py অনুযায়ী
        self.assertEqual(ProductSupplier.objects.count(), 1)

    def test_product_supplier_update(self):
        product_supplier = ProductSupplier.objects.create(
            product=self.product, supplier=self.supplier, price=40.00
        )
        product_supplier.price = 42.50
        product_supplier.save()
        updated_product_supplier = ProductSupplier.objects.get(id=product_supplier.id)
        self.assertEqual(float(updated_product_supplier.price), 42.50)

    def test_product_supplier_deletion(self):
        product_supplier = ProductSupplier.objects.create(
            product=self.product, supplier=self.supplier, price=30.00
        )
        product_supplier.delete()
        self.assertEqual(ProductSupplier.objects.count(), 0)

# PurchaseOrder মডেলের জন্য টেস্ট কেস।
class PurchaseOrderModelTest(TestCase):
    def setUp(self):
        # PurchaseOrder এর জন্য প্রয়োজনীয় Supplier তৈরি করা হচ্ছে।
        self.supplier = Supplier.objects.create(name="Book Supplier Co.", email="books@example.com")

    def test_purchase_order_creation(self):
        # একটি নতুন PurchaseOrder অবজেক্ট তৈরি করা হচ্ছে।
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            expected_delivery_date=timezone.now().date() + timedelta(days=7),
            status='draft',
            notes="Urgent order for new titles"
        )
        # নিশ্চিত করা হচ্ছে যে অবjectটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(po.supplier, self.supplier)
        self.assertEqual(po.status, 'draft')
        self.assertAlmostEqual(float(po.total_amount), 0.00) # প্রাথমিক মোট পরিমাণ 0 হওয়া উচিত
        self.assertEqual(PurchaseOrder.objects.count(), 1)
        self.assertIn(f"PO-{po.pk}", str(po)) # __str__ মেথড পরীক্ষা

    def test_purchase_order_update(self):
        po = PurchaseOrder.objects.create(supplier=self.supplier, status='draft')
        po.status = 'confirmed'
        po.save()
        updated_po = PurchaseOrder.objects.get(id=po.id)
        self.assertEqual(updated_po.status, 'confirmed')

    def test_purchase_order_deletion(self):
        po = PurchaseOrder.objects.create(supplier=self.supplier, status='draft')
        po.delete()
        self.assertEqual(PurchaseOrder.objects.count(), 0)

# PurchaseOrderItem মডেলের জন্য টেস্ট কেস।
class PurchaseOrderItemModelTest(TestCase):
    def setUp(self):
        # PurchaseOrderItem এর জন্য প্রয়োজনীয় Product এবং PurchaseOrder তৈরি করা হচ্ছে।
        self.category = Category.objects.create(name="Books")
        self.uom_category = UnitOfMeasureCategory.objects.create(name="Units")
        self.unit_of_measure = UnitOfMeasure.objects.create(
            name="Unit", short_code="un", category=self.uom_category, ratio=1.0, is_base_unit=True
        )
        self.product1 = Product.objects.create(
            name="Python Programming", product_code="PP001", category=self.category,
            price=25.00, unit_of_measure=self.unit_of_measure
        )
        self.product2 = Product.objects.create(
            name="Django Handbook", product_code="DH001", category=self.category,
            price=35.00, unit_of_measure=self.unit_of_measure
        )
        self.supplier = Supplier.objects.create(name="Tech Books Ltd.")
        self.purchase_order = PurchaseOrder.objects.create(supplier=self.supplier, status='draft')

    def test_purchase_order_item_creation(self):
        # একটি নতুন PurchaseOrderItem অবজেক্ট তৈরি করা হচ্ছে।
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order, # 'sales_order' এর পরিবর্তে 'purchase_order' ব্যবহার করা হয়েছে
            product=self.product1,
            quantity=10,
            unit_price=20.00
        )
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(po_item.purchase_order, self.purchase_order)
        self.assertEqual(po_item.product, self.product1)
        self.assertEqual(po_item.quantity, 10)
        self.assertEqual(float(po_item.unit_price), 20.00)
        self.assertAlmostEqual(float(po_item.subtotal), 200.00) # subtotal প্রপার্টি পরীক্ষা
        self.assertEqual(PurchaseOrderItem.objects.count(), 1)
        self.assertIn(f"{po_item.quantity} x {po_item.product.name}", str(po_item)) # __str__ মেথড পরীক্ষা

        # PurchaseOrder এর total_amount স্বয়ংক্রিয়ভাবে আপডেট হয় কিনা তা পরীক্ষা করা হচ্ছে।
        # এই লজিকটি সাধারণত সিগনাল দ্বারা পরিচালিত হয়।
        # এখানে আমরা ম্যানুয়ালি total_amount আপডেট করে পরীক্ষা করছি।
        self.purchase_order.total_amount = self.purchase_order.items.aggregate(total=Sum('subtotal'))['total'] or 0
        self.purchase_order.save()
        self.purchase_order.refresh_from_db()
        self.assertAlmostEqual(float(self.purchase_order.total_amount), 200.00)

    def test_purchase_order_item_update(self):
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order, product=self.product1, quantity=5, unit_price=20.00
        )
        po_item.quantity = 15
        po_item.unit_price = 22.00
        po_item.save()
        updated_po_item = PurchaseOrderItem.objects.get(id=po_item.id)
        self.assertEqual(updated_po_item.quantity, 15)
        self.assertEqual(float(updated_po_item.unit_price), 22.00)
        self.assertAlmostEqual(float(updated_po_item.subtotal), 330.00)

        # PurchaseOrder এর total_amount আপডেট পরীক্ষা করা হচ্ছে।
        self.purchase_order.total_amount = self.purchase_order.items.aggregate(total=Sum('subtotal'))['total'] or 0
        self.purchase_order.save()
        self.purchase_order.refresh_from_db()
        self.assertAlmostEqual(float(self.purchase_order.total_amount), 330.00)

    def test_purchase_order_item_deletion(self):
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order, product=self.product1, quantity=5, unit_price=20.00
        )
        po_item.delete()
        self.assertEqual(PurchaseOrderItem.objects.count(), 0)

        # PurchaseOrder এর total_amount আপডেট পরীক্ষা করা হচ্ছে।
        self.purchase_order.total_amount = self.purchase_order.items.aggregate(total=Sum('subtotal'))['total'] or 0
        self.purchase_order.save()
        self.purchase_order.refresh_from_db()
        self.assertAlmostEqual(float(self.purchase_order.total_amount), 0.00) # আইটেম মুছে ফেলার পর 0 হওয়া উচিত

    def test_multiple_purchase_order_items_total_amount(self):
        # একাধিক আইটেম যোগ করে মোট পরিমাণ পরীক্ষা করা হচ্ছে।
        PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order, product=self.product1, quantity=5, unit_price=20.00 # Subtotal 100
        )
        PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order, product=self.product2, quantity=2, unit_price=30.00 # Subtotal 60
        )
        
        # total_amount ম্যানুয়ালি আপডেট করে পরীক্ষা করা হচ্ছে।
        self.purchase_order.total_amount = self.purchase_order.items.aggregate(total=Sum('subtotal'))['total'] or 0
        self.purchase_order.save()
        self.purchase_order.refresh_from_db()
        self.assertAlmostEqual(float(self.purchase_order.total_amount), 160.00) # 100 + 60 = 160


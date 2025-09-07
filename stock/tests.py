# stock/tests.py

from django.test import TestCase
from .models import Warehouse, Location, Stock, LotSerialNumber, InventoryTransaction
from products.models import Product, Category, UnitOfMeasure, UnitOfMeasureCategory
from partners.models import Customer, Supplier
from django.utils import timezone
from datetime import timedelta

# Warehouse মডেলের জন্য টেস্ট কেস।
class WarehouseModelTest(TestCase):
    def test_warehouse_creation(self):
        # একটি নতুন Warehouse অবজেক্ট তৈরি করা হচ্ছে।
        warehouse = Warehouse.objects.create(name="Central Warehouse", address="123 Main St")
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(warehouse.name, "Central Warehouse")
        self.assertEqual(warehouse.address, "123 Main St")
        self.assertEqual(str(warehouse), "Central Warehouse")
        self.assertEqual(Warehouse.objects.count(), 1)

    def test_warehouse_update(self):
        warehouse = Warehouse.objects.create(name="Old Warehouse")
        warehouse.name = "New Warehouse"
        warehouse.save()
        updated_warehouse = Warehouse.objects.get(id=warehouse.id)
        self.assertEqual(updated_warehouse.name, "New Warehouse")

    def test_warehouse_deletion(self):
        warehouse = Warehouse.objects.create(name="Delete Warehouse")
        warehouse.delete()
        self.assertEqual(Warehouse.objects.count(), 0)

# Location মডেলের জন্য টেস্ট কেস।
class LocationModelTest(TestCase):
    def setUp(self):
        # Location এর জন্য প্রয়োজনীয় Warehouse তৈরি করা হচ্ছে।
        self.warehouse = Warehouse.objects.create(name="Test Warehouse")

    def test_location_creation(self):
        # একটি নতুন Location অবজেক্ট তৈরি করা হচ্ছে।
        location = Location.objects.create(name="Shelf A", warehouse=self.warehouse)
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(location.name, "Shelf A")
        self.assertEqual(location.warehouse, self.warehouse)
        self.assertEqual(str(location), f"{self.warehouse.name} / Shelf A")
        self.assertEqual(Location.objects.count(), 1)

    def test_nested_location_creation(self):
        # একটি প্যারেন্ট লোকেশন তৈরি করা হচ্ছে।
        parent_location = Location.objects.create(name="Floor 1", warehouse=self.warehouse)
        # একটি চাইল্ড লোকেশন তৈরি করা হচ্ছে।
        child_location = Location.objects.create(name="Rack B", warehouse=self.warehouse, parent_location=parent_location)
        self.assertEqual(child_location.parent_location, parent_location)
        self.assertEqual(str(child_location), f"{self.warehouse.name} / Floor 1 / Rack B")

    def test_location_update(self):
        location = Location.objects.create(name="Old Location", warehouse=self.warehouse)
        location.name = "New Location"
        location.save()
        updated_location = Location.objects.get(id=location.id)
        self.assertEqual(updated_location.name, "New Location")

    def test_location_deletion(self):
        location = Location.objects.create(name="Delete Location", warehouse=self.warehouse)
        location.delete()
        self.assertEqual(Location.objects.count(), 0)

    def test_location_cannot_be_own_parent(self):
        # একটি লোকেশন তার নিজের প্যারেন্ট হতে পারবে না।
        location = Location.objects.create(name="Self Parent Test", warehouse=self.warehouse)
        location.parent_location = location
        with self.assertRaises(Exception): # ValidationError আশা করা হচ্ছে, তবে Django এর full_clean() এর কারণে এটি Exception হতে পারে
            location.full_clean() # clean মেথড কল করা হচ্ছে

    def test_circular_dependency(self):
        # সাইক্লিক ডিপেন্ডেন্সি পরীক্ষা (A -> B -> A)
        loc_a = Location.objects.create(name="Loc A", warehouse=self.warehouse)
        loc_b = Location.objects.create(name="Loc B", warehouse=self.warehouse, parent_location=loc_a)
        loc_a.parent_location = loc_b # A এর প্যারেন্ট B সেট করা হচ্ছে
        with self.assertRaises(Exception): # ValidationError আশা করা হচ্ছে
            loc_a.full_clean() # clean মেথড কল করা হচ্ছে

# Stock মডেলের জন্য টেস্ট কেস।
class StockModelTest(TestCase):
    def setUp(self):
        # Stock এর জন্য প্রয়োজনীয় Product এবং Location তৈরি করা হচ্ছে।
        self.warehouse = Warehouse.objects.create(name="Stock Warehouse")
        self.location = Location.objects.create(name="Stock Location", warehouse=self.warehouse)
        self.category = Category.objects.create(name="Electronics")
        self.uom_category = UnitOfMeasureCategory.objects.create(name="Units")
        self.unit_of_measure = UnitOfMeasure.objects.create(
            name="Piece", short_code="pc", category=self.uom_category, ratio=1.0, is_base_unit=True
        )
        self.product = Product.objects.create(
            name="Test Product", product_code="TP001", category=self.category, price=100.00,
            unit_of_measure=self.unit_of_measure
        )

    def test_stock_creation(self):
        # একটি নতুন Stock অবজেক্ট তৈরি করা হচ্ছে।
        stock = Stock.objects.create(product=self.product, location=self.location, quantity=100)
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(stock.product, self.product)
        self.assertEqual(stock.location, self.location)
        self.assertEqual(stock.quantity, 100)
        self.assertEqual(str(stock), f"{self.product.name} (100) at {self.location}")
        self.assertEqual(Stock.objects.count(), 1)

    def test_stock_update(self):
        stock = Stock.objects.create(product=self.product, location=self.location, quantity=50)
        stock.quantity = 150
        stock.save()
        updated_stock = Stock.objects.get(id=stock.id)
        self.assertEqual(updated_stock.quantity, 150)

    def test_stock_unique_together(self):
        # একই product এবং location এর জন্য দ্বিতীয় Stock তৈরি করার চেষ্টা করা হচ্ছে।
        Stock.objects.create(product=self.product, location=self.location, quantity=10)
        with self.assertRaises(Exception): # IntegrityError আশা করা হচ্ছে
            Stock.objects.create(product=self.product, location=self.location, quantity=20)

    def test_stock_deletion(self):
        stock = Stock.objects.create(product=self.product, location=self.location, quantity=10)
        stock.delete()
        self.assertEqual(Stock.objects.count(), 0)

# LotSerialNumber মডেলের জন্য টেস্ট কেস।
class LotSerialNumberModelTest(TestCase):
    def setUp(self):
        # LotSerialNumber এর জন্য প্রয়োজনীয় Product এবং Location তৈরি করা হচ্ছে।
        self.warehouse = Warehouse.objects.create(name="Lot Warehouse")
        self.location = Location.objects.create(name="Lot Location", warehouse=self.warehouse)
        self.category = Category.objects.create(name="Electronics")
        self.uom_category = UnitOfMeasureCategory.objects.create(name="Units")
        self.unit_of_measure = UnitOfMeasure.objects.create(
            name="Piece", short_code="pc", category=self.uom_category, ratio=1.0, is_base_unit=True
        )
        self.product = Product.objects.create(
            name="Test Product for Lot", product_code="TPL001", category=self.category, price=100.00,
            unit_of_measure=self.unit_of_measure, tracking_method='lot' # ট্র্যাকিং মেথড 'lot' সেট করা হয়েছে
        )

    def test_lot_serial_creation(self):
        # একটি নতুন LotSerialNumber অবজেক্ট তৈরি করা হচ্ছে।
        lot_serial = LotSerialNumber.objects.create(
            product=self.product,
            location=self.location,
            lot_number="BATCH-001",
            quantity=50,
            expiration_date=timezone.now().date() + timedelta(days=365)
        )
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে সংরক্ষণ করা হয়েছে।
        self.assertEqual(lot_serial.product, self.product)
        self.assertEqual(lot_serial.location, self.location)
        self.assertEqual(lot_serial.lot_number, "BATCH-001")
        self.assertEqual(lot_serial.quantity, 50)
        self.assertEqual(LotSerialNumber.objects.count(), 1)
        self.assertEqual(str(lot_serial), f"{self.product.name} - BATCH-001 ({lot_serial.quantity} in {self.location.name})")

    def test_lot_serial_update(self):
        lot_serial = LotSerialNumber.objects.create(
            product=self.product, location=self.location, lot_number="BATCH-002", quantity=20
        )
        lot_serial.quantity = 40
        lot_serial.save()
        updated_lot_serial = LotSerialNumber.objects.get(id=lot_serial.id)
        self.assertEqual(updated_lot_serial.quantity, 40)

    def test_lot_serial_unique_together(self):
        # একই product, location, এবং lot_number এর জন্য দ্বিতীয় LotSerialNumber তৈরি করার চেষ্টা করা হচ্ছে।
        LotSerialNumber.objects.create(product=self.product, location=self.location, lot_number="BATCH-003", quantity=10)
        with self.assertRaises(Exception): # IntegrityError আশা করা হচ্ছে
            LotSerialNumber.objects.create(product=self.product, location=self.location, lot_number="BATCH-003", quantity=5)

    def test_lot_serial_deletion(self):
        lot_serial = LotSerialNumber.objects.create(
            product=self.product, location=self.location, lot_number="BATCH-004", quantity=10
        )
        lot_serial.delete()
        self.assertEqual(LotSerialNumber.objects.count(), 0)

# InventoryTransaction মডেলের জন্য টেস্ট কেস।
class InventoryTransactionModelTest(TestCase):
    def setUp(self):
        # InventoryTransaction এর জন্য প্রয়োজনীয় মডেল তৈরি করা হচ্ছে।
        self.warehouse = Warehouse.objects.create(name="Transaction Warehouse")
        self.location_source = Location.objects.create(name="Source Loc", warehouse=self.warehouse)
        self.location_dest = Location.objects.create(name="Dest Loc", warehouse=self.warehouse)
        self.category = Category.objects.create(name="Groceries")
        self.uom_category = UnitOfMeasureCategory.objects.create(name="Units")
        self.unit_of_measure = UnitOfMeasure.objects.create(
            name="Packet", short_code="pkt", category=self.uom_category, ratio=1.0, is_base_unit=True
        )
        self.product = Product.objects.create(
            name="Milk", product_code="MILK001", category=self.category, price=2.50,
            unit_of_measure=self.unit_of_measure, tracking_method='none'
        )
        self.customer = Customer.objects.create(name="Test Customer")
        self.supplier = Supplier.objects.create(name="Test Supplier")
        self.lot_serial = LotSerialNumber.objects.create(
            product=self.product, location=self.location_source, lot_number="LOT-ABC", quantity=100
        )
        # প্রাথমিক স্টক তৈরি করা হচ্ছে যাতে ট্রানজেকশন সফল হয়
        Stock.objects.create(product=self.product, location=self.location_source, quantity=100)
        Stock.objects.create(product=self.product, location=self.location_dest, quantity=0)


    def test_receipt_transaction_creation(self):
        # Receipt ট্রানজেকশন তৈরি করা হচ্ছে।
        transaction = InventoryTransaction.objects.create(
            product=self.product,
            transaction_type='receipt',
            quantity=50,
            supplier=self.supplier,
            destination_location=self.location_source,
            lot_serial=self.lot_serial # লট/সিরিয়াল ট্র্যাকিং থাকলে
        )
        self.assertEqual(transaction.transaction_type, 'receipt')
        self.assertEqual(transaction.quantity, 50)
        self.assertEqual(transaction.destination_location, self.location_source)
        self.assertEqual(InventoryTransaction.objects.count(), 1)
        # নিশ্চিত করা হচ্ছে যে Product এর save() মেথড কল হয়েছে
        # (যা Product এর স্ট্যাটাস আপডেট করে)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'in_stock') # যেহেতু স্টক যোগ হয়েছে

    def test_sale_transaction_creation(self):
        # Sale ট্রানজেকশন তৈরি করা হচ্ছে।
        transaction = InventoryTransaction.objects.create(
            product=self.product,
            transaction_type='sale',
            quantity=10,
            customer=self.customer,
            source_location=self.location_source,
            lot_serial=self.lot_serial # লট/সিরিয়াল ট্র্যাকিং থাকলে
        )
        self.assertEqual(transaction.transaction_type, 'sale')
        self.assertEqual(transaction.quantity, 10)
        self.assertEqual(transaction.source_location, self.location_source)
        self.assertEqual(InventoryTransaction.objects.count(), 1)
        # নিশ্চিত করা হচ্ছে যে Product এর save() মেথড কল হয়েছে
        # (যা Product এর স্ট্যাটাস আপডেট করে)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'in_stock') # এখনো ইন স্টক, কারণ 100-10 = 90 > min_stock_level

    def test_transfer_transaction_creation(self):
        # Transfer ট্রানজেকশন তৈরি করা হচ্ছে।
        transaction = InventoryTransaction.objects.create(
            product=self.product,
            transaction_type='transfer',
            quantity=20,
            source_location=self.location_source,
            destination_location=self.location_dest
        )
        self.assertEqual(transaction.transaction_type, 'transfer')
        self.assertEqual(transaction.quantity, 20)
        self.assertEqual(transaction.source_location, self.location_source)
        self.assertEqual(transaction.destination_location, self.location_dest)
        self.assertEqual(InventoryTransaction.objects.count(), 1)

    def test_adjustment_transaction_creation(self):
        # Adjustment ট্রানজেকশন তৈরি করা হচ্ছে।
        transaction = InventoryTransaction.objects.create(
            product=self.product,
            transaction_type='adjustment',
            quantity=5, # পজিটিভ অ্যাডজাস্টমেন্ট
            destination_location=self.location_source,
            notes="Initial count adjustment"
        )
        self.assertEqual(transaction.transaction_type, 'adjustment')
        self.assertEqual(transaction.quantity, 5)
        self.assertEqual(InventoryTransaction.objects.count(), 1)

    def test_transaction_deletion(self):
        transaction = InventoryTransaction.objects.create(
            product=self.product, transaction_type='receipt', quantity=10, destination_location=self.location_source
        )
        transaction.delete()
        self.assertEqual(InventoryTransaction.objects.count(), 0)


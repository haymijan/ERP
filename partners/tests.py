# partners/tests.py

from django.test import TestCase
from .models import Customer, Supplier

# Customer মডেলের জন্য টেস্ট কেস।
# এটি নিশ্চিত করে যে Customer মডেল সঠিকভাবে তৈরি এবং সংরক্ষণ করা যায়।
class CustomerModelTest(TestCase):
    def test_customer_creation(self):
        # একটি নতুন Customer অবজেক্ট তৈরি করা হচ্ছে।
        customer = Customer.objects.create(
            name="Test Customer",
            email="test@example.com",
            phone="1234567890",
            address="123 Test St, Test City"
        )
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে ডাটাবেজে সংরক্ষণ করা হয়েছে।
        self.assertEqual(customer.name, "Test Customer")
        self.assertEqual(customer.email, "test@example.com")
        self.assertEqual(customer.phone, "1234567890")
        self.assertEqual(customer.address, "123 Test St, Test City")
        # নিশ্চিত করা হচ্ছে যে __str__ মেথডটি প্রত্যাশিত আউটপুট দেয়।
        self.assertEqual(str(customer), "Test Customer")
        # মোট গ্রাহকের সংখ্যা 1 কিনা তা নিশ্চিত করা হচ্ছে।
        self.assertEqual(Customer.objects.count(), 1)

    def test_customer_update(self):
        # একটি গ্রাহক তৈরি করা হচ্ছে।
        customer = Customer.objects.create(name="Old Name", email="old@example.com")
        # গ্রাহকের তথ্য আপডেট করা হচ্ছে।
        customer.name = "New Name"
        customer.save()
        # নিশ্চিত করা হচ্ছে যে তথ্য সফলভাবে আপডেট হয়েছে।
        updated_customer = Customer.objects.get(id=customer.id)
        self.assertEqual(updated_customer.name, "New Name")

    def test_customer_deletion(self):
        # একটি গ্রাহক তৈরি করা হচ্ছে।
        customer = Customer.objects.create(name="Delete Me", email="delete@example.com")
        # গ্রাহক মুছে ফেলা হচ্ছে।
        customer.delete()
        # নিশ্চিত করা হচ্ছে যে গ্রাহক আর ডাটাবেজে নেই।
        self.assertEqual(Customer.objects.count(), 0)

# Supplier মডেলের জন্য টেস্ট কেস।
# এটি নিশ্চিত করে যে Supplier মডেল সঠিকভাবে তৈরি এবং সংরক্ষণ করা যায়।
class SupplierModelTest(TestCase):
    def test_supplier_creation(self):
        # একটি নতুন Supplier অবজেক্ট তৈরি করা হচ্ছে।
        supplier = Supplier.objects.create(
            name="Test Supplier Inc.",
            contact_person="John Doe",
            email="contact@testsupplier.com",
            phone="0987654321",
            address="456 Supplier Ave, Supplier City"
        )
        # নিশ্চিত করা হচ্ছে যে অবজেক্টটি সফলভাবে ডাটাবেজে সংরক্ষণ করা হয়েছে।
        self.assertEqual(supplier.name, "Test Supplier Inc.")
        self.assertEqual(supplier.contact_person, "John Doe")
        self.assertEqual(supplier.email, "contact@testsupplier.com")
        self.assertEqual(supplier.phone, "0987654321")
        self.assertEqual(supplier.address, "456 Supplier Ave, Supplier City")
        # নিশ্চিত করা হচ্ছে যে __str__ মেথডটি প্রত্যাশিত আউটপুট দেয়।
        self.assertEqual(str(supplier), "Test Supplier Inc.")
        # মোট সরবরাহকারীর সংখ্যা 1 কিনা তা নিশ্চিত করা হচ্ছে।
        self.assertEqual(Supplier.objects.count(), 1)

    def test_supplier_update(self):
        # একটি সরবরাহকারী তৈরি করা হচ্ছে।
        supplier = Supplier.objects.create(name="Old Supplier", email="old_supplier@example.com")
        # সরবরাহকারীর তথ্য আপডেট করা হচ্ছে।
        supplier.name = "New Supplier"
        supplier.save()
        # নিশ্চিত করা হচ্ছে যে তথ্য সফলভাবে আপডেট হয়েছে।
        updated_supplier = Supplier.objects.get(id=supplier.id)
        self.assertEqual(updated_supplier.name, "New Supplier")

    def test_supplier_deletion(self):
        # একটি সরবরাহকারী তৈরি করা হচ্ছে।
        supplier = Supplier.objects.create(name="Supplier to Delete", email="delete_supplier@example.com")
        # সরবরাহকারী মুছে ফেলা হচ্ছে।
        supplier.delete()
        # নিশ্চিত করা হচ্ছে যে সরবরাহকারী আর ডাটাবেজে নেই।
        self.assertEqual(Supplier.objects.count(), 0)


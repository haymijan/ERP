# products/management/commands/find_mpo_files.py

import os
from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    help = 'Finds products with .mpo image format in either image or barcode fields.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Searching for products with .mpo images..."))

        problematic_products = []

        # Check all products
        for product in Product.objects.all():
            # Check the main image field
            if product.image and hasattr(product.image, 'path') and product.image.path:
                try:
                    file_extension = os.path.splitext(product.image.path)[1].lower()
                    if file_extension == '.mpo':
                        problematic_products.append({
                            "id": product.id,
                            "name": product.name,
                            "field": "Image",
                            "path": product.image.path
                        })
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Could not process image for Product ID {product.id}: {e}"))

            # Check the barcode image field
            if product.barcode and hasattr(product.barcode, 'path') and product.barcode.path:
                try:
                    file_extension = os.path.splitext(product.barcode.path)[1].lower()
                    if file_extension == '.mpo':
                        problematic_products.append({
                            "id": product.id,
                            "name": product.name,
                            "field": "Barcode",
                            "path": product.barcode.path
                        })
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Could not process barcode for Product ID {product.id}: {e}"))

        if problematic_products:
            self.stdout.write(self.style.WARNING("\n--- Found Products with .mpo Image ---"))
            for p_info in problematic_products:
                self.stdout.write(f"Product ID: {p_info['id']}, Name: '{p_info['name']}', Problem in field: '{p_info['field']}'")
            self.stdout.write(self.style.SUCCESS("\nPlease go to the admin panel to fix these products by removing or replacing the file."))
        else:
            self.stdout.write(self.style.SUCCESS("\nNo products found with .mpo image format in either 'image' or 'barcode' fields."))
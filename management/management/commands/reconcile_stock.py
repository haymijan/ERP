from django.core.management.base import BaseCommand
from django.db.models import Sum
from stock.models import Stock, LotSerialNumber, Warehouse
from products.models import Product

class Command(BaseCommand):
    help = 'Reconciles the main Stock table quantities with the sum of LotSerialNumber quantities for tracked products.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Starting lot reconciliation...'))

        # শুধুমাত্র যে প্রোডাক্টগুলো লট/সিরিয়াল দিয়ে ট্র্যাক করা হয়, সেগুলোর জন্য চালানো হবে
        tracked_products = Product.objects.filter(tracking_method__in=['lot', 'serial'])

        for product in tracked_products:
            # এই প্রোডাক্টটি যে সব ওয়্যারহাউজে আছে, সেগুলো খুঁজে বের করা
            warehouses_with_lots = Warehouse.objects.filter(
                locations__lots__product=product
            ).distinct()
            
            for warehouse in warehouses_with_lots:
                # এই ওয়্যারহাউজের সব লোকেশন থেকে এই প্রোডাক্টের লটের মোট পরিমাণ গণনা করা
                total_from_lots = LotSerialNumber.objects.filter(
                    product=product,
                    location__warehouse=warehouse
                ).aggregate(total=Sum('quantity'))['total'] or 0

                # ওয়্যারহাউজের জন্য বর্তমানে সংরক্ষিত মোট স্টক খুঁজে বের করা
                stock_record, created = Stock.objects.get_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={'quantity': 0}
                )
                
                stored_quantity = stock_record.quantity

                # যদি গড়মিল পাওয়া যায়
                if stored_quantity != total_from_lots:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Discrepancy found for "{product.name}" in "{warehouse.name}": '
                            f'Stored Total = {stored_quantity}, Sum of Lots = {total_from_lots}.'
                        )
                    )
                    
                    # সংরক্ষিত মোট স্টককে লটের মোট পরিমাণ দিয়ে আপডেট করা
                    stock_record.quantity = total_from_lots
                    stock_record.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'---> Stock for "{product.name}" in "{warehouse.name}" updated to {total_from_lots}.'
                        )
                    )

        self.stdout.write(self.style.SUCCESS('Lot reconciliation completed successfully.'))
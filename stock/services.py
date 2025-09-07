# stock/services.py

from django.db import transaction
from django.db.models import F
from .models import Stock, InventoryTransaction, Location, LotSerialNumber, Warehouse

class StockService:
    @staticmethod
    def change_stock(product, warehouse, quantity_change, transaction_type, user, 
                     content_object=None, location=None, lot_serial=None, notes=''):
        if quantity_change == 0:
            return

        with transaction.atomic():
            stock, created = Stock.objects.select_for_update().get_or_create(
                product=product,
                warehouse=warehouse,
                defaults={'quantity': 0}
            )

            if quantity_change < 0 and stock.quantity < abs(quantity_change):
                raise ValueError(f"'{product.name}' এর পর্যাপ্ত স্টক '{warehouse.name}'-এ নেই।")

            stock.quantity = F('quantity') + quantity_change
            stock.save(update_fields=['quantity'])

            if lot_serial:
                lot = LotSerialNumber.objects.select_for_update().get(id=lot_serial.id)
                if quantity_change < 0 and lot.quantity < abs(quantity_change):
                    raise ValueError(f"'{lot.lot_number}' লটে পর্যাপ্ত স্টক নেই।")
                
                lot.quantity = F('quantity') + quantity_change
                lot.save(update_fields=['quantity'])

            # --- ট্রানজেকশন লগিং এর জন্য নতুন এবং উন্নত লজিক ---
            source_loc = None
            dest_loc = None
            
            # content_object থেকে StockTransferRequest মডেলের instance আনা হচ্ছে
            StockTransferRequest = content_object.__class__

            if transaction_type == 'transfer_out' and isinstance(content_object, StockTransferRequest):
                source_loc = location
                # ডেস্টিনেশন ওয়্যারহাউসের প্রথম লোকেশনটি ডিফল্ট হিসেবে নেওয়া হলো
                dest_loc = content_object.destination_warehouse.locations.first()
            elif transaction_type == 'transfer_in' and isinstance(content_object, StockTransferRequest):
                # সোর্স ওয়্যারহাউসের প্রথম লোকেশনটি ডিফল্ট হিসেবে নেওয়া হলো
                # dispatched_lot থেকে আসল সোর্স লোকেশন পাওয়া আরও সঠিক হবে
                if content_object.dispatched_lot:
                    source_loc = content_object.dispatched_lot.location
                else: # ফলব্যাক
                    source_loc = content_object.source_warehouse.locations.first()
                dest_loc = location
            else: # Purchase, Sale, Adjustment ইত্যাদি।
                if quantity_change > 0: # স্টক বাড়লে
                    dest_loc = location
                else: # স্টক কমলে
                    source_loc = location

            InventoryTransaction.objects.create(
                product=product,
                warehouse=warehouse,
                quantity=quantity_change,
                transaction_type=transaction_type,
                user=user,
                content_object=content_object,
                source_location=source_loc,
                destination_location=dest_loc,
                lot_serial=lot_serial,
                notes=notes
            )
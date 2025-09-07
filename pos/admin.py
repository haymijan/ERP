# pos/admin.py

from django.contrib import admin
# POS অ্যাপের নিজস্ব কোনো মডেল না থাকায়, এখানে কোনো মডেল রেজিস্টার করার প্রয়োজন নেই।
# যদি ভবিষ্যতে POS-এর জন্য কোনো নতুন মডেল তৈরি করা হয়, তাহলে সেগুলোকে এখানে রেজিস্টার করতে হবে।

# উদাহরণস্বরূপ, যদি pos অ্যাপে PaymentMethod নামে কোনো মডেল থাকে:
# from .models import PaymentMethod
# @admin.register(PaymentMethod)
# class PaymentMethodAdmin(admin.ModelAdmin):
#     list_display = ('name',)


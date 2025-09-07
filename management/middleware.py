from django.core.exceptions import PermissionDenied
from django.conf import settings

class IPWhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # settings থেকে অনুমোদিত আইপি-গুলো লোড করুন
        self.allowed_ips = getattr(settings, 'ALLOWED_IPS', [])

    def __call__(self, request):
        # ক্লায়েন্টের আইপি অ্যাড্রেস নিন
        # প্রক্সি সার্ভারের পেছনে থাকলে X-Forwarded-For হেডার চেক করা জরুরি
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For হেডারে একাধিক আইপি থাকতে পারে, প্রথমটি নিন
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            # সরাসরি কানেকশনের জন্য REMOTE_ADDR ব্যবহার করুন
            ip = request.META.get('REMOTE_ADDR')

        # আইপিটি অনুমোদিত লিস্টে আছে কি না তা চেক করুন
        # DEBUG মোড চালু থাকলে এই মিডলওয়্যারটি বাইপাস করতে পারেন (ঐচ্ছিক)
        if settings.DEBUG:
            pass  # ডেভেলপমেন্টের সময় আইপি চেক না করতে চাইলে
        elif ip not in self.allowed_ips:
            # যদি আইপি অনুমোদিত না হয়, তাহলে PermissionDenied দেখান
            raise PermissionDenied("Your IP address is not allowed to access this site.")

        response = self.get_response(request)
        return response
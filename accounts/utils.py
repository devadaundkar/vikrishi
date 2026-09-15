from functools import wraps
from django.shortcuts import redirect

def custom_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'user_email' in request.session:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('/accounts/login/?next=' + request.path)
    return _wrapped_view

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from pymongo import MongoClient
from django.contrib.auth.decorators import login_required
from django.conf import settings
from functools import wraps
from accounts.utils import custom_login_required
import bcrypt

client = MongoClient(settings.MONGODB_URI)
db = client["farmingrent"]
users = db["users"]
support_collection = db["contact"]





def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        if users.find_one({"email": email}):
            messages.error(request, "Email already registered.")
            return redirect("signup")

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        users.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "password": hashed_password
        })

        messages.success(request, "Account created successfully!")
        return redirect("login")

    return render(request, "signup.html")

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = users.find_one({"email": email})
        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            request.session['user_email'] = email
            request.session['phone'] = user.get("phone")
            request.session['username'] = user.get("name", "User")
            return redirect("dashboard")

        messages.error(request, "Invalid credentials.")
        return redirect("login")

    return render(request, "login.html")



def dashboard(request):
    if 'user_email' in request.session:
        user_email = request.session['user_email']

        tools_collection = db['tools']
        bookings_collection = db['bookings']

        # Count of tools listed by this user
        tools_count = tools_collection.count_documents({'email': user_email})

        # Get tool IDs listed by this user
        user_tools = list(tools_collection.find({'email': user_email}))
        user_tool_ids = [tool['t_id'] for tool in user_tools]

        # Bookings made by this user
        user_bookings = list(bookings_collection.find({'booked_by': user_email}))
        bookings_count = len(user_bookings)

        # Bookings on the tools listed by this user
        bookings_on_user_tools = list(bookings_collection.find({'t_id': {'$in': user_tool_ids}}))


        total_earnings = 0
        for booking in bookings_on_user_tools:
            t_id = booking.get('tool_id')
            no_of_days = booking.get('days', 0)

            try:
                no_of_days = int(no_of_days)
            except (ValueError, TypeError):
                no_of_days = 0

            tool = tools_collection.find_one({'t_id': t_id})
            if tool:
                try:
                    price = int(tool.get('price', 0))
                except (ValueError, TypeError):
                    price = 0

                total_earnings += price * no_of_days

        return render(request, 'dashboard.html', {
            'username': request.session['username'],
            'email': user_email,
            'phone': request.session['phone'],
            'tools_count': tools_count,
            'bookings_count': bookings_count,
            'total_earnings': total_earnings
        })
    else:
        return redirect("login")






def logout_view(request):
    logout(request)
    return redirect('login')


@custom_login_required
def change_password(request):
    if 'user_email' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        email = request.session['user_email']
        user = users.find_one({"email": email})

        if not user or user.get("password") != current_password:
            messages.error(request, "Current password is incorrect.")
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')

        # Update password in MongoDB
        users.update_one({"email": email}, {"$set": {"password": new_password}})
        messages.success(request, "Password changed successfully.")
        return redirect('dashboard')

    return render(request, 'changepassword.html')


def contact_support(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        msg = request.POST.get("message")

        # Save the support message in MongoDB
        support_collection.insert_one({
            "name": name,
            "email": email,
            "message": msg,
            "status": "pending"
        })

        messages.success(request, "Your message has been sent successfully!")
        return redirect("contact_support")


    return render(request, "contact.html")


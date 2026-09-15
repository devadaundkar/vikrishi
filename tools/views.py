from django.shortcuts import render, redirect
from django.contrib import messages
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
import base64
from django.conf import settings
from .utils import check_if_farming_tool_hf
from django.core.files.storage import FileSystemStorage
from accounts.utils import custom_login_required

client = MongoClient(settings.MONGODB_URI)
db = client["farmingrent"]
toolsdb = db["tools"]
bookingsdb = db["bookings"]

@custom_login_required
def add_tool_view(request):
    if request.method == "POST":
        tool_name = request.POST.get("tool_name")
        tool_category = request.POST.get("tool_category")
        price = request.POST.get("price")
        condition = request.POST.get("condition")
        description = request.POST.get("description")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        timeslot = request.POST.getlist("timeslot")
        location = request.POST.get("location")
        delivery = request.POST.get("delivery")
        phone = request.POST.get("phone")
        user_email = request.session.get("user_email")

        images = []
        for image in request.FILES.getlist("images"):
            image_data = image.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            mime_type = image.content_type
            images.append(f"data:{mime_type};base64,{encoded_image}")

        tool_data = {
            "tool_name": tool_name,
            "tool_category": tool_category,
            "price": price,
            "condition": condition,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "timeslot": timeslot,
            "location": location,
            "delivery": delivery,
            "phone": phone,
            "email": user_email,
            "images" : images,
            "submitted_at": datetime.now()
        }

          # Insert the tool and get the inserted _id
        result = toolsdb.insert_one(tool_data)

        # Add a t_id field with the stringified _id
        toolsdb.update_one({"_id": result.inserted_id}, {"$set": {"t_id": str(result.inserted_id)}})
        messages.success(request, "Tool listed successfully!")
        return redirect("add_tool")

    return render(request, "add_tool.html")

@custom_login_required
def my_tools_view(request):
    if not request.session.get("user_email"):
        return redirect("login")

    user_email = request.session.get("user_email")
    tools = list(toolsdb.find({"email": user_email}))

    for tool in tools:
        booking = bookingsdb.find_one({"tool_id": tool["t_id"]})
        if booking:
            tool["booked_name"] = booking.get("name")
            tool["booked_by"] = booking.get("booked_by")  # or name if available
            tool["booking_date"] = booking.get("date")
            tool["booking_slot"] = booking.get("timeslot")
            tool["booking_contact"] = booking.get("phone")  # assuming it's stored
        else:
            tool["booked_by"] = None

    return render(request, "mytools.html", {"tools": tools})


@custom_login_required
def book_tools_view(request):
    filters = {}

    # Get current logged-in user
    logged_in_email = request.session.get('user_email')
    if logged_in_email:
        filters['email'] = {"$ne": logged_in_email}  # Exclude user's own tools

    # Apply filters
    location = request.GET.get('location')
    if location:
        filters['location'] = location

    category = request.GET.getlist('category')
    if category:
        filters['tool_category'] = {"$in": category}

    timeslot = request.GET.get('timeslot')
    if timeslot:
        filters['timeslot'] = timeslot

    if request.GET.get('availableOnly'):
        filters['available'] = True

    # Fetch all tools based on filters
    all_tools = list(toolsdb.find(filters))

    # Fetch all bookings
    all_bookings = list(bookingsdb.find({}))
    booked_by_others = set()
    booked_by_me = set()

    for booking in all_bookings:
        tool_id = str(booking['tool_id'])
        if booking['booked_by'] == logged_in_email:
            booked_by_me.add(tool_id)
        else:
            booked_by_others.add(tool_id)

    # Show tools only if:
    # - they are available
    # - or booked by current user
    visible_tools = []
    for tool in all_tools:
        tool_id_str = str(tool['t_id'])
        if tool_id_str not in booked_by_others:
            tool['t_id'] = tool_id_str
            visible_tools.append(tool)

    categories = ["Tractor", "Seeder", "Irrigation", "Harvester"]
    selected_categories = request.GET.getlist('category')

    return render(request, "booking.html", {
        "tools": visible_tools,
        "categories": categories,
        "selected_categories": selected_categories,
        "request": request,
        "booked_tool_ids": list(booked_by_me)  # So template knows what to disable
    })



def home(request):
    return render(request,'index.html')

@custom_login_required
def delete_tool_view(request, tool_id):
    toolsdb.delete_one({"t_id": tool_id})
    return redirect("my_tools")

@custom_login_required
def edit_tool_view(request, tool_id):
        # Check if user is logged in via session
    if not request.session.get("user_email"):
        return redirect("login")  # Replace 'login' with your login URL name
    tool = toolsdb.find_one({"t_id": tool_id})

    time_slots = ["Morning", "Afternoon", "Evening"]  # 👈 Add this

    if request.method == "POST":
        updated_data = {
            "tool_name": request.POST.get("tool_name"),
            "tool_category": request.POST.get("tool_category"),
            "price": request.POST.get("price"),
            "condition": request.POST.get("condition"),
            "description": request.POST.get("description"),
            "start_date": request.POST.get("start_date"),
            "end_date": request.POST.get("end_date"),
            "timeslot": request.POST.getlist("timeslot"),
            "location": request.POST.get("location"),
            "delivery": request.POST.get("delivery"),
            "phone": request.POST.get("phone"),
            "email": tool["email"],
        }
        toolsdb.update_one({"t_id": tool_id}, {"$set": updated_data})
        return redirect("my_tools")

    return render(request, "edit_tool.html", {"tool": tool, "time_slots": time_slots})

@custom_login_required
def tool_booking_detail(request, t_id):
    tool = toolsdb.find_one({"t_id": t_id})

    if not tool:
        return render(request, "404.html", {"message": "Tool not found."})

    if request.method == "POST":
        name = request.POST.get("name")
        days = int(request.POST.get("days", 1))
        delivery_option = request.POST.get("delivery")
        address = request.POST.get("address")
        phone = request.POST.get("phone")
        user_email = request.session.get("user_email")

        booking_data = {
            "tool_id": t_id,
            "tool_name": tool.get("tool_name"),
            "booked_by": user_email,
            "name": name,
            "days": days,
            "delivery_option": delivery_option,
            "address": address,
            "phone": phone,
            "price_per_day": tool.get("price"),
            "total_price": days * int(tool.get("price", 0)),
            "booking_time": datetime.now()
        }

        bookingsdb.insert_one(booking_data)

        messages.success(request, "Booking confirmed!")
        return redirect("viewtool")

    return render(request, "actualbooking.html", {"tool": tool})

@custom_login_required
def my_bookings_view(request):
    logged_in_email = request.session.get('user_email')

    if not logged_in_email:
        return redirect('login')  # redirect to login if not authenticated

    user_bookings = list(bookingsdb.find({"booked_by": logged_in_email}))

    # Get corresponding tool data for each booking
    booked_tools = []
    for booking in user_bookings:
        tool = toolsdb.find_one({"t_id": booking["tool_id"]})
        if tool:
            tool['t_id'] = str(tool['t_id'])
            booking['tool'] = tool
            booked_tools.append(booking)

    return render(request, "mybooking.html", {
        "bookings": booked_tools
    })


@custom_login_required
def viewtool(request):
    return render(request,'booking.html')


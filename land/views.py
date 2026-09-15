from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest,HttpResponse
from django.conf import settings
from django.contrib import messages
import json
import razorpay
import pymongo
import hmac
import hashlib
from bson.objectid import ObjectId
from twilio.rest import Client
from django.contrib.auth.decorators import login_required
from accounts.utils import custom_login_required

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

client = pymongo.MongoClient(settings.MONGODB_URI)
db = client["farmingrent"]
land_collection = db["land"]
land_booking_collection = db["landbooking"]

@custom_login_required
def add_farm(request):
    if request.method == "POST":
        owner = request.POST.get("ownerName")
        location = request.POST.get("location")
        contact = request.POST.get("contact")
        soilType = request.POST.get("soilType")
        ph = request.POST.get("ph")
        nitrogen = request.POST.get("nitrogen")
        phosphorous = request.POST.get("phosphorous")
        potassium = request.POST.get("potassium")
        area = request.POST.get("area")
        rate = request.POST.get("rate")
        image = request.FILES.get("farmImage")

        # Initial entry without t_id
        land_entry = {
            "owner": owner,
            "location": location,
            "contact": contact,
            "soilType": soilType,
            "ph": ph,
            "nitrogen": nitrogen,
            "phosphorous": phosphorous,
            "potassium": potassium,
            "area": area,
            "rate": rate,
            "image": image.read(),
            "user_email": request.session.get("user_email")
        }

        result = db.land.insert_one(land_entry)
        inserted_id = result.inserted_id

        # Update document with string version of _id
        db.land.update_one(
            {"_id": inserted_id},
            {"$set": {"t_id": str(inserted_id)}}
        )

        messages.success(request, "Farm submitted successfully!")
        return redirect("rent_land")

    return render(request, "add_farm.html")


def generate_map_embed(location):
    encoded = location.replace(" ", "+")
    return f"https://www.google.com/maps/embed/v1/place?q={encoded}&key=AIzaSyBbfgOajOjAh8LDejJbJtUh2cl3IPkw5pM"

@custom_login_required
def rent_land(request):
    # Get all lands
    lands = list(land_collection.find())
    land_id = request.GET.get("land_id")  # Get selected land ID from query params
    selected_land = None
    map_url = ""

    # Fetch all booked land_t_id's from the landbooking collection
    booked_land_ids = land_booking_collection.distinct("land_t_id")

    # Remove all booked lands from the lands list
    lands = [land for land in lands if land["t_id"] not in booked_land_ids]

    if land_id:
        try:
            # Fetch selected land based on the t_id (string version of _id)
            selected_land = land_collection.find_one({"t_id": land_id})
            if selected_land:
                map_url = generate_map_embed(selected_land["location"])
        except Exception as e:
            print("Invalid land_id or DB error:", e)
    elif lands:
        # Default to the last land if no land_id is provided
        selected_land = lands[-1]
        map_url = generate_map_embed(selected_land["location"])

    return render(request, "rentaland.html", {
        "lands": lands,
        "selected_land": selected_land,
        "map_url": map_url
    })


@custom_login_required
def landbooking(request):
    t_id = request.GET.get("t_id") or request.POST.get("land_t_id")
    amount = "₹0"
    razorpay_amount = 0
    land_data = None

    if not t_id:
        return JsonResponse({"error": "Land ID is required"}, status=400)

    # Get land data (works for both GET and POST)
    land_data = land_collection.find_one({"t_id": t_id})
    if not land_data:
        return JsonResponse({"error": "Land not found"}, status=404)

    try:
        rate = float(land_data.get("rate", 0))
        razorpay_amount = int(rate * 0.10 * 100)
        amount = round(rate * 0.10, 2)
        amount = int(amount)
    except (TypeError, ValueError) as e:
        print("Rate error:", e)
        return JsonResponse({"error": "Invalid rate value"}, status=400)

    if request.method == "POST":
        try:
            name = request.POST.get("name")
            address = request.POST.get("address")
            phone = request.POST.get("phone")
            book_from = request.POST.get("bookFrom")
            months = request.POST.get("months")
            details = request.POST.get("details")

            # Validate required fields
            if not all([name, address, phone, book_from, months]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            # Create Razorpay order
            order = razorpay_client.order.create({
                "amount": razorpay_amount,
                "currency": "INR",
                "payment_capture": 1
            })

            # Save booking info
            booking_entry = {
                "name": name,
                "address": address,
                "phone": phone,
                "book_from": book_from,
                "months": months,
                "details": details,
                "amount": str(round(rate * 0.10, 2)),
                "status": "Pending",
                "land_t_id": t_id,  # Use the t_id we already have
                "razor_order_id": order["id"]
            }
            result = land_booking_collection.insert_one(booking_entry)
            booking_id = str(result.inserted_id)
            return JsonResponse({
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "order_id": order["id"],
                "amount": razorpay_amount,
                "booking_id": booking_id,
                "name": name,
                "phone": phone
            })

        except Exception as e:
            print("Booking error:", e)
            return JsonResponse({"error": str(e)}, status=500)
        
    # GET request handling
    return render(request, "landbooking.html", {
        "t_id": t_id,
        "amount": amount,
        "land_data": land_data
    })

from django.http import JsonResponse
import subprocess
import os

from django.http import JsonResponse
from twilio.rest import Client
import os
from twilio.rest import Client
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from twilio.rest import Client
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from django.shortcuts import redirect
from django.contrib import messages

@csrf_exempt
def send_whatsapp(request):
    if request.method == "POST":
        try:
            land_t_id = request.POST.get("land_t_id")
            if not land_t_id:
                return redirect('rent_land')  # Or send any other redirect with a message

            # Fetch booking info using land_t_id (still needed for order_id)
            booking = land_booking_collection.find_one({"land_t_id": land_t_id}, sort=[('_id', -1)])
            if not booking:
                messages.error(request, "Booking not found")
                return redirect('rent_land')

            order_id = booking.get("razor_order_id")
            amount_paid = booking.get("amount")  # Fetch the amount paid from the booking
            person_name = booking.get("name", "Unknown")  # Name of the person who booked
            if not order_id:
                messages.error(request, "Payment ID missing in booking")
                return redirect('rent_land')

            if not amount_paid:
                messages.error(request, "Amount paid is missing in booking")
                return redirect('rent_land')

            # Fetch details from land_collection using land_t_id
            land = land_collection.find_one({"t_id": land_t_id})
            if not land:
                messages.error(request, "Land not found")
                return redirect('rent_land')

            # Phone number from land_booking_collection (for the person who booked the land)
            land_booking_phone = booking.get("phone")  # Assuming 'phone' is stored here
            if not land_booking_phone:
                messages.error(request, "Phone number not found in booking record")
                return redirect('rent_land')

            # Phone number from land_collection (for the landowner)
            land_contact = land.get("contact")
            if not land_contact:
                messages.error(request, "Phone number not found in land record")
                return redirect('rent_land')

            # Format for WhatsApp
            to_booking_phone = f"whatsapp:+91{land_booking_phone[-10:]}" if not land_booking_phone.startswith("whatsapp:") else land_booking_phone
            to_land_phone = f"whatsapp:+91{land_contact[-10:]}" if not land_contact.startswith("whatsapp:") else land_contact

            # Twilio credentials
            ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
            AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
            FROM_WHATSAPP_NUMBER = "whatsapp:+14155238886"

            # Send WhatsApp message to the booking contact (the person who booked the land)
            client = Client(ACCOUNT_SID, AUTH_TOKEN)
            booking_message = client.messages.create(
                body=f"Hi {person_name}! Your booking is confirmed ✅.\nPayment ID: {order_id}\nAmount Paid: ₹{amount_paid}",
                from_=FROM_WHATSAPP_NUMBER,
                to=to_booking_phone
            )

            # Send WhatsApp message to the landowner (the owner of the land)
            land_message = client.messages.create(
                body=f"Hi! A new booking has been confirmed ✅.\nBooking ID: {land_t_id}\nAmount Paid: ₹{amount_paid}\nBooked by: {person_name}\nPhone: {land_booking_phone}",
                from_=FROM_WHATSAPP_NUMBER,
                to=to_land_phone
            )

            # On success, add a success message and redirect back
            messages.success(request, "WhatsApp messages sent successfully!")
            return redirect('rent_land')

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('rent_land')

    return redirect('rent_land')  # Default redirect if the method is not POST





import matplotlib
matplotlib.use('Agg')  # Must be set before importing pyplot
import matplotlib.pyplot as plt
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.conf import settings
import os
import cv2
import numpy as np
from PIL import Image
import io
import base64
import time

def analyze_soil_color(image_path):
    """Analyze the dominant colors in the soil image"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {'error': 'Could not read image file'}
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pixels = img.reshape(-1, 3)
        avg_color = np.clip(np.mean(pixels, axis=0), 0, 255).astype(int)
        color_variance = np.var(pixels, axis=0)
        
        return {
            'average_color': avg_color.tolist(),
            'color_variance': color_variance.tolist(),
            'color_diversity': float(np.mean(color_variance))
        }
    except Exception as e:
        return {'error': str(e)}

def detect_moisture(image_path):
    """Simple moisture detection based on dark pixel percentage"""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {'error': 'Could not read image file'}
        
        _, thresholded = cv2.threshold(img, 70, 255, cv2.THRESH_BINARY_INV)
        moisture_percentage = (np.sum(thresholded == 255) / (img.shape[0] * img.shape[1])) * 100
        
        # Create figure without using GUI
        fig = plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)
        plt.imshow(img, cmap='gray')
        plt.title('Original')
        
        plt.subplot(1, 2, 2)
        plt.imshow(thresholded, cmap='gray')
        plt.title(f'Moisture Detection ({moisture_percentage:.1f}%)')
        
        # Save to buffer and close properly
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)  # Explicitly close the figure
        buf.seek(0)
        
        return {
            'moisture_percentage': float(moisture_percentage),
            'moisture_plot': base64.b64encode(buf.read()).decode('ascii')
        }
    except Exception as e:
        return {'error': str(e)}

def analyze_texture(image_path):
    """Analyze soil texture using edge detection"""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {'error': 'Could not read image file'}
        
        edges = cv2.Canny(img, 100, 200)
        edge_density = (np.sum(edges == 255) / (img.shape[0] * img.shape[1])) * 100
        
        # Create figure without using GUI
        fig = plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)
        plt.imshow(img, cmap='gray')
        plt.title('Original')
        
        plt.subplot(1, 2, 2)
        plt.imshow(edges, cmap='gray')
        plt.title(f'Texture Analysis (Density: {edge_density:.1f}%)')
        
        # Save to buffer and close properly
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)  # Explicitly close the figure
        buf.seek(0)
        
        return {
            'edge_density': float(edge_density),
            'texture_plot': base64.b64encode(buf.read()).decode('ascii')
        }
    except Exception as e:
        return {'error': str(e)}

@custom_login_required
def soil_analysis_view(request):
    analysis_results = None
    original_image = None
    moisture_data = None
    texture_data = None
    color_data = None

    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # Save uploaded file
            uploaded_file = request.FILES['image']
            file_path = os.path.join(settings.MEDIA_ROOT, 'soil_image.jpg')
            
            # Use a unique filename to prevent conflicts
            filename = f"soil_{request.user.id}_{int(time.time())}.jpg"
            file_path = os.path.join(settings.MEDIA_ROOT, 'soil_images', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with default_storage.open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Convert to base64 for display
            with Image.open(file_path) as img:
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                original_image = base64.b64encode(buffered.getvalue()).decode('ascii')
            
            # Perform analyses
            color_data = analyze_soil_color(file_path)
            moisture_data = detect_moisture(file_path)
            texture_data = analyze_texture(file_path)
            
            analysis_results = {
                'color': color_data,
                'moisture': moisture_data,
                'texture': texture_data
            }
            
            # Clean up the temporary file
            try:
                os.remove(file_path)
            except:
                pass
            
        except Exception as e:
            analysis_results = {'error': str(e)}

    context = {
        'analysis': analysis_results,
        'original_image': original_image,
        'moisture_data': moisture_data,
        'texture_data': texture_data,
        'color_data': color_data
    }
    
    return render(request, 'base.html', context)
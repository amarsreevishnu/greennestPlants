import random
import re

from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse
from datetime import datetime
from django.contrib.auth import update_session_auth_hash
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import EmailOTP,Profile, Address
from products.models import Product


User = get_user_model()  # Gets CustomUser model


def user_signup(request):
    if request.user.is_authenticated:
        return redirect('user_home')
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
    
        if not name or not email or not password or not password_confirm:
            messages.error(request, "All fields are required.")
            return redirect('user_signup')
        
        if not re.match(r'^[A-Za-z ]+$', name):
            messages.error(request, "Name should only contain letters and spaces.")
            return redirect('user_signup')

        if len(password)<4:
            messages.error(request,"Password length must be at least four.")
            return redirect('user_signup')

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('user_signup')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('user_signup')
        user = User.objects.create(
            username=email,   
            email=email,
            first_name=name,  
            password=make_password(password),  
            is_active=False  
        )
        # Store user id in session
        request.session['pending_user_id'] = user.id
        
        send_otp_email(user) 
        return redirect('verify_otp')

    return render(request, 'users/user_signup.html')

def send_otp_email(user):
    otp = f"{random.randint(1000, 9999)}"
    print(otp)
    EmailOTP.objects.update_or_create(user=user, defaults={'otp': otp, 'created_at': timezone.now()})
    send_mail(
        "Your OTP Code",
        f"Your OTP is {otp}. It expires in 1 minute.",
        "greennest.ecom@gmail.com",
        [user.email],
    )

def verify_otp(request):
    # redirect to signup if no session
    user_id = request.session.get('pending_user_id')
    if 'pending_user_id' not in request.session:
        return redirect('user_signup')  
    

    user = get_object_or_404(User, pk=user_id)
    otp_obj = get_object_or_404(EmailOTP, user=user)

    if request.method == "POST":
        entered_otp = (
        request.POST.get("otp1", "") +
        request.POST.get("otp2", "") +
        request.POST.get("otp3", "") +
        request.POST.get("otp4", "")
        )
        if len(entered_otp) != 4:
            messages.error(request, "Please enter the complete 4-digit OTP.")
            return render(request, "users/verify_otp.html")
        
        if otp_obj.is_expired():
            otp_obj.delete()
            context = {"otp_expired": True}
            return render(request, "users/verify_otp.html", context)
        
        if entered_otp == otp_obj.otp:
            user.is_active = True
            user.save()
            otp_obj.delete()
            del request.session['pending_user_id']
            messages.success(request, "Your account has been verified! Please log in.")
            return redirect('user_home')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
    

    return render(request, "users/verify_otp.html")


def resend_otp_ajax(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":

        user_id = request.session.get('pending_user_id')
        if not user_id:
            return JsonResponse({"success": False, "message": "Session expired. Please sign up again."})

        user = get_object_or_404(User, pk=user_id)
        otp_obj, created = EmailOTP.objects.get_or_create(user=user)

        if otp_obj.created_at and timezone.now() - otp_obj.created_at < timedelta(minutes=1):
            remaining = 60 - int((timezone.now() - otp_obj.created_at).total_seconds())
            return JsonResponse({
                "success": False, 
                "message": f"Please wait {remaining} seconds before requesting a new OTP.",
                "remaining": remaining
            })

        send_otp_email(user)
        return JsonResponse({"success": True, "message": "New OTP sent successfully."})

    return JsonResponse({"success": False, "message": "Invalid request."})


@never_cache
def user_login(request):
    
    if request.user.is_authenticated:
        return redirect('user_home')
    if request.method=='POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect('user_login')
        
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)  
            return redirect('user_home')
        else:
            messages.error(request, "Invalid credentials or user does not exist.")
    
    return render(request, 'users/user_login.html')

def user_logout(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out successfully.")
    return redirect('user_login')

@never_cache
@login_required(login_url='user_login')
def user_home(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'users/user_home.html', {'user': request.user,'products':products})

def forget_password(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Email is required.")
            return redirect('forget_password')
        
        try:
            user = User.objects.get(email=email)
            send_otp_email(user)
            request.session['reset_user_id'] = user.id
            messages.success(request, "OTP sent to your email. Please verify to reset your password.")
            return redirect('verify_reset_otp')
        except User.DoesNotExist:
            messages.error(request, "User does not exist.")
    
    return render(request, 'users/user_Forget_Password.html')

def verify_reset_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please request a new OTP.")
        return redirect('forget_password')

    user = get_object_or_404(User, pk=user_id)
    otp_obj = get_object_or_404(EmailOTP, user=user)
    
    if request.method == "POST":
        entered_otp = (
            request.POST.get("otp1", "") +
            request.POST.get("otp2", "") +
            request.POST.get("otp3", "") +
            request.POST.get("otp4", "")
        )

        if otp_obj.is_expired():
            context = {"otp_expired": True}
            return render(request, "users/verify_reset_otp.html", context)

        if entered_otp == otp_obj.otp:
            otp_obj.delete() # OTP verified, delete it
            # Add a flag so reset page can be shown
            request.session['otp_verified_for_reset'] = True
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "users/verify_reset_otp.html")



def reset_password(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified_for_reset', False)
    
    if not user_id or not otp_verified:
        messages.error(request, "Unauthorized access or session expired.")
        return redirect('forget_password')

    user = get_object_or_404(User, pk=user_id)
    

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        print(new_password,confirm_password)
        # Password match check
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')

        # Update password
        user.set_password(new_password)
        user.save()

        # Clear reset session
        request.session.pop('reset_user_id', None)
        request.session.pop('otp_verified_for_reset', None)  

        messages.success(request, "Password reset successful! Please log in.")
        return redirect('user_login')

    return render(request, "users/user_reset_password.html")


# ---------------------user profile section-------------------------------------------------


@login_required(login_url='user_login')
@never_cache
def profile_detail(request):
    
    profile = request.user.profile
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    return render(request, "users/profile_detail.html",{"profile": profile, "default_address":default_address})

@login_required(login_url='user_login') 
@never_cache
def profile_edit(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        # Get User model fields
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")

        # Get Profile model fields
        phone = request.POST.get("phone")
        dob_str = request.POST.get("dob")
        gender = request.POST.get("gender")
        avatar = request.FILES.get("image")  

        # Update User model fields
        user.first_name = full_name  
        user.save()

        # Update Profile model fields
        profile.phone = phone
        profile.gender = gender

        if dob_str:
            try:
                profile.dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect("profile_edit")

        if avatar:
            profile.avatar = avatar 
        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("profile_detail")

    return render(request, "users/profile_edit.html", {"profile": profile})

@login_required(login_url='user_login')
@never_cache
def profile_change_password(request):
    

    if request.method=="POST":
        current_password=request.POST.get("current_password")
        new_password=request.POST.get("new_password")
        confirm_new_password=request.POST.get("confirm_new_password")

        user = request.user
        if user.check_password(current_password):
            if new_password == confirm_new_password:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect("profile_detail")
            else:
                messages.error(request, "New passwords do not match.")
        else:
            messages.error(request, "Current password is incorrect.")


    return render(request,"users/profile_change_password.html")



@login_required(login_url="user_login")
@never_cache
def change_email(request):
    
    if request.method=="POST":
        current_email=request.POST.get("current_email","").strip()
        new_email = request.POST.get("new_email", "").strip()

        if not new_email or not current_email:
            messages.error(request, "Both current and new email are required.")
            return redirect("profile_change_email")

        if current_email != request.user.email:
            messages.error(request, "Current email does not match your account.")
            return redirect("update_email")
        
        if new_email == request.user.email:
            messages.error(request, "New email cannot be the same as your current email.")
            return redirect("update_email")
        
        # 2. Format check (basic)
        try:
            validate_email(new_email)
        except ValidationError:
            messages.error(request, "Enter a valid New Email address.")
            return redirect("profile_change_email")

        # 3. Unique check in DB (ignore current user)
        if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
            messages.error(request, "This New Email is already in use.")
            return redirect("profile_change_email")

        # 4. Update email
        request.user.email = new_email
        request.user.save()
        messages.success(request, "Your email was updated successfully.")
        return redirect("profile_detail")
        
        
    
    return render(request,'users/profile_change_email.html')


@login_required
def address_list(request):
    addresses = request.user.addresses.all()
    return render(request, "users/user_address.html", {"addresses": addresses})


@login_required
@never_cache
def address_add(request):
    
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        line1 = request.POST.get("line1")   
        line2 = request.POST.get("line2")   
        city = request.POST.get("city")
        state = request.POST.get("state")
        postal_code = request.POST.get("postal_code")
        country = request.POST.get("country")
        is_default = request.POST.get("is_default") == "on"
        
        if is_default:
            # Remove default from other addresses
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            line1=line1,
            line2=line2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            is_default=is_default
        )
        messages.success(request, "Address updated successfully!")
        return redirect("address_list")
    return render(request, "users/user_add_address.html")


@login_required
def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        address.full_name = request.POST.get("full_name")
        address.phone = request.POST.get("phone")
        address.line1 = request.POST.get("line1")
        address.line2 = request.POST.get("line2")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.postal_code = request.POST.get("postal_code")
        address.country = request.POST.get("country")
        address.address_type = request.POST.get("address_type")
        address.is_default = request.POST.get("is_default") == "on"

        if address.is_default:
            # Remove default from other addresses
            Address.objects.filter(user=request.user, is_default=True).exclude(pk=address.pk).update(is_default=False)
            
        address.save()
        messages.success(request, "Address updated successfully!")
        return redirect("address_list")

    
    return render(request, "users/user_add_address.html", {"address": address})

@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully!")
    return redirect("address_list")
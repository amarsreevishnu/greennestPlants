import random
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

from .models import EmailOTP


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
            is_active=False # User is inactive until email verification
        )
        # Store user id in session
        request.session['pending_user_id'] = user.id
        # Send OTP email
        send_otp_email(user)

       
        return redirect('verify_otp')

    return render(request, 'users/user_signup.html')

def send_otp_email(user):
    otp = f"{random.randint(1000, 9999)}"
    EmailOTP.objects.update_or_create(user=user, defaults={'otp': otp, 'created_at': timezone.now()})
    send_mail(
        "Your OTP Code",
        f"Your OTP is {otp}. It expires in 1 minute.",
        "greennest.ecom@gmail.com",
        [user.email],
    )

def verify_otp(request):
    
    user_id = request.session.get('pending_user_id')
    if 'pending_user_id' not in request.session:
        return redirect('user_signup')  # redirect to signup if no session
    

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
            return render(request, "users/verify_otp.html", context)
        
        if entered_otp == otp_obj.otp:
            user.is_active = True
            user.save()
            otp_obj.delete()
            del request.session['pending_user_id']
            messages.success(request, "Your account has been verified! Please log in.")
            return redirect('user_login')
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
        print(email, password)
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect('user_login')
        
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)  # No backend arg needed now
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
@login_required
def user_home(request):
    return render(request, 'users/user_home.html', {'user': request.user})

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

        # Password match check
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')

        # Update password
        user.password = make_password(new_password)
        user.save()

        # Clear reset session
        request.session.pop('reset_user_id', None)
        request.session.pop('otp_verified_for_reset', None)  # if you set this earlier

        messages.success(request, "Password reset successful! Please log in.")
        return redirect('user_login')

    return render(request, "users/user_reset_password.html")
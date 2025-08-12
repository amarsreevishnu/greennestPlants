from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model, login

# Create your views here.
User = get_user_model()  # Gets your CustomUser model


def user_signup(request):
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
            username=email,   # i am using email as username
            email=email,
            first_name=name,  
            password=make_password(password)  # hash password
        )
        login(request, user)
        messages.success(request, "Registration successful!")
        return redirect('home')
    return render(request, 'users/user_signup.html')


def verify_otp(request):
    if request.method=='POST':
        entered_otp = request.POST.get('otp')
        user_id = request.session.get('pending_user_id')
        if not user_id:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect('signup')

def user_login(request):
    
    if request.method=='POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(email, password)
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect('user_login')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                login(request, user)
                messages.success(request, "Login successful!")
                return redirect('home')
            else:
                messages.error(request, "Invalid credentials.")
        except User.DoesNotExist:
            messages.error(request, "User does not exist.")
    # Logic to retrieve user profile information
    return render(request, 'users/user_login.html', {})

from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import FineTuningQuery, UserFeedback, Profile, UserRequestCount
from .ai_engine import handle_user_query
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProfileForm, CustomPasswordChangeForm, CustomUserCreationForm
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.utils import timezone
from pytz import timezone as pytz_timezone
import datetime


@login_required
def home(request):
    return render(request, "ai_queries/home.html")


def about(request):
    return render(request, 'ai_queries/about_greeting.html')


@login_required
def generate_response(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input', '')

        if user_input:
            try:
                # Hard-code to always use Azerbaijan-Baku time zone
                azerbaijan_tz = pytz_timezone('Asia/Baku')
                today = datetime.datetime.now(azerbaijan_tz).date()
                with transaction.atomic():
                    request_count, created = UserRequestCount.objects.get_or_create(
                        user=request.user,
                        date=today,
                        defaults={'count': 0}
                    )
                    if request_count.count >= 10:
                        return JsonResponse(
                            {
                                'response': "Sorğu limitinizi keçmisiniz.",
                                'rate_limit': {
                                    'limit': 10,
                                    'remaining': 0,
                                    'reset': today + timezone.timedelta(days=1)
                                }
                            },
                            status=429
                        )
                    request_count.count += 1
                    request_count.save()

                # Call the AI handler
                gpt_response = handle_user_query(user_input)

                # Create a FineTuningQuery record
                fine_tuning_query = FineTuningQuery.objects.create(
                    query_text=user_input,
                    gpt_response=gpt_response
                )

                # Calculate remaining requests
                remaining = 10 - request_count.count

                return JsonResponse(
                    {
                        'response': gpt_response,
                        'query_id': fine_tuning_query.id,
                        'rate_limit': {
                            'limit': 10,
                            'remaining': remaining,
                            'reset': today + timezone.timedelta(days=1)
                        }
                    }
                )

            except Exception as e:
                return JsonResponse({'response': f"Error: {str(e)}"}, status=500)
        else:
            return JsonResponse({'response': "Zəhmət olmasa düzgün sorğu daxil edin."}, status=400)
    return JsonResponse({'response': "Yanlış sorğu metodu."}, status=405)


def save_feedback(request):
    if request.method == 'POST':
        query_id = request.POST.get('query_id')
        if not query_id or not query_id.isdigit():
            return JsonResponse({'status': 'error', 'message': 'Invalid query ID.'}, status=400)

        doc_title = request.POST.get('docTitle')
        relevant_article = request.POST.get('relevantArticle')
        feedback_text = request.POST.get('feedbackText')

        try:
            user_query = FineTuningQuery.objects.get(id=int(query_id))
            UserFeedback.objects.create(
                user_query=user_query,
                doc_title=doc_title,
                relevant_article=relevant_article,
                feedback_text=feedback_text
            )
            return JsonResponse({'status': 'success', 'message': 'Feedback submitted successfully!'})
        except FineTuningQuery.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Related query not found.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


# Registration View
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Save custom fields to Profile
            profile = Profile.objects.get(user=user)
            profile.name = form.cleaned_data.get('name', '')
            profile.phone = form.cleaned_data.get('phone', '')
            profile.save()
            # Log in the user after registration
            login(request, user)
            messages.success(request, "Qeydiyyat uğurlu oldu!")
            return redirect('home')
        else:
            messages.error(request, "Zəhmət olmasa aşağıdakı səhvləri düzəldin.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'ai_queries/register.html', {'form': form})


# Login View
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Giriş uğurla başa çatdı!')
            return redirect('home')
        else:
            messages.error(request, 'İstifadəçi adı və ya parol səhvdir.')
    return render(request, 'ai_queries/login.html')


# Logout View
def user_logout(request):
    logout(request)
    return redirect('login')


# Profile Settings View
@login_required
def profile_settings(request):
    profile = request.user.profile
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, instance=profile, user_instance=request.user)
        password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)

        # Determine if the user is attempting to change the password
        password_fields = ['old_password', 'new_password1', 'new_password2']
        password_fields_filled = any(request.POST.get(field) for field in password_fields)

        if profile_form.is_valid() and (not password_fields_filled or password_form.is_valid()):
            profile_form.save()

            if password_fields_filled:
                password_form.save()
                update_session_auth_hash(request, password_form.user)  # Keeps the user logged in
                messages.success(request, 'Profil və şifrə uğurla yeniləndi!')
            else:
                messages.success(request, 'Profil uğurla yeniləndi!')

            return redirect('home')  # Redirect to home after update
        else:
            messages.error(request, 'Zəhmət olmasa aşağıdakı səhvləri düzəldin.')
    else:
        profile_form = ProfileForm(instance=profile, user_instance=request.user)
        password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'ai_queries/profile_settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })

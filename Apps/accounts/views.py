from django.contrib.auth import logout
from django.shortcuts import redirect, render
from Apps.accounts.models import UserDashboardPage


def get_login_url():
    from Apps.accounts.models import LoginPage
    login_page = LoginPage.objects.live().first()
    return login_page.url if login_page else '/login/'


def user_dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect(get_login_url())
    dashboard_page = UserDashboardPage.objects.live().first()
    context = dashboard_page.get_context(request) if dashboard_page else {}
    context.update({'page': dashboard_page, 'user': request.user})
    from Apps.blogs.models import BlogPage
    context['recent_blogs'] = BlogPage.objects.all().order_by('-latest_revision_created_at')[:5]
    return render(request, 'accounts/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect(get_login_url())


def settings_view(request):
    if not request.user.is_authenticated:
        return redirect(get_login_url())
    dashboard_page = UserDashboardPage.objects.live().first()
    context = dashboard_page.get_context(request) if dashboard_page else {}
    
    if request.method == 'POST':
        from django.contrib import messages
        from django.contrib.auth import update_session_auth_hash

        action_type = request.POST.get('action_type')

        if action_type == 'update_password':
            old_pass = request.POST.get('old_password', '')
            new_pass1 = request.POST.get('new_password1', '')
            new_pass2 = request.POST.get('new_password2', '')

            if not request.user.check_password(old_pass):
                messages.error(request, "Current password is incorrect!")
            elif new_pass1 != new_pass2:
                messages.error(request, "New passwords do not match!")
            elif len(new_pass1) < 6:
                messages.error(request, "New password must be at least 6 characters long!")
            else:
                request.user.set_password(new_pass1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully!")
            return redirect('/settings/#security')
        else:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            avatar_file = request.FILES.get('avatar')

            user = request.user
            if first_name is not None:
                user.first_name = first_name.strip()
            if last_name is not None:
                user.last_name = last_name.strip()
            if avatar_file and hasattr(user, 'avatar'):
                user.avatar = avatar_file

            user.save()
            messages.success(request, "Profile details updated successfully!")
            return redirect('/settings/')

    context.update({
        'page': dashboard_page,
        'user': request.user,
        'active_tab': 'settings',
    })
    return render(request, 'accounts/settings.html', context)

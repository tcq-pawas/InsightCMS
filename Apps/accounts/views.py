from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.db import models
from Apps.accounts.models import UserDashboardPage


def get_login_url():
    from Apps.accounts.models import LoginPage
    login_page = LoginPage.objects.live().first()
    return login_page.url if login_page else '/login/'


def user_dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect(get_login_url())

    from django.utils import timezone
    from Apps.companies.models import UserProfile, CompanyMembership
    from Apps.accounts.models import User
    from Apps.blogs.models import BlogPage

    # 1. Logged-in user ki company find karein
    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else None

    dashboard_page = UserDashboardPage.objects.live().first()
    context = dashboard_page.get_context(request) if dashboard_page else {}
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    # 2. Scope blogs according to user role:
    # - If Super Admin / Company Admin -> View all blogs across company
    # - If Employee (Company User) -> View ONLY their own written blogs
    is_employee = (request.user.role == User.Role.COMPANY_USER)
    
    if is_employee:
        my_blogs_qs = BlogPage.objects.filter(author=request.user)
        if company:
            my_blogs_qs = my_blogs_qs.filter(company=company)
        dashboard_blogs_qs = my_blogs_qs
    else:
        dashboard_blogs_qs = BlogPage.objects.all()
        if company:
            dashboard_blogs_qs = dashboard_blogs_qs.filter(company=company)

    # Calculate real-time counts for cards
    today = timezone.localdate()
    total_blogs_count = dashboard_blogs_qs.count()
    published_blogs_count = dashboard_blogs_qs.filter(live=True).count()
    unpublished_blogs_count = dashboard_blogs_qs.filter(live=False).count()
    today_blogs_count = dashboard_blogs_qs.filter(
        latest_revision_created_at__date=today
    ).count()

    # 3. Writers / Authors data calculation (for Company Admin view)
    # Fetch team members of this company or all authors who wrote blogs
    writers_data = []
    if not is_employee:
        if company:
            company_users = User.objects.filter(
                models.Q(userprofile__company=company) | models.Q(company_memberships__company=company)
            ).distinct()
        else:
            company_users = User.objects.all()

        all_company_blogs = BlogPage.objects.all()
        if company:
            all_company_blogs = all_company_blogs.filter(company=company)

        for u in company_users:
            user_blogs = all_company_blogs.filter(author=u)
            user_total = user_blogs.count()
            user_published = user_blogs.filter(live=True).count()
            user_unpublished = user_blogs.filter(live=False).count()

            writers_data.append({
                'user': u,
                'name': u.get_full_name() or u.admin_username or u.email.split('@')[0],
                'email': u.email,
                'role': u.get_role_display(),
                'total_posts': user_total,
                'published': user_published,
                'unpublished': user_unpublished,
            })

        # Sort writers by total posts descending
        writers_data.sort(key=lambda x: x['total_posts'], reverse=True)

    # For employee view: fetch their own blogs with full details
    employee_blogs = dashboard_blogs_qs.select_related('category', 'featured_image').order_by('-latest_revision_created_at')

    context.update({
        'page': dashboard_page,
        'sidebar_links': sidebar_links,
        'user': request.user,
        'company': company,
        'is_employee': is_employee,
        'total_blogs_count': total_blogs_count,
        'today_blogs_count': today_blogs_count,
        'published_blogs_count': published_blogs_count,
        'unpublished_blogs_count': unpublished_blogs_count,
        'writers_data': writers_data,
        'employee_blogs': employee_blogs,
        'recent_blogs': dashboard_blogs_qs.order_by('-latest_revision_created_at')[:5]
    })
    return render(request, 'accounts/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect(get_login_url())


def settings_view(request):
    if not request.user.is_authenticated:
        return redirect(get_login_url())

    from Apps.accounts.models import SettingsPage
    settings_page = SettingsPage.objects.live().first()
    dashboard_page = UserDashboardPage.objects.live().first()

    page_obj = settings_page if settings_page else dashboard_page
    context = page_obj.get_context(request) if page_obj else {}
    
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

        elif action_type == 'add_team_member':
            from Apps.companies.models import UserProfile, CompanyMembership
            from Apps.accounts.models import User

            # Sirf Company Admin ya Super Admin hi member add kar sakta hai
            if request.user.role not in [User.Role.SUPER_ADMIN, User.Role.COMPANY_ADMIN]:
                messages.error(request, "Permission denied. Only Company Admins can add team members.")
                return redirect('/settings/#team')

            profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
            company = profile.company if profile else None

            if not company:
                messages.error(request, "No company linked to your account.")
                return redirect('/settings/#team')

            member_email = request.POST.get('member_email', '').strip().lower()
            member_first_name = request.POST.get('member_first_name', '').strip()
            member_last_name = request.POST.get('member_last_name', '').strip()
            member_password = request.POST.get('member_password', '')

            if not member_email or not member_password:
                messages.error(request, "Email and password are required for new team member.")
                return redirect('/settings/#team')

            if User.objects.filter(email=member_email).exists():
                messages.error(request, f"User with email '{member_email}' already exists.")
                return redirect('/settings/#team')

            # Create User as COMPANY_USER (Writer / Editor) - pre-approved by company admin
            new_user = User.objects.create_user(
                email=member_email,
                password=member_password,
                first_name=member_first_name,
                last_name=member_last_name,
                company_name=company.company_name,
                role=User.Role.COMPANY_USER,
                is_staff=True,       # Wagtail CMS editorial access
                is_active=True,
                is_approved=True     # Pre-approved by Company Admin (No super admin approval needed)
            )

            # Link to this company
            CompanyMembership.objects.create(
                user=new_user,
                company=company,
                role=CompanyMembership.Role.EDITOR
            )
            UserProfile.objects.create(
                user=new_user,
                company=company
            )

            messages.success(request, f"Team member '{member_first_name or member_email}' added successfully to {company.company_name}!")
            return redirect('/settings/#team')

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

    # Fetch active company & team members
    from Apps.companies.models import UserProfile
    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else None

    team_members = []
    if company:
        team_members = UserProfile.objects.filter(company=company).select_related('user')

    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []
    context.update({
        'page': page_obj,
        'sidebar_links': sidebar_links,
        'user': request.user,
        'company': company,
        'team_members': team_members,
        'active_tab': 'settings',
    })
    return render(request, 'accounts/settings.html', context)


def forgot_password_view(request):
    from django.contrib import messages
    from Apps.accounts.models import LoginPage
    from Apps.accounts.models import User

    login_page = LoginPage.objects.live().first()
    login_url = login_page.url if login_page else '/login/'

    submitted = False
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        # Even if user does not exist, show success message for security best practice
        messages.success(request, f"If an account exists with {email}, a password reset link has been sent.")
        submitted = True

    return render(request, 'accounts/forgot_password.html', {
        'login_url': login_url,
        'submitted': submitted
    })

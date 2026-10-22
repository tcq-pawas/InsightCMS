from django.contrib.auth import logout
from django.contrib import messages
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
    if not company:
        membership = CompanyMembership.objects.filter(user=request.user).select_related('company').first()
        if membership:
            company = membership.company
    if not company and request.user.role == User.Role.SUPER_ADMIN:
        if request.user.company_name:
            from Apps.companies.models import Company
            company = Company.objects.filter(company_name__iexact=request.user.company_name).first()

    dashboard_page = UserDashboardPage.objects.live().first()
    context = dashboard_page.get_context(request) if dashboard_page else {}
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    # 2. Scope blogs according to user role:
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

    # Real Analytics Data (Blogger-style Stats)
    from datetime import timedelta
    from django.db.models import Count
    from Apps.blogs.models import BlogPostView

    views_qs = BlogPostView.objects.all()
    if company:
        views_qs = views_qs.filter(company=company)
    if is_employee:
        views_qs = views_qs.filter(blog__author=request.user)

    total_views_count = views_qs.count()
    unique_visitors_count = views_qs.values('session_key').distinct().count()
    today_views_count = views_qs.filter(created_at__date=today).count()

    # 7-day daily traffic chart
    chart_labels = []
    chart_views = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        chart_labels.append(d.strftime('%b %d'))
        chart_views.append(views_qs.filter(created_at__date=d).count())

    # Top popular articles by view count
    popular_blogs = list(dashboard_blogs_qs.filter(live=True).annotate(
        views_total=Count('page_views')
    ).order_by('-views_total')[:5])

    # Top Referral sources
    top_referrals = list(views_qs.values('referrer_domain').annotate(
        count=Count('id')
    ).order_by('-count')[:5])

    # Device breakdown
    top_devices = list(views_qs.values('device_type').annotate(
        count=Count('id')
    ).order_by('-count')[:4])

    # Top Browsers
    top_browsers = list(views_qs.values('browser').annotate(
        count=Count('id')
    ).order_by('-count')[:4])

    # 3. Writers / Authors data calculation (for Company Admin view)
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

        writers_data.sort(key=lambda x: x['total_posts'], reverse=True)

    employee_blogs = dashboard_blogs_qs.select_related('category', 'featured_image').order_by('-latest_revision_created_at')

    notifications = request.user.notifications.all()[:10]
    unread_notifications_count = request.user.notifications.filter(is_read=False).count()

    context.update({
        'page': dashboard_page,
        'sidebar_links': sidebar_links,
        'user': request.user,
        'company': company,
        'is_employee': is_employee,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'total_blogs_count': total_blogs_count,
        'today_blogs_count': today_blogs_count,
        'published_blogs_count': published_blogs_count,
        'unpublished_blogs_count': unpublished_blogs_count,
        'total_views_count': total_views_count,
        'unique_visitors_count': unique_visitors_count,
        'today_views_count': today_views_count,
        'chart_labels': chart_labels,
        'chart_views': chart_views,
        'popular_blogs': popular_blogs,
        'top_referrals': top_referrals,
        'top_devices': top_devices,
        'top_browsers': top_browsers,
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

    from Apps.accounts.models import User as UserModel
    if request.user.role == UserModel.Role.COMPANY_USER:
        from django.contrib import messages
        messages.error(request, "Access restricted. Settings are for Company Admins only.")
        return redirect('/dashboard/')

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

        elif action_type == 'update_comments_setting':
            from Apps.companies.models import UserProfile
            from Apps.accounts.models import User as UserModel2
            if request.user.role not in [UserModel2.Role.SUPER_ADMIN, UserModel2.Role.COMPANY_ADMIN]:
                messages.error(request, "Only Company Admins can change comment settings.")
                return redirect(request.path)
            profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
            company = profile.company if profile else None
            if not company:
                messages.error(request, "No company linked to your account.")
                return redirect(request.path)

            # 1. General
            company.allow_comments = request.POST.get('allow_comments') == 'on'
            company.comments_allow_replies = request.POST.get('comments_allow_replies') == 'on'
            try:
                company.comments_per_page = max(1, int(request.POST.get('comments_per_page', 10)))
            except (ValueError, TypeError):
                company.comments_per_page = 10

            # 2. Moderation
            company.comments_require_moderation = request.POST.get('comments_require_moderation') == 'on'
            under_review_msg = request.POST.get('comments_under_review_message', '').strip()
            if under_review_msg:
                company.comments_under_review_message = under_review_msg

            # 3. Form Fields
            company.comments_name_field_required = request.POST.get('comments_name_field_required') == 'on'
            if 'comments_email_field_required' in request.POST:
                company.comments_email_field_mode = 'required' if request.POST.get('comments_email_field_required') == 'on' else 'optional'
            else:
                email_mode = request.POST.get('comments_email_field_mode')
                if email_mode in ['required', 'optional', 'hidden']:
                    company.comments_email_field_mode = email_mode
                else:
                    company.comments_email_field_mode = 'optional'

            company.save()
            messages.success(request, "Comments settings saved successfully!")
            return redirect(request.path)

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


def set_password_confirm_view(request, uidb64, token):
    from django.contrib import messages
    from django.contrib.auth import login as auth_login
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from Apps.accounts.models import User as UserModel, LoginPage

    login_page = LoginPage.objects.live().first()
    login_url = login_page.url if login_page else '/login/'

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        target_user = UserModel.objects.filter(pk=uid).first()
    except (TypeError, ValueError, OverflowError):
        target_user = None

    if not target_user or not default_token_generator.check_token(target_user, token):
        messages.error(request, "This invitation / password reset link has expired or is invalid. Please request a new one.")
        return redirect(login_url)

    company_name = getattr(target_user, 'company_name', 'InsightCMS')
    is_invite = not target_user.has_usable_password()

    if request.method == 'POST':
        new_pass = request.POST.get('new_password', '').strip()
        confirm_pass = request.POST.get('confirm_password', '').strip()

        if not new_pass or len(new_pass) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        elif new_pass != confirm_pass:
            messages.error(request, "Passwords do not match. Please re-enter.")
        else:
            target_user.set_password(new_pass)
            target_user.is_active = True
            target_user.is_approved = True
            target_user.save()

            # Automatically log the user in
            auth_login(request, target_user)
            messages.success(request, f"Welcome to {company_name}! Your password has been set successfully.")
            return redirect('/dashboard/')

    return render(request, 'accounts/set_password.html', {
        'target_user': target_user,
        'company_name': company_name,
        'is_invite': is_invite,
        'login_url': login_url,
    })


def forgot_password_view(request):
    from django.contrib import messages
    from django.contrib.auth.tokens import default_token_generator
    from django.core.mail import send_mail
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from Apps.accounts.models import LoginPage, User as UserModel

    login_page = LoginPage.objects.live().first()
    login_url = login_page.url if login_page else '/login/'

    submitted = False
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user_obj = UserModel.objects.filter(email=email).first()
        if user_obj:
            token = default_token_generator.make_token(user_obj)
            uidb64 = urlsafe_base64_encode(force_bytes(user_obj.pk))
            reset_url = request.build_absolute_uri(f"/set-password/{uidb64}/{token}/")

            try:
                send_mail(
                    subject="Reset Your Password - InsightCMS",
                    message=(
                        f"Hello {user_obj.get_full_name() or user_obj.email},\n\n"
                        f"You requested to reset your password.\n"
                        f"Click the link below to set a new password:\n{reset_url}\n\n"
                        f"If you did not request this, please ignore this email.\n"
                    ),
                    from_email="noreply@insightcms.com",
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.success(request, f"If an account exists with {email}, a password reset link has been sent.")
        submitted = True

    return render(request, 'accounts/forgot_password.html', {
        'login_url': login_url,
        'submitted': submitted
    })


def user_profile_view(request):
    if not request.user.is_authenticated:
        return redirect(get_login_url())

    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    from Apps.companies.models import UserProfile
    from Apps.accounts.models import UserDashboardPage

    dashboard_page = UserDashboardPage.objects.live().first()
    context = dashboard_page.get_context(request) if dashboard_page else {}
    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []

    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else None

    if request.method == 'POST':
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
            return redirect('/my-profile/#security')

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
            return redirect('/my-profile/')

    notifications = request.user.notifications.all()[:10]
    unread_notifications_count = request.user.notifications.filter(is_read=False).count()

    from Apps.accounts.models import SettingsPage
    settings_page = SettingsPage.objects.live().first()

    context.update({
        'page': dashboard_page,
        'settings_page': settings_page,
        'sidebar_links': sidebar_links,
        'user': request.user,
        'company': company,
        'is_employee': (request.user.role == request.user.Role.COMPANY_USER),
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'active_tab': 'my_profile',
    })
    return render(request, 'accounts/my_profile.html', context)


def blog_comments_settings_view(request):
    """
    Settings > Blog Settings > Comments Settings page
    Controls General, Moderation, and Form Fields for comments.
    """
    if not request.user.is_authenticated:
        return redirect(get_login_url())

    from Apps.accounts.models import User as UserModel
    if request.user.role == UserModel.Role.COMPANY_USER:
        from django.contrib import messages
        messages.error(request, "Access restricted. Settings are for Company Admins only.")
        return redirect('/dashboard/')

    from Apps.accounts.models import SettingsPage
    settings_page = SettingsPage.objects.live().first()
    dashboard_page = UserDashboardPage.objects.live().first()
    page_obj = settings_page if settings_page else dashboard_page
    context = page_obj.get_context(request) if page_obj else {}

    from Apps.companies.models import UserProfile, Company
    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else getattr(request.user, 'company', None)
    if not company and request.user.role == UserModel.Role.SUPER_ADMIN:
        # Priority: own company_name > session (don't let another user's session bleed in)
        if request.user.company_name:
            company = Company.objects.filter(company_name__iexact=request.user.company_name).first()
        if not company:
            active_comp_id = request.session.get('active_company_id')
            if active_comp_id:
                company = Company.objects.filter(id=active_comp_id).first()

    if request.method == 'POST':
        from django.contrib import messages
        if not company:
            messages.error(request, "No company linked to your account.")
            return redirect(request.path)

        # 1. General
        company.allow_comments = request.POST.get('allow_comments') == 'on'
        company.comments_allow_replies = request.POST.get('comments_allow_replies') == 'on'
        try:
            company.comments_per_page = max(1, int(request.POST.get('comments_per_page', 10)))
        except (ValueError, TypeError):
            company.comments_per_page = 10

        # 2. Moderation
        company.comments_require_moderation = request.POST.get('comments_require_moderation') == 'on'
        under_review_msg = request.POST.get('comments_under_review_message', '').strip()
        if under_review_msg:
            company.comments_under_review_message = under_review_msg

        # 3. Form Fields
        company.comments_name_field_required = request.POST.get('comments_name_field_required') == 'on'
        if 'comments_email_field_required' in request.POST:
            company.comments_email_field_mode = 'required' if request.POST.get('comments_email_field_required') == 'on' else 'optional'
        else:
            email_mode = request.POST.get('comments_email_field_mode')
            if email_mode in ['required', 'optional', 'hidden']:
                company.comments_email_field_mode = email_mode
            else:
                company.comments_email_field_mode = 'optional'

        company.save()
        messages.success(request, "Comments settings saved successfully!")
        return redirect(request.path)

    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []
    notifications = request.user.notifications.all()[:10]
    unread_notifications_count = request.user.notifications.filter(is_read=False).count()

    context.update({
        'page': page_obj,
        'sidebar_links': sidebar_links,
        'user': request.user,
        'company': company,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'active_tab': 'settings',
        'active_subtab': 'comments_settings',
    })
    return render(request, 'accounts/comments_settings.html', context)


def manage_users_settings_view(request):
    """
    Settings > Manage User Settings
    Features: Add user, Remove user, Block/Unblock user, Update Permissions (Manager/Editor).
    """
    if not request.user.is_authenticated:
        return redirect(get_login_url())

    from django.contrib import messages
    from Apps.accounts.models import User as UserModel, SettingsPage
    from Apps.companies.models import UserProfile, CompanyMembership, Company

    if request.user.role == UserModel.Role.COMPANY_USER:
        messages.error(request, "Access restricted. Settings are for Company Admins only.")
        return redirect('/dashboard/')

    settings_page = SettingsPage.objects.live().first()
    dashboard_page = UserDashboardPage.objects.live().first()
    page_obj = settings_page if settings_page else dashboard_page
    context = page_obj.get_context(request) if page_obj else {}

    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else getattr(request.user, 'company', None)
    if not company:
        membership = CompanyMembership.objects.filter(user=request.user).select_related('company').first()
        if membership:
            company = membership.company
    if not company and request.user.role == UserModel.Role.SUPER_ADMIN:
        # Priority: own company_name first (e.g. "BlogPro"), then session fallback
        if request.user.company_name:
            company = Company.objects.filter(company_name__iexact=request.user.company_name).first()
        if not company:
            active_comp_id = request.session.get('active_company_id')
            if active_comp_id:
                company = Company.objects.filter(id=active_comp_id).first()

    # Handle POST actions
    if request.method == 'POST':
        from Apps.companies.models import UserGroup
        action_type = request.POST.get('action_type', '').strip()

        # 1. ADD USER / SEND INVITATION
        if action_type == 'add_user':
            member_email    = request.POST.get('member_email', '').strip().lower()
            member_fname    = request.POST.get('member_first_name', '').strip()
            member_lname    = request.POST.get('member_last_name', '').strip()
            group_id        = request.POST.get('group_id', '').strip()

            if not member_email:
                messages.error(request, "Email address is required to invite a user.")
                return redirect(request.path)

            if UserModel.objects.filter(email=member_email).exists():
                messages.error(request, f"A user with email '{member_email}' already exists.")
                return redirect(request.path)

            # Create user without password (user sets password via email link)
            company_title = company.company_name if company else "InsightCMS"
            new_user = UserModel.objects.create_user(
                email=member_email,
                first_name=member_fname,
                last_name=member_lname,
                company_name=company_title,
                role=UserModel.Role.COMPANY_USER,
                is_staff=True,
                is_active=True,
                is_approved=True,
                is_blocked=False
            )
            new_user.set_unusable_password()
            new_user.save()

            group_obj = UserGroup.objects.filter(id=group_id, company=company).first() if (group_id and company) else None
            if company:
                CompanyMembership.objects.create(
                    user=new_user, company=company,
                    role=CompanyMembership.Role.EDITOR,
                    group=group_obj
                )
                UserProfile.objects.create(user=new_user, company=company)

            # Generate invite token & link
            from django.contrib.auth.tokens import default_token_generator
            from django.core.mail import EmailMessage, get_connection
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes

            token = default_token_generator.make_token(new_user)
            uidb64 = urlsafe_base64_encode(force_bytes(new_user.pk))
            invite_url = request.build_absolute_uri(f"/set-password/{uidb64}/{token}/")

            # Send Invitation Email using Company SMTP if configured, else fallback
            email_sent = False
            email_error = None
            inviter_name = request.user.get_full_name() or request.user.email
            email_subject = f"You're invited to join {company_title} on InsightCMS"
            email_body = (
                f"Hello {new_user.get_full_name() or member_email},\n\n"
                f"{inviter_name} has invited you to join {company_title} as a team member.\n\n"
                f"To activate your account and set your password, please click the link below:\n"
                f"{invite_url}\n\n"
                f"This link is valid for 3 days.\n\n"
                f"Best regards,\n"
                f"{company_title} Team"
            )

            try:
                from Apps.common.email_service import send_company_email
                send_company_email(
                    company=company,
                    recipient_list=[member_email],
                    subject=email_subject,
                    html_message="",
                    text_message=email_body
                )
                email_sent = True
            except Exception as e:
                email_error = str(e)

            group_txt = group_obj.name if group_obj else "No Group"
            if email_sent:
                messages.success(request, f"User created and invitation email sent to '{member_email}' successfully!")
            else:
                messages.warning(request, f"User created, but email could not be sent: {email_error}. Please configure Email Settings in the 'Email Settings' tab.")
            return redirect(request.path)

        # 2. REMOVE USER
        elif action_type == 'remove_user':
            target_user_id = request.POST.get('user_id')
            if str(target_user_id) == str(request.user.id):
                messages.error(request, "You cannot remove your own account.")
                return redirect(request.path)
            target_user = UserModel.objects.filter(pk=target_user_id).first()
            if target_user:
                # Delete company associations first
                CompanyMembership.objects.filter(user=target_user).delete()
                UserProfile.objects.filter(user=target_user).delete()
                user_ident = target_user.get_full_name() or target_user.email
                # Permanently delete the user from Database
                target_user.delete()
                messages.success(request, f"User '{user_ident}' has been permanently deleted from database.")
            else:
                messages.error(request, "User not found.")
            return redirect(request.path)

        # 3. BLOCK / UNBLOCK USER
        elif action_type == 'toggle_block':
            target_user_id = request.POST.get('user_id')
            if str(target_user_id) == str(request.user.id):
                messages.error(request, "You cannot block yourself.")
                return redirect(request.path)
            target_user = UserModel.objects.filter(pk=target_user_id).first()
            if target_user:
                target_user.is_blocked = not target_user.is_blocked
                target_user.is_active  = not target_user.is_blocked
                target_user.save()
                txt = "BLOCKED" if target_user.is_blocked else "UNBLOCKED"
                messages.success(request, f"User '{target_user.get_full_name() or target_user.email}' has been {txt}.")
            else:
                messages.error(request, "User not found.")
            return redirect(request.path)

        # 4. ASSIGN USER TO GROUP
        elif action_type == 'assign_group':
            target_user_id = request.POST.get('user_id')
            group_id = request.POST.get('group_id', '').strip()
            target_user = UserModel.objects.filter(pk=target_user_id).first()
            if target_user:
                group_obj = UserGroup.objects.filter(id=group_id, company=company).first() if group_id else None
                membership = CompanyMembership.objects.filter(user=target_user, company=company).first()
                if membership:
                    membership.group = group_obj
                    membership.save()
                else:
                    CompanyMembership.objects.create(user=target_user, company=company, group=group_obj)
                group_txt = group_obj.name if group_obj else "No Group"
                messages.success(request, f"'{target_user.get_full_name() or target_user.email}' moved to group: {group_txt}.")
            else:
                messages.error(request, "User not found.")
            return redirect(request.path)

        # 5. ADD GROUP
        elif action_type == 'add_group':
            if not company:
                messages.error(request, "No company found to associate with this group.")
                return redirect(request.path)
            group_name = request.POST.get('group_name', '').strip()
            group_desc = request.POST.get('group_description', '').strip()
            if not group_name:
                messages.error(request, "Group name is required.")
                return redirect(request.path)
            if UserGroup.objects.filter(company=company, name__iexact=group_name).exists():
                messages.error(request, f"A group named '{group_name}' already exists.")
                return redirect(request.path)
            UserGroup.objects.create(
                company=company, name=group_name, description=group_desc,
                can_create_posts    = request.POST.get('can_create_posts')    == 'on',
                can_edit_posts      = request.POST.get('can_edit_posts')      == 'on',
                can_publish_posts   = request.POST.get('can_publish_posts')   == 'on',
                can_manage_comments = request.POST.get('can_manage_comments') == 'on',
            )
            messages.success(request, f"Group '{group_name}' created successfully.")
            return redirect(request.path)

        # 6. UPDATE GROUP PERMISSIONS
        elif action_type == 'update_group':
            group_id = request.POST.get('group_id', '').strip()
            group_obj = UserGroup.objects.filter(id=group_id, company=company).first()
            if group_obj:
                group_obj.name        = request.POST.get('group_name', group_obj.name).strip()
                group_obj.description = request.POST.get('group_description', '').strip()
                group_obj.can_create_posts    = request.POST.get('can_create_posts')    == 'on'
                group_obj.can_edit_posts      = request.POST.get('can_edit_posts')      == 'on'
                group_obj.can_publish_posts   = request.POST.get('can_publish_posts')   == 'on'
                group_obj.can_manage_comments = request.POST.get('can_manage_comments') == 'on'
                group_obj.save()
                messages.success(request, f"Group '{group_obj.name}' permissions updated.")
            else:
                messages.error(request, "Group not found.")
            return redirect(request.path)

        # 8. EDIT USER
        elif action_type == 'edit_user':
            target_user_id = request.POST.get('user_id')
            target_user = UserModel.objects.filter(pk=target_user_id).first()
            if not target_user:
                messages.error(request, "User not found.")
                return redirect(request.path)

            first_name = request.POST.get('first_name', '').strip()
            last_name  = request.POST.get('last_name', '').strip()
            email      = request.POST.get('email', '').strip().lower()
            group_id   = request.POST.get('group_id', '').strip()
            role       = request.POST.get('role', '').strip()
            password   = request.POST.get('password', '').strip()

            if email:
                if UserModel.objects.filter(email=email).exclude(pk=target_user.pk).exists():
                    messages.error(request, f"Another user with email '{email}' already exists.")
                    return redirect(request.path)
                target_user.email = email

            target_user.first_name = first_name
            target_user.last_name  = last_name

            if role in [UserModel.Role.COMPANY_ADMIN, UserModel.Role.COMPANY_USER]:
                # Don't let users downgrade the super admin
                if target_user.role != UserModel.Role.SUPER_ADMIN:
                    target_user.role = role

            if password:
                if len(password) < 6:
                    messages.error(request, "Password must be at least 6 characters long.")
                    return redirect(request.path)
                target_user.set_password(password)

            target_user.save()

            # Update Group
            group_obj = UserGroup.objects.filter(id=group_id, company=company).first() if group_id else None
            membership = CompanyMembership.objects.filter(user=target_user, company=company).first()
            if membership:
                membership.group = group_obj
                membership.save()
            elif company:
                CompanyMembership.objects.create(user=target_user, company=company, group=group_obj)

            messages.success(request, f"User '{target_user.get_full_name() or target_user.email}' details updated successfully!")
            return redirect(request.path)

        # 9. SAVE SMTP / EMAIL SETTINGS
        elif action_type == 'save_smtp_settings':
            if not company:
                messages.error(request, "Company not found.")
                return redirect(request.path)

            company.smtp_host      = request.POST.get('smtp_host', 'smtp.gmail.com').strip()
            company.smtp_port      = int(request.POST.get('smtp_port', 587) or 587)
            company.smtp_use_tls   = (request.POST.get('smtp_use_tls') == 'on')
            company.smtp_user      = request.POST.get('smtp_user', '').strip()
            company.smtp_password  = request.POST.get('smtp_password', '').strip()
            company.smtp_from_name = request.POST.get('smtp_from_name', '').strip()
            company.email_provider = 'manual'
            company.save()

            messages.success(request, f"Manual SMTP updated successfully! Active Sender: {company.smtp_user}")
            return redirect(f"{request.path}?tab=email")

        # 10. TEST SMTP / SEND TEST EMAIL
        elif action_type == 'test_smtp_settings':
            if not company:
                messages.error(request, "Company not found.")
                return redirect(request.path)

            test_to_email = request.POST.get('test_to_email', '').strip() or request.user.email
            if not company.smtp_user or not company.smtp_password:
                messages.error(request, "Please enter and save Sender Email and App Password first before testing.")
                return redirect(f"{request.path}?tab=email")

            try:
                from django.core.mail import EmailMessage, get_connection
                conn = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=company.smtp_host or 'smtp.gmail.com',
                    port=company.smtp_port or 587,
                    username=company.smtp_user,
                    password=company.smtp_password,
                    use_tls=company.smtp_use_tls,
                    fail_silently=False,
                )
                from_addr = f"{company.smtp_from_name or company.company_name} <{company.smtp_user}>"
                test_msg = EmailMessage(
                    subject=f"Test Email from {company.company_name} - InsightCMS",
                    body=f"Hello!\n\nThis is a test email sent from your InsightCMS Email Settings for {company.company_name}.\nYour SMTP configuration is working properly!\n\nBest regards,\nInsightCMS Team",
                    from_email=from_addr,
                    to=[test_to_email],
                    connection=conn,
                )
                test_msg.send(fail_silently=False)
                messages.success(request, f"Test email sent successfully to '{test_to_email}'! Your SMTP settings are working.")
            except Exception as e:
                messages.error(request, f"Failed to send test email: {str(e)}")

            return redirect(f"{request.path}?tab=email")

        # 11. RESET / CLEAR EMAIL SETTINGS
        elif action_type == 'reset_email_settings':
            if company:
                company.email_provider = 'manual'
                company.google_email = ''
                company.google_refresh_token = ''
                company.google_access_token = ''
                company.google_token_expiry = None
                company.smtp_user = ''
                company.smtp_password = ''
                company.smtp_from_name = ''
                company.save()
                messages.success(request, "Email configuration has been cleared. You can now connect a new Google Account or enter new SMTP credentials.")
            else:
                messages.error(request, "Company not found.")
            return redirect(f"{request.path}?tab=email")

    # GET: Fetch data
    from Apps.companies.models import UserGroup
    if company:
        groups = UserGroup.objects.filter(company=company).prefetch_related('members__user')
        memberships = CompanyMembership.objects.filter(company=company).select_related('user', 'group')
        profiles = UserProfile.objects.filter(company=company).select_related('user')
    else:
        groups = UserGroup.objects.none()
        memberships = CompanyMembership.objects.all().select_related('user', 'group')
        profiles = UserProfile.objects.all().select_related('user')
    user_memberships_map = {m.user_id: m for m in memberships}

    # Build team_list
    team_list = []
    seen_ids = set()
    for p in profiles:
        u = p.user
        if u.id in seen_ids:
            continue
        seen_ids.add(u.id)
        mem = user_memberships_map.get(u.id)
        group_obj   = mem.group if mem else None
        group_name  = group_obj.name if group_obj else '—'
        team_list.append({
            'user': u,
            'id': u.id,
            'name': u.get_full_name() or u.admin_username or u.email.split('@')[0],
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
            'role': u.role,
            'group': group_obj,
            'group_name': group_name,
            'is_admin': (u.role in [UserModel.Role.COMPANY_ADMIN, UserModel.Role.SUPER_ADMIN]),
            'is_blocked': getattr(u, 'is_blocked', False),
            'date_joined': u.date_joined,
            'is_self': (u.id == request.user.id),
        })

    # Build group_data (group + its members for display)
    group_data = []
    for grp in groups:
        grp_members = [t for t in team_list if t['group'] and t['group'].id == grp.id]
        group_data.append({
            'group': grp,
            'members': grp_members,
            'permissions': grp.permission_labels(),
        })

    # Ungrouped members
    ungrouped = [t for t in team_list if not t['group'] and not t['is_admin']]
    admin_members = [t for t in team_list if t['is_admin']]

    sidebar_links = dashboard_page.sidebar_links if dashboard_page else []
    notifications = request.user.notifications.all()[:10]
    unread_notifications_count = request.user.notifications.filter(is_read=False).count()

    context.update({
        'page': page_obj,
        'sidebar_links': sidebar_links,
        'user': request.user,
        'company': company,
        'team_list': team_list,
        'group_data': group_data,
        'ungrouped': ungrouped,
        'admin_members': admin_members,
        'groups': groups,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'active_tab': 'settings',
        'active_subtab': 'manage_users',
    })
    return render(request, 'accounts/manage_users.html', context)


# =========================================================================
# Google OAuth 2.0 Integration Views (One-Click Gmail Setup)
# =========================================================================
def google_oauth_connect_view(request):
    """
    Step 1: Initiates Google OAuth 2.0 flow for Gmail API sending.
    Redirects user to Google Consent Screen.
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    from django.conf import settings
    from google_auth_oauthlib.flow import Flow
    import secrets

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '').strip()

    if not client_id or not client_secret:
        messages.error(
            request, 
            "Google OAuth is not configured yet. Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in settings or .env"
        )
        return redirect('/settings/users/?tab=email')

    # Build client config dict
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    redirect_uri = request.build_absolute_uri('/integrations/google/callback/')

    flow = Flow.from_client_config(
        client_config,
        scopes=getattr(settings, 'GOOGLE_OAUTH_SCOPES', ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/userinfo.email', 'openid']),
        redirect_uri=redirect_uri
    )

    state = secrets.token_urlsafe(16)
    request.session['google_oauth_state'] = state

    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state
    )

    # In modern google-auth-oauthlib, PKCE code_verifier is generated on flow and must be preserved for fetch_token
    if hasattr(flow, 'code_verifier') and flow.code_verifier:
        request.session['google_oauth_code_verifier'] = flow.code_verifier

    return redirect(authorization_url)


def google_oauth_callback_view(request):
    """
    Step 2: Handles redirect from Google OAuth consent screen.
    Exchanges code for tokens, extracts user's Gmail, and saves to Company model.
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    from django.conf import settings
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from Apps.companies.models import UserProfile, CompanyMembership, Company

    # Check for error parameter from Google
    if 'error' in request.GET:
        err = request.GET.get('error', 'Google authorization cancelled')
        messages.error(request, f"Google authorization failed: {err}")
        return redirect('/settings/users/?tab=email')

    code = request.GET.get('code')
    state = request.GET.get('state')
    saved_state = request.session.pop('google_oauth_state', None)

    if not code:
        messages.error(request, "Authorization code missing from Google response.")
        return redirect('/settings/users/?tab=email')

    # Fetch active company
    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else getattr(request.user, 'company', None)
    if not company:
        membership = CompanyMembership.objects.filter(user=request.user).select_related('company').first()
        if membership:
            company = membership.company
    if not company and request.user.role == 'super_admin':
        active_comp_id = request.session.get('active_company_id')
        if active_comp_id:
            company = Company.objects.filter(id=active_comp_id).first()

    if not company:
        messages.error(request, "Could not determine company to bind Google Account.")
        return redirect('/settings/users/?tab=email')

    try:
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '').strip()

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        # Use same redirect uri host/port as incoming request
        redirect_uri = request.build_absolute_uri('/integrations/google/callback/')

        flow = Flow.from_client_config(
            client_config,
            scopes=getattr(settings, 'GOOGLE_OAUTH_SCOPES', ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/userinfo.email', 'openid']),
            redirect_uri=redirect_uri,
            state=state
        )

        code_verifier = request.session.pop('google_oauth_code_verifier', None)
        if code_verifier:
            flow.code_verifier = code_verifier

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Fetch connected Google user profile email
        oauth2_service = build('oauth2', 'v2', credentials=credentials)
        user_info = oauth2_service.userinfo().get().execute()
        connected_email = user_info.get('email', '')

        # Save tokens in Company model
        company.email_provider = 'google'
        company.google_email = connected_email
        if credentials.refresh_token:
            company.google_refresh_token = credentials.refresh_token
        if credentials.token:
            company.google_access_token = credentials.token
        if credentials.expiry:
            company.google_token_expiry = credentials.expiry
        company.save()

        messages.success(
            request, 
            f"Successfully connected Google account ({connected_email})! One-click email sending is now active."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error completing Google connection: {str(e)}")

    return redirect('/settings/users/?tab=email')


def google_oauth_disconnect_view(request):
    """
    Step 3: Disconnects Google OAuth for the company and reverts provider to manual.
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    from Apps.companies.models import UserProfile, CompanyMembership, Company

    profile = UserProfile.objects.filter(user=request.user).select_related('company').first()
    company = profile.company if profile else getattr(request.user, 'company', None)
    if not company:
        membership = CompanyMembership.objects.filter(user=request.user).select_related('company').first()
        if membership:
            company = membership.company

    if company:
        old_email = company.google_email
        company.email_provider = 'manual'
        company.google_email = ''
        company.google_refresh_token = ''
        company.google_access_token = ''
        company.google_token_expiry = None
        company.save()
        messages.info(request, f"Google account ({old_email or 'OAuth'}) has been disconnected.")
    else:
        messages.error(request, "Company not found.")

    return redirect('/settings/users/?tab=email')



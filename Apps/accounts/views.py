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
            email_mode = request.POST.get('comments_email_field_mode', 'optional')
            if email_mode in ['required', 'optional', 'hidden']:
                company.comments_email_field_mode = email_mode

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
        active_comp_id = request.session.get('active_company_id')
        if active_comp_id:
            company = Company.objects.filter(id=active_comp_id).first()

    # Note: If Super Admin has no linked company, company remains None so platform defaults (BlogPro) render.

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
        email_mode = request.POST.get('comments_email_field_mode', 'optional')
        if email_mode in ['required', 'optional', 'hidden']:
            company.comments_email_field_mode = email_mode

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
    if not company and request.user.role == UserModel.Role.SUPER_ADMIN:
        active_comp_id = request.session.get('active_company_id')
        if active_comp_id:
            company = Company.objects.filter(id=active_comp_id).first()

    # Note: If Super Admin has no linked company, company remains None so platform defaults (BlogPro) render.

    # Handle POST actions
    if request.method == 'POST':
        from Apps.companies.models import UserGroup
        action_type = request.POST.get('action_type', '').strip()

        # 1. ADD USER (with group)
        if action_type == 'add_user':
            member_email    = request.POST.get('member_email', '').strip().lower()
            member_fname    = request.POST.get('member_first_name', '').strip()
            member_lname    = request.POST.get('member_last_name', '').strip()
            member_password = request.POST.get('member_password', '')
            group_id        = request.POST.get('group_id', '').strip()

            if not member_email or not member_password:
                messages.error(request, "Email and password are required to add a user.")
                return redirect(request.path)

            if UserModel.objects.filter(email=member_email).exists():
                messages.error(request, f"A user with email '{member_email}' already exists.")
                return redirect(request.path)

            new_user = UserModel.objects.create_user(
                email=member_email, password=member_password,
                first_name=member_fname, last_name=member_lname,
                company_name=company.company_name,
                role=UserModel.Role.COMPANY_USER,
                is_staff=True, is_active=True, is_approved=True, is_blocked=False
            )

            group_obj = UserGroup.objects.filter(id=group_id, company=company).first() if group_id else None
            CompanyMembership.objects.create(
                user=new_user, company=company,
                role=CompanyMembership.Role.EDITOR,
                group=group_obj
            )
            UserProfile.objects.create(user=new_user, company=company)

            group_txt = group_obj.name if group_obj else "No Group"
            messages.success(request, f"User '{new_user.get_full_name() or member_email}' added to group: {group_txt}.")
            return redirect(request.path)

        # 2. REMOVE USER
        elif action_type == 'remove_user':
            target_user_id = request.POST.get('user_id')
            if str(target_user_id) == str(request.user.id):
                messages.error(request, "You cannot remove your own account.")
                return redirect(request.path)
            target_user = UserModel.objects.filter(pk=target_user_id).first()
            if target_user:
                CompanyMembership.objects.filter(user=target_user, company=company).delete()
                UserProfile.objects.filter(user=target_user, company=company).delete()
                target_user.is_active = False
                target_user.save()
                messages.success(request, f"User '{target_user.get_full_name() or target_user.email}' removed.")
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

        # 7. DELETE GROUP
        elif action_type == 'delete_group':
            group_id = request.POST.get('group_id', '').strip()
            group_obj = UserGroup.objects.filter(id=group_id, company=company).first()
            if group_obj:
                group_name = group_obj.name
                # Remove group assignment from members, keep users
                group_obj.members.update(group=None)
                group_obj.delete()
                messages.success(request, f"Group '{group_name}' deleted.")
            else:
                messages.error(request, "Group not found.")
            return redirect(request.path)

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
            'email': u.email,
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


from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from Apps.accounts.models import UserDashboardPage


@login_required(login_url='/accounts/login/')
def user_dashboard_view(request):
    dashboard_page = UserDashboardPage.objects.live().first()
    context = dashboard_page.get_context(request) if dashboard_page else {}
    context.update({'page': dashboard_page, 'user': request.user})
    from Apps.blogs.models import BlogPage
    context['recent_blogs'] = BlogPage.objects.all().order_by('-latest_revision_created_at')[:5]
    return render(request, 'accounts/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')

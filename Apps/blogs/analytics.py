import re
from urllib.parse import urlparse
from django.utils import timezone
from datetime import timedelta


def get_client_ip(request):
    """Extract client IP address handling proxies and direct connections."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent):
    """Parse User-Agent string to classify Device Type, Browser, and OS."""
    if not user_agent:
        return 'Desktop', 'Other', 'Other'

    ua = user_agent.lower()

    # 1. Device Type
    if any(k in ua for k in ('ipad', 'tablet', 'kindle', 'silk', 'playbook')):
        device = 'Tablet'
    elif any(k in ua for k in ('mobile', 'android', 'iphone', 'ipod', 'blackberry', 'windows phone')):
        device = 'Mobile'
    else:
        device = 'Desktop'

    # 2. Browser
    if 'edg' in ua:
        browser = 'Edge'
    elif 'opr' in ua or 'opera' in ua:
        browser = 'Opera'
    elif 'chrome' in ua and 'chromium' not in ua:
        browser = 'Chrome'
    elif 'safari' in ua and 'chrome' not in ua:
        browser = 'Safari'
    elif 'firefox' in ua:
        browser = 'Firefox'
    else:
        browser = 'Other'

    # 3. Operating System
    if 'windows' in ua:
        os = 'Windows'
    elif 'android' in ua:
        os = 'Android'
    elif any(k in ua for k in ('iphone', 'ipad', 'ios')):
        os = 'iOS'
    elif 'macintosh' in ua or 'mac os' in ua:
        os = 'macOS'
    elif 'linux' in ua:
        os = 'Linux'
    else:
        os = 'Other'

    return device, browser, os


def parse_referrer(referrer_url, site_host=None):
    """Categorize referring traffic source (Direct, Search, Social, or Domain)."""
    if not referrer_url:
        return 'Direct'

    try:
        parsed = urlparse(referrer_url)
        domain = parsed.netloc.lower()

        if not domain:
            return 'Direct'

        # Internal referral check
        if site_host and site_host.lower() in domain:
            return 'Internal'

        # Search Engines
        if 'google.' in domain:
            return 'Google Search'
        if 'bing.com' in domain:
            return 'Bing'
        if 'yahoo.com' in domain:
            return 'Yahoo'
        if 'duckduckgo.com' in domain:
            return 'DuckDuckGo'
        if 'baidu.com' in domain:
            return 'Baidu'
        if 'yandex.' in domain:
            return 'Yandex'

        # Social Media
        if any(k in domain for k in ('t.co', 'twitter.com', 'x.com')):
            return 'Twitter / X'
        if any(k in domain for k in ('facebook.com', 'fb.com', 'fb.me')):
            return 'Facebook'
        if 'instagram.com' in domain:
            return 'Instagram'
        if 'linkedin.com' in domain:
            return 'LinkedIn'
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'YouTube'
        if 'reddit.com' in domain:
            return 'Reddit'
        if 'pinterest.' in domain:
            return 'Pinterest'
        if 'whatsapp' in domain:
            return 'WhatsApp'
        if 'threads.net' in domain:
            return 'Threads'

        # External Website
        clean_domain = domain.replace('www.', '')
        return clean_domain if clean_domain else 'External'
    except Exception:
        return 'Direct'


def track_blog_view(request, blog_page):
    """Logs a blog view in BlogPostView with 15-minute debounce."""
    try:
        from Apps.blogs.models import BlogPostView

        # Ensure session exists for unique visitor counting
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key or 'anonymous'

        # Avoid duplicate counting within 15 minutes for the exact same session & blog
        fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
        recent_view = BlogPostView.objects.filter(
            blog=blog_page,
            session_key=session_key,
            created_at__gte=fifteen_minutes_ago
        ).exists()

        if recent_view:
            return None

        ip = get_client_ip(request)
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        device, browser, os = parse_user_agent(ua_string)

        raw_referrer = request.META.get('HTTP_REFERER', '')
        referrer_domain = parse_referrer(raw_referrer, request.get_host())

        view_obj = BlogPostView.objects.create(
            blog=blog_page,
            company=blog_page.company,
            session_key=session_key,
            ip_address=ip if ip and len(ip) <= 45 else None,
            referrer=raw_referrer[:500] if raw_referrer else '',
            referrer_domain=referrer_domain[:150],
            device_type=device,
            browser=browser,
            os=os,
        )
        return view_obj
    except Exception:
        # Never break visitor page render due to logging
        return None

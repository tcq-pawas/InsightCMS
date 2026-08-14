from wagtail import hooks


@hooks.register('construct_page_listing_buttons')
def add_blog_page_listing_buttons(buttons, page, page_perms=None, is_parent=False, context=None, *args, **kwargs):
    """Add custom buttons to blog page listing."""
    pass


@hooks.register('construct_homepage_panels')
def add_homepage_panels(request, panels):
    """Customize homepage panels."""
    pass

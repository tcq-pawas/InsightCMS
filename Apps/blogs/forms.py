"""
Apps/blogs/forms.py

Implements Section 7, point 3: "the logged-in user is suggested as
author" when an editor creates a new blog post.

Attach this as `base_form_class` on BlogPage. Wagtail passes the
logged-in user into the form as `for_user`, so we use that to
pre-fill the `author` field ONLY when creating a brand new post (an
existing post's author should never be silently overwritten on edit).
"""
from wagtail.admin.forms import WagtailAdminPageForm


class BlogPageForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user = getattr(self, "for_user", None)
        if user is None or "author" not in self.fields:
            return

        # Only pre-fill on a brand-new, unsaved post. If editing an
        # existing post, leave whatever author is already set alone.
        is_new_page = self.instance.pk is None
        if is_new_page and not self.initial.get("author"):
            self.fields["author"].initial = user.pk
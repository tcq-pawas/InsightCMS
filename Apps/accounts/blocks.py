from wagtail import blocks


class SidebarChildLinkBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=50, default="Comments Settings", help_text="Sub-link name (e.g. Comments Settings, Manage User Settings)")
    url = blocks.CharBlock(required=True, max_length=255, default="/settings/blog/comments/", help_text="URL path (e.g. /settings/blog/comments/)")
    icon = blocks.ChoiceBlock(
        choices=[
            ('fa-regular fa-comments', 'Comments (Outline)'),
            ('fa-solid fa-comments', 'Comments (Solid)'),
            ('fa-solid fa-folder-open', 'Folder Open'),
            ('fa-solid fa-newspaper', 'Newspaper / Blog'),
            ('fa-solid fa-users-gear', 'Users / Team Settings'),
            ('fa-solid fa-sliders', 'Sliders / Controls'),
            ('fa-solid fa-gear', 'Gear / Settings'),
            ('fa-solid fa-shield-halved', 'Security / Shield'),
            ('fa-solid fa-file-lines', 'File / Pages'),
            ('fa-solid fa-magnifying-glass-chart', 'SEO / Search & Growth'),
            ('fa-solid fa-link', 'Link / Generic'),
        ],
        default='fa-regular fa-comments',
        help_text="Choose FontAwesome Icon"
    )
    badge_text = blocks.CharBlock(required=False, max_length=10, help_text="Optional badge")
    admin_only = blocks.BooleanBlock(required=False, default=False, help_text="Only show to Company Admins. Hide from regular employees.")
    hide_from_superadmin = blocks.BooleanBlock(required=False, default=False, help_text="Hide this sublink from Super Admin")

    class Meta:
        icon = "link"
        label = "Sub Link Item"


class SidebarSubmenuBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=50, default="Blog Settings", help_text="Submenu Group Name (e.g. Blog Settings)")
    icon = blocks.ChoiceBlock(
        choices=[
            ('fa-solid fa-folder-open', 'Folder Open'),
            ('fa-solid fa-newspaper', 'Newspaper / Blog'),
            ('fa-solid fa-gear', 'Gear / Settings'),
            ('fa-solid fa-sliders', 'Sliders'),
            ('fa-solid fa-layer-group', 'Layer Group'),
        ],
        default='fa-solid fa-folder-open',
        help_text="Submenu Icon"
    )
    admin_only = blocks.BooleanBlock(required=False, default=False, help_text="Only show this group to Company Admins. Hide from regular employees.")
    hide_from_superadmin = blocks.BooleanBlock(required=False, default=False, help_text="Hide this group from Super Admin")
    nested_links = blocks.ListBlock(SidebarChildLinkBlock(), label="Nested Links (e.g. Comments Settings)", required=False)

    class Meta:
        icon = "folder-open-inverse"
        label = "Submenu Group (Level 1)"


# 1. Single Sidebar Link Block (Menu Item)
class SidebarLinkBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=50, default="Settings", help_text="Link name (e.g. Dashboard, Posts, Settings)")
    url = blocks.CharBlock(required=False, max_length=255, default="/dashboard/", help_text="URL path (Leave # or empty if using submenus)")
    icon = blocks.ChoiceBlock(
        choices=[
            ('fa-solid fa-table-cells-large', 'Dashboard / Grid'),
            ('fa-solid fa-pen-nib', 'Pen / Posts'),
            ('fa-solid fa-layer-group', 'Layer / Categories'),
            ('fa-solid fa-image', 'Image / Media'),
            ('fa-solid fa-file-lines', 'File / Pages'),
            ('fa-regular fa-comments', 'Comments (Outline)'),
            ('fa-solid fa-comments', 'Comments (Solid)'),
            ('fa-solid fa-chart-line', 'Chart / Analytics'),
            ('fa-solid fa-user', 'User / Subscribers'),
            ('fa-solid fa-user-gear', 'User / Profile Settings'),
            ('fa-solid fa-wand-magic-sparkles', 'Magic / Appearance'),
            ('fa-solid fa-puzzle-piece', 'Puzzle / Plugins'),
            ('fa-solid fa-gear', 'Gear / Settings'),
            ('fa-solid fa-users-gear', 'Manage Users'),
            ('fa-solid fa-code', 'Code / Integration'),
            ('fa-solid fa-magnifying-glass-chart', 'SEO / Search & Growth'),
        ],
        default='fa-solid fa-gear',
        help_text="Choose FontAwesome Icon"
    )
    badge_text = blocks.CharBlock(required=False, max_length=10, help_text="Optional badge text (e.g. 24 or New)")
    is_active = blocks.BooleanBlock(required=False, default=False, help_text="Highlight as active/selected item")
    admin_only = blocks.BooleanBlock(required=False, default=False, help_text="Check this if this link is only for Admins and should be hidden from Employees")
    hide_from_superadmin = blocks.BooleanBlock(required=False, default=False, help_text="Hide this navigation link from Super Admin")
    
    # Nested dynamic submenus and direct sublinks
    submenus = blocks.ListBlock(SidebarSubmenuBlock(), label="Submenu Groups (e.g. Blog Settings)", required=False)
    direct_sublinks = blocks.ListBlock(SidebarChildLinkBlock(), label="Direct Sublinks (e.g. Manage User Settings)", required=False)

    class Meta:
        icon = "link"
        label = "Sidebar Navigation Item"


# =========================================================================
# 5 MODULAR BODY BLOCKS (Jo (+) dabane par popup me dikhenge)
# =========================================================================

# Block 1: Stat Card Item + Row Block
class StatCardBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=50, default="Total Blogs", help_text="e.g. Total Blogs, Today's Blog, Published Blogs, Unpublished Blogs")
    value = blocks.CharBlock(required=False, max_length=50, default="", help_text="Optional. Leave blank to auto-calculate live from database.")
    growth = blocks.CharBlock(required=False, max_length=50, default="12.5%", help_text="e.g. 12.5%")
    icon_theme = blocks.ChoiceBlock(
        choices=[
            ('icon-blue', 'Blue (Posts)'),
            ('icon-cyan', 'Cyan (Views)'),
            ('icon-pink', 'Pink (Comments)'),
            ('icon-purple', 'Purple (Subscribers)'),
            ('icon-orange', 'Orange (Published)'),
        ],
        default='icon-blue'
    )

    class Meta:
        icon = "doc-full"
        label = "Stat Card Item"


class StatsRowBlock(blocks.StructBlock):
    stat_cards = blocks.ListBlock(StatCardBlock(), label="Stat Cards")
    caption = blocks.CharBlock(required=False, default="vs last month", help_text="Bottom caption")

    class Meta:
        icon = "table"
        label = "Stat Cards Row"
        template = "accounts/blocks/stats_row.html"


# Block 3: Recent Posts Table Block
class RecentPostsTableBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, default="Recent Posts")
    subtext = blocks.CharBlock(required=False, default="Manage your latest published and draft articles")
    view_all_text = blocks.CharBlock(required=False, default="View All ›")
    view_all_url = blocks.CharBlock(required=False, default="/cms/pages/")

    th_name = blocks.CharBlock(required=False, default="NAME")
    th_email = blocks.CharBlock(required=False, default="EMAIL")
    th_published = blocks.CharBlock(required=False, default="PUBLISHED")
    th_posts = blocks.CharBlock(required=False, default="TOTAL POSTS")
    th_unpublished = blocks.CharBlock(required=False, default="UNPUBLISHED")

    class Meta:
        icon = "list-ul"
        label = "Recent Posts Table"
        template = "accounts/blocks/recent_post_table.html"


# Block 4: Clean Stats-based Audience Overview Block (8 Compact Stats)
class AudienceOverviewBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, default="Audience Overview")
    subtext = blocks.CharBlock(required=False, default="Where your readers come from and how they browse")

    # Stat 1: Top Country
    stat1_label = blocks.CharBlock(required=False, default="Top Country")
    stat1_value = blocks.CharBlock(required=False, default="India")
    stat1_sub = blocks.CharBlock(required=False, default="32% of total visitors")

    # Stat 2: Total Visitors
    stat2_label = blocks.CharBlock(required=False, default="Total Visitors")
    stat2_value = blocks.CharBlock(required=False, default="12.4K")
    stat2_sub = blocks.CharBlock(required=False, default="18% vs last month")

    # Stat 3: New Visitors
    stat3_label = blocks.CharBlock(required=False, default="New Visitors")
    stat3_value = blocks.CharBlock(required=False, default="7.7K")
    stat3_sub = blocks.CharBlock(required=False, default="62% of total visitors")

    # Stat 4: Returning Visitors
    stat4_label = blocks.CharBlock(required=False, default="Returning Visitors")
    stat4_value = blocks.CharBlock(required=False, default="4.7K")
    stat4_sub = blocks.CharBlock(required=False, default="38% of total visitors")

    # Stat 5: Top Traffic Source
    stat5_label = blocks.CharBlock(required=False, default="Top Traffic Source")
    stat5_value = blocks.CharBlock(required=False, default="Organic Search")
    stat5_sub = blocks.CharBlock(required=False, default="46% of total traffic")

    # Stat 6: Top Device
    stat6_label = blocks.CharBlock(required=False, default="Top Device")
    stat6_value = blocks.CharBlock(required=False, default="Mobile")
    stat6_sub = blocks.CharBlock(required=False, default="60% of total visitors")

    # Stat 7: Avg. Time on Site
    stat7_label = blocks.CharBlock(required=False, default="Avg. Time on Site")
    stat7_value = blocks.CharBlock(required=False, default="3m 42s")
    stat7_sub = blocks.CharBlock(required=False, default="10% vs last month")

    # Stat 8: Avg. Pages / Visit
    stat8_label = blocks.CharBlock(required=False, default="Avg. Pages / Visit")
    stat8_value = blocks.CharBlock(required=False, default="2.8")
    stat8_sub = blocks.CharBlock(required=False, default="7% vs last month")

    class Meta:
        icon = "group"
        label = "Audience Overview"
        template = "accounts/blocks/audience_overview.html"


# Block 5: Single Comment + Recent Comments Block
class SingleCommentBlock(blocks.StructBlock):
    author = blocks.CharBlock(required=True, default="Alex Johnson")
    time = blocks.CharBlock(required=False, default="10m ago")
    text = blocks.TextBlock(required=True, default="Great insights on Wagtail StreamFields!")
    post_title = blocks.CharBlock(required=False, default="Getting Started with Wagtail CMS")


class RecentCommentsBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, default="Recent Comments")
    subtext = blocks.CharBlock(required=False, default="Latest reader interactions")
    view_all_text = blocks.CharBlock(required=False, default="View All ›")
    view_all_url = blocks.CharBlock(required=False, default="/cms/")
    comments = blocks.ListBlock(SingleCommentBlock(), label="Comments List")

    class Meta:
        icon = "comment"
        label = "Recent Comments"
        template = "accounts/blocks/recent_comments.html"


# Block 6: Upgrade Banner Block
class UpgradeBannerBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, default="Ready to take your blog to the next level?")
    text = blocks.CharBlock(required=False, default="Upgrade to BlogPro Pro and unlock powerful features.")
    button_text = blocks.CharBlock(required=False, default="Upgrade Now")
    button_url = blocks.CharBlock(required=False, default="#")

    class Meta:
        icon = "gem"
        label = "Upgrade Banner"
        template = "accounts/blocks/upgrade_banner.html"


# Block 0: Header & Brand Block
class HeaderBrandBlock(blocks.StructBlock):
    brand_name = blocks.CharBlock(required=False, default="ShivangiCMS")
    welcome_heading = blocks.CharBlock(required=False, default="Hello Shivangi!")
    welcome_subtext = blocks.CharBlock(required=False, default="Manage your assigned blogs, workspace, and publish content seamlessly.")
    new_post_button_text = blocks.CharBlock(required=False, default="+ New Post")
    new_post_button_url = blocks.CharBlock(required=False, default="/cms/pages/")

    class Meta:
        icon = "title"
        label = "Header & Brand"
        template = "accounts/blocks/header_brand.html"


# Block: Sidebar Block
class SidebarBlock(blocks.StructBlock):
    brand_name = blocks.CharBlock(required=False, default="BlogPro")
    sidebar_links = blocks.ListBlock(SidebarLinkBlock(), label="Sidebar Links")

    class Meta:
        icon = "list-ul"
        label = "Sidebar Menu"
        template = "accounts/blocks/sidebar.html"


# Block: Topbar Block
class TopbarBlock(blocks.StructBlock):
    search_placeholder = blocks.CharBlock(required=False, default="Search anything...")

    class Meta:
        icon = "pick"
        label = "Topbar Search Bar"
        template = "accounts/blocks/topbar.html"


# Block: Footer Block
class FooterBlock(blocks.StructBlock):
    tagline = blocks.TextBlock(required=False, default="The all-in-one blogging platform that helps you create, manage, and grow your blog.")
    copyright_text = blocks.CharBlock(required=False, default="© 2024 BlogPro. All rights reserved.")

    class Meta:
        icon = "site"
        label = "Footer Section"
        template = "accounts/blocks/footer.html"


# =========================================================================
# CONFIG BLOCKS (Sections 3, 3.1, 4, 5 — appear in (+) menu with 🗑️ icon)
# =========================================================================

# Section 3: Recent Posts Table Configuration (Admin View)
class RecentPostsConfigBlock(blocks.StructBlock):
    heading           = blocks.CharBlock(required=False, default="Recent Posts")
    subtext           = blocks.CharBlock(required=False, default="Manage your latest published and draft articles")
    th_name    = blocks.CharBlock(required=False, default="NAME")
    th_email      = blocks.CharBlock(required=False, default="EMAIL")
    th_published       = blocks.CharBlock(required=False, default="PUBLISHED")
    th_posts         = blocks.CharBlock(required=False, default="TOTAL POSTS")
    th_unpublished           = blocks.CharBlock(required=False, default="UNPUBLISHED")
    empty_posts_text       = blocks.CharBlock(required=False, default="No blog posts yet.")
    empty_create_btn_text  = blocks.CharBlock(required=False, default="Create Your First Post")

    class Meta:
        icon = "list-ul"
        label = "Recent Posts Table Config (Admin View)"
        template = "accounts/blocks/recent_posts_config.html"


# Section 3.1: Employee Blogs Table Configuration (Employee View)
class EmployeeBlogsConfigBlock(blocks.StructBlock):
    emp_blogs_heading         = blocks.CharBlock(required=False, default="My Blog Posts")
    emp_blogs_subtext         = blocks.CharBlock(required=False, default="Write, manage, and track your submitted articles")
    emp_write_blog_btn_text   = blocks.CharBlock(required=False, default="+ Write New Blog")
    emp_write_blog_btn_url    = blocks.CharBlock(required=False, default="/blog-posts/create/")
    emp_th_blog_title         = blocks.CharBlock(required=False, default="BLOG TITLE")
    emp_th_description        = blocks.CharBlock(required=False, default="DESCRIPTION")
    emp_th_status             = blocks.CharBlock(required=False, default="STATUS")
    emp_status_rejected       = blocks.CharBlock(required=False, default="Rejected")
    emp_status_approved       = blocks.CharBlock(required=False, default="Approved")
    emp_status_pending        = blocks.CharBlock(required=False, default="Pending")
    emp_no_description_text   = blocks.CharBlock(required=False, default="No description")
    emp_empty_blogs_text      = blocks.CharBlock(required=False, default="No blogs yet. Start writing!")
    emp_empty_create_btn_text = blocks.CharBlock(required=False, default="Write Your First Blog")

    class Meta:
        icon = "edit"
        label = "Employee Blogs Table Config (Employee View)"
        template = "accounts/blocks/employee_blogs_config.html"


# Section 4: Comments Moderation Page Configuration
class CommentsModerationConfigBlock(blocks.StructBlock):
    comments_page_title         = blocks.CharBlock(required=False, default="Comments Moderation")
    comments_page_subtext       = blocks.CharBlock(required=False, default="Moderate visitor comments on your blog posts across")
    filter_blog_label           = blocks.CharBlock(required=False, default="Blog:")
    card_total_comments_label   = blocks.CharBlock(required=False, default="Total Comments")
    card_pending_review_label   = blocks.CharBlock(required=False, default="Pending Review")
    card_approved_label         = blocks.CharBlock(required=False, default="Approved")
    card_rejected_label         = blocks.CharBlock(required=False, default="Rejected")
    tab_all_label               = blocks.CharBlock(required=False, default="All")
    tab_pending_label           = blocks.CharBlock(required=False, default="Pending")
    tab_approved_label          = blocks.CharBlock(required=False, default="Approved")
    tab_rejected_label          = blocks.CharBlock(required=False, default="Rejected")
    comments_page_empty_heading = blocks.CharBlock(required=False, default="No Comments Yet")
    comments_page_empty_subtext = blocks.CharBlock(required=False, default="When readers comment on your posts, they'll appear here.")
    comments_th_author          = blocks.CharBlock(required=False, default="AUTHOR")
    comments_th_comment         = blocks.CharBlock(required=False, default="COMMENT")
    comments_th_post            = blocks.CharBlock(required=False, default="POST")
    comments_th_date            = blocks.CharBlock(required=False, default="DATE")
    comments_th_status          = blocks.CharBlock(required=False, default="STATUS")
    comments_th_actions         = blocks.CharBlock(required=False, default="ACTIONS")
    bulk_delete_btn             = blocks.CharBlock(required=False, default="Delete Selected")
    bulk_reject_btn             = blocks.CharBlock(required=False, default="Reject Selected")
    bulk_approve_btn            = blocks.CharBlock(required=False, default="Approve Selected")
    action_reply_btn            = blocks.CharBlock(required=False, default="Reply")
    action_approve_btn          = blocks.CharBlock(required=False, default="Approve")
    action_reject_btn           = blocks.CharBlock(required=False, default="Reject")
    status_badge_pending        = blocks.CharBlock(required=False, default="Pending")
    status_badge_approved       = blocks.CharBlock(required=False, default="Approved")
    status_badge_rejected       = blocks.CharBlock(required=False, default="Rejected")
    team_badge_text             = blocks.CharBlock(required=False, default="Team")
    reply_modal_their_comment_label = blocks.CharBlock(required=False, default="Their comment:")
    reply_modal_your_reply_label    = blocks.CharBlock(required=False, default="Your Reply")
    reply_modal_placeholder         = blocks.CharBlock(required=False, default="Write your reply...")
    reply_modal_cancel_btn          = blocks.CharBlock(required=False, default="Cancel")
    reply_modal_send_btn            = blocks.CharBlock(required=False, default="Send Reply")
    delete_modal_title              = blocks.CharBlock(required=False, default="Delete Comment?")
    delete_modal_cancel_btn         = blocks.CharBlock(required=False, default="Cancel")
    delete_modal_confirm_btn        = blocks.CharBlock(required=False, default="Delete")
    all_blog_posts_option           = blocks.CharBlock(required=False, default="All Blog Posts")
    empty_approved_text             = blocks.CharBlock(required=False, default="No approved comments yet.")
    empty_spam_text                 = blocks.CharBlock(required=False, default="No spam comments. 🎉")
    blog_selector_label             = blocks.CharBlock(required=False, default="Blog:")
    comment_subtext_prefix          = blocks.CharBlock(required=False, default="Moderate visitor comments on your blog posts across")

    class Meta:
        icon = "comment"
        label = "Comments Moderation Config"
        template = "accounts/blocks/comments_moderation_config.html"


# Section 5: Footer Settings & Social Links Configuration
class FooterSettingsConfigBlock(blocks.StructBlock):
    footer_tagline         = blocks.TextBlock(required=False, default="The all-in-one blogging platform that helps you create, manage, and grow your blog.")
    footer_facebook_url    = blocks.CharBlock(required=False, default="#")
    footer_twitter_url     = blocks.CharBlock(required=False, default="#")
    footer_instagram_url   = blocks.CharBlock(required=False, default="#")
    footer_linkedin_url    = blocks.CharBlock(required=False, default="#")
    footer_col1_heading    = blocks.CharBlock(required=False, default="PRODUCT")
    footer_col1_link1_text = blocks.CharBlock(required=False, default="Features")
    footer_col1_link1_url  = blocks.CharBlock(required=False, default="#")
    footer_col1_link2_text = blocks.CharBlock(required=False, default="Pricing")
    footer_col1_link2_url  = blocks.CharBlock(required=False, default="#")
    footer_col2_heading    = blocks.CharBlock(required=False, default="SUPPORT")
    footer_col2_link1_text = blocks.CharBlock(required=False, default="Help Center")
    footer_col2_link1_url  = blocks.CharBlock(required=False, default="#")
    footer_col2_link2_text = blocks.CharBlock(required=False, default="Documentation")
    footer_col2_link2_url  = blocks.CharBlock(required=False, default="#")
    copyright_text         = blocks.CharBlock(required=False, default="© 2024 BlogPro. All rights reserved.")

    class Meta:
        icon = "site"
        label = "Footer Settings & Social Links"
        template = "accounts/blocks/footer_settings_config.html"


# =========================================================================
# MASTER DASHBOARD STREAMBLOCK (Only Content Body Blocks)
# =========================================================================
class DashboardBodyStreamBlock(blocks.StreamBlock):
    header_brand        = HeaderBrandBlock(icon="title",    label="Header & Action Button")
    stats_row           = StatsRowBlock(icon="table",       label="Stat Cards Row")
    recent_posts        = RecentPostsTableBlock(icon="list-ul", label="Recent Posts Table")
    audience_overview   = AudienceOverviewBlock(icon="group",   label="Audience Overview")
    recent_comments     = RecentCommentsBlock(icon="comment",   label="Recent Comments")
    upgrade_banner      = UpgradeBannerBlock(icon="gem",        label="Upgrade Banner")
    recent_posts_config = RecentPostsConfigBlock(icon="list-ul", label="Recent Posts Table Config (Admin)")
    employee_blogs_config      = EmployeeBlogsConfigBlock(icon="edit",    label="Employee Blogs Table Config")
    comments_moderation_config = CommentsModerationConfigBlock(icon="comment", label="Comments Moderation Config")
    footer_settings_config     = FooterSettingsConfigBlock(icon="site",   label="Footer Settings & Social Links")

    class Meta:
        icon = "cogs"
        label = "Dashboard Body Blocks"
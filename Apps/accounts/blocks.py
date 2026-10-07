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
            ('fa-solid fa-link', 'Link / Generic'),
        ],
        default='fa-regular fa-comments',
        help_text="Choose FontAwesome Icon"
    )
    badge_text = blocks.CharBlock(required=False, max_length=10, help_text="Optional badge")

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
        ],
        default='fa-solid fa-gear',
        help_text="Choose FontAwesome Icon"
    )
    badge_text = blocks.CharBlock(required=False, max_length=10, help_text="Optional badge text (e.g. 24 or New)")
    is_active = blocks.BooleanBlock(required=False, default=False, help_text="Highlight as active/selected item")
    
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

    th_post_title = blocks.CharBlock(required=False, default="POST TITLE")
    th_category = blocks.CharBlock(required=False, default="CATEGORY")
    th_status = blocks.CharBlock(required=False, default="STATUS")
    th_views = blocks.CharBlock(required=False, default="VIEWS")
    th_date = blocks.CharBlock(required=False, default="DATE")
    th_actions = blocks.CharBlock(required=False, default="ACTIONS")

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
# MASTER DASHBOARD STREAMBLOCK (Only Content Body Blocks)
# =========================================================================
class DashboardBodyStreamBlock(blocks.StreamBlock):
    stats_row = StatsRowBlock(icon="table", label="Stat Cards Row")
    recent_posts = RecentPostsTableBlock(icon="list-ul", label="Recent Posts Table")
    audience_overview = AudienceOverviewBlock(icon="group", label="Audience Overview")
    recent_comments = RecentCommentsBlock(icon="comment", label="Recent Comments")
    upgrade_banner = UpgradeBannerBlock(icon="gem", label="Upgrade Banner")

    class Meta:
        icon = "cogs"
        label = "Dashboard Body Blocks"
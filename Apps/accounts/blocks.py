from wagtail import blocks



# 1. Single Sidebar Link Block (Menu Item)
class SidebarLinkBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=50, default="Posts", help_text="Link name (e.g. Posts, Categories, Media)")
    url = blocks.CharBlock(required=True, max_length=255, default="/cms/pages/", help_text="URL path (e.g. /dashboard/, /cms/pages/)")
    icon = blocks.ChoiceBlock(
        choices=[
            ('fa-table-cells-large', 'Dashboard / Grid'),
            ('fa-pen-nib', 'Pen / Posts'),
            ('fa-layer-group', 'Layer / Categories'),
            ('fa-image', 'Image / Media'),
            ('fa-file-lines', 'File / Pages'),
            ('fa-comments', 'Comments'),
            ('fa-chart-line', 'Chart / Analytics'),
            ('fa-user', 'User / Subscribers'),
            ('fa-wand-magic-sparkles', 'Magic / Appearance'),
            ('fa-puzzle-piece', 'Puzzle / Plugins'),
            ('fa-gear', 'Gear / Settings'),
        ],
        default='fa-file-lines',
        help_text="Choose FontAwesome Icon"
    )
    badge_text = blocks.CharBlock(required=False, max_length=10, help_text="Optional badge text (e.g. 24 or New)")
    is_active = blocks.BooleanBlock(required=False, default=False, help_text="Highlight as active/selected item")

    class Meta:
        icon = "link"
        label = "Sidebar Link Item"


# 1.1 Complete Sidebar Block (Brand + Section + Links)
class SidebarNavBlock(blocks.StructBlock):
    brand_name = blocks.CharBlock(required=False, default="BlogPro", help_text="Brand Logo Name")
    main_links = blocks.ListBlock(SidebarLinkBlock(), help_text="Main menu items (Dashboard, Posts, Categories, etc.)")
    
    section_heading = blocks.CharBlock(required=False, default="PREFERENCES", help_text="Section title (e.g. PREFERENCES)")
    preference_links = blocks.ListBlock(SidebarLinkBlock(), help_text="Preference links (Appearance, Plugins, Settings)")

    class Meta:
        icon = "list-ul"
        label = "Sidebar Navigation"


# 2. Single Stat Card Block
class StatCardBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=50, default="Total Posts")
    value = blocks.CharBlock(required=True, max_length=50, default="128")
    growth = blocks.CharBlock(required=False, max_length=50, default="+ 12.5%", help_text="e.g. + 12.5%")
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
        label = "Stat Card"


# 3. Topbar Header Block
class TopbarBlock(blocks.StructBlock):
    search_placeholder = blocks.CharBlock(required=False, default="Search anything...")
    search_shortcut = blocks.CharBlock(required=False, default="⌘K")
    notification_count = blocks.CharBlock(required=False, default="3")

    class Meta:
        icon = "search"
        label = "Topbar Settings"


# 4. Upgrade Banner Block (Bottom Blue Card)
class UpgradeBannerBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, default="Ready to take your blog to the next level?")
    text = blocks.CharBlock(required=True, default="Upgrade to BlogPro Pro and unlock powerful features.")
    button_text = blocks.CharBlock(required=True, default="Upgrade Now")
    button_url = blocks.CharBlock(required=False, default="#")

    class Meta:
        icon = "gem"
        label = "Bottom Upgrade Banner"


# 5. Sidebar Upgrade Card Block
class SidebarUpgradeCardBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, default="Upgrade to Pro")
    text = blocks.CharBlock(required=True, default="Unlock advanced features and grow your blog faster.")
    button_text = blocks.CharBlock(required=True, default="Upgrade Now")

    class Meta:
        icon = "pick"
        label = "Sidebar Upgrade Card"


# 6. Footer Block
class DashboardFooterBlock(blocks.StructBlock):
    tagline = blocks.TextBlock(required=False, default="The all-in-one blogging platform that helps you create, manage, and grow your blog.")
    newsletter_placeholder = blocks.CharBlock(required=False, default="Enter your email")

    class Meta:
        icon = "form"
        label = "Footer Settings"
from django.contrib import admin
from django.db.models import Count
from django.utils import timezone

from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "post_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_posts=Count("posts"))

    @admin.display(description="Posts", ordering="_posts")
    def post_count(self, obj):
        return obj._posts


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "published", "is_featured", "published_at")
    list_filter = ("published", "is_featured", "category", "published_at")
    list_editable = ("published", "is_featured")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "reading_time")
    date_hierarchy = "created_at"
    list_select_related = ("category", "author")
    actions = ["publish_posts", "unpublish_posts"]
    fieldsets = (
        ("Post", {"fields": ("title", "slug", "category", "author")}),
        ("Content", {"fields": ("excerpt", "content", "featured_image", "featured_image_alt")}),
        ("Publishing", {"fields": ("published", "published_at", "is_featured")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("Bookkeeping", {"fields": ("reading_time", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if obj.author is None:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected posts")
    def publish_posts(self, request, queryset):
        updated = 0
        for post in queryset:
            post.published = True
            if post.published_at is None:
                post.published_at = timezone.now()
            post.save(update_fields=["published", "published_at", "updated_at"])
            updated += 1
        self.message_user(request, f"{updated} post(s) published.")

    @admin.action(description="Unpublish selected posts")
    def unpublish_posts(self, request, queryset):
        updated = queryset.update(published=False)
        self.message_user(request, f"{updated} post(s) unpublished.")

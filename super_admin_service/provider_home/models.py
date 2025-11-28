import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


# ======================================================================
# MAIN HOMEPAGE MODEL (ONE RECORD PER PROVIDER TYPE, WITH VERSIONING)
# ======================================================================
class ProviderHomePage(models.Model):
    PROVIDER_TYPES = [
        ("individual", "Individual"),
        ("organization", "Organization"),
        ("both", "Both"),
    ]

    LAYOUT_TYPES = [
        ("classic", "Classic Layout"),
        ("modern", "Modern Minimal"),
        ("premium", "Premium Gradient Layout"),
        ("full_width", "Full Width Layout"),
        ("boxed", "Boxed Layout"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES, default="both")

    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # Publishing Controls
    is_published = models.BooleanField(default=False)
    publish_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)  # rolling version
    ab_variant = models.CharField(max_length=20, null=True, blank=True)  # "A", "B", "C"

    # Global Page Layout
    layout_type = models.CharField(max_length=50, choices=LAYOUT_TYPES, default="premium")
    show_navigation = models.BooleanField(default=True)
    show_footer = models.BooleanField(default=True)

    # Themes
    primary_color = models.CharField(max_length=20, null=True, blank=True)
    secondary_color = models.CharField(max_length=20, null=True, blank=True)
    background_color = models.CharField(max_length=20, null=True, blank=True)
    text_color = models.CharField(max_length=20, null=True, blank=True)

    # SEO
    seo_title = models.CharField(max_length=255, null=True, blank=True)
    seo_description = models.TextField(null=True, blank=True)
    seo_keywords = models.JSONField(default=list)

    # Audit
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="homepage_created")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="homepage_updated")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-publish_at", "-updated_at"]

    def __str__(self):
        return f"{self.provider_type.title()} Home (v{self.version}) — {self.slug}"

    @property
    def is_active(self):
        if not self.is_published:
            return False
        if self.publish_at and timezone.now() < self.publish_at:
            return False
        return True


# ======================================================================
# HERO SECTION
# ======================================================================
class HeroBanner(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="hero_banners", on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    subtitle = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.URLField(max_length=2000, null=True, blank=True)

    cta_text = models.CharField(max_length=200, null=True, blank=True)
    cta_url = models.URLField(max_length=2000, null=True, blank=True)

    overlay_color = models.CharField(max_length=20, null=True, blank=True)
    gradient_background = models.CharField(max_length=50, null=True, blank=True)

    layout = models.CharField(
        max_length=50,
        default="image_right",
        choices=[
            ("image_left", "Image Left"),
            ("image_right", "Image Right"),
            ("centered", "Centered"),
            ("full_width", "Full Width Hero")
        ]
    )

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# BANNER SLIDER / CAROUSEL
# ======================================================================
class BannerSlide(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="banner_slides", on_delete=models.CASCADE)
    
    image = models.URLField(max_length=2000)
    title = models.CharField(max_length=255, null=True, blank=True)
    subtitle = models.CharField(max_length=500, null=True, blank=True)
    
    cta_text = models.CharField(max_length=200, null=True, blank=True)
    cta_url = models.URLField(max_length=2000, null=True, blank=True)
    animation = models.CharField(max_length=50, null=True, blank=True)  # fade/slide/zoom

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# IMAGE GALLERY
# ======================================================================
class HomeImage(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="images", on_delete=models.CASCADE)
    image = models.URLField(max_length=2000)
    caption = models.CharField(max_length=255, null=True, blank=True)
    style = models.CharField(max_length=50, null=True, blank=True)  # rounded, square, circle

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# FEATURES SECTION
# ======================================================================
class FeatureCard(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="features", on_delete=models.CASCADE)
    
    icon = models.CharField(max_length=200, null=True, blank=True)  # mdi-dog, fa-user
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    
    badge_text = models.CharField(max_length=50, null=True, blank=True)  # NEW, PREMIUM
    highlight = models.BooleanField(default=False)  # bold highlight
    
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# TESTIMONIALS (Rich)
# ======================================================================
class Testimonial(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="testimonials", on_delete=models.CASCADE)
    
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, null=True, blank=True)
    review = models.TextField()
    image = models.URLField(max_length=2000, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    company_logo = models.URLField(max_length=2000, null=True, blank=True)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# VIDEO SECTION
# ======================================================================
class HomeVideo(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="videos", on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=2000)
    thumbnail = models.URLField(max_length=2000, null=True, blank=True)

    autoplay = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# SERVICES SECTION
# ======================================================================
class ServiceCard(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="services", on_delete=models.CASCADE)
    
    icon = models.CharField(max_length=200, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)

    highlight_color = models.CharField(max_length=20, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


# ======================================================================
# FAQ SECTION
# ======================================================================
class FAQItem(models.Model):
    home = models.ForeignKey(ProviderHomePage, related_name="faqs", on_delete=models.CASCADE)
    
    question = models.CharField(max_length=500)
    answer = models.TextField()

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

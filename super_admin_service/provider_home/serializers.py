# provider_home/serializers.py
from rest_framework import serializers
from .models import (
    ProviderHomePage, HeroBanner, BannerSlide, HomeImage, FeatureCard,
    Testimonial, HomeVideo, ServiceCard, FAQItem
)

class HeroBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroBanner
        fields = "__all__"
        read_only_fields = ("home", "id")

class BannerSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerSlide
        fields = "__all__"
        read_only_fields = ("home", "id")

class HomeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeImage
        fields = "__all__"
        read_only_fields = ("home", "id")

class FeatureCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureCard
        fields = "__all__"
        read_only_fields = ("home", "id")

class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = "__all__"
        read_only_fields = ("home", "id")

class HomeVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeVideo
        fields = "__all__"
        read_only_fields = ("home", "id")

class ServiceCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCard
        fields = "__all__"
        read_only_fields = ("home", "id")

class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = "__all__"
        read_only_fields = ("home", "id")


class ProviderHomePageSerializer(serializers.ModelSerializer):
    hero_banners = HeroBannerSerializer(many=True, read_only=True)
    banner_slides = BannerSlideSerializer(many=True, read_only=True)
    images = HomeImageSerializer(many=True, read_only=True)
    features = FeatureCardSerializer(many=True, read_only=True)
    testimonials = TestimonialSerializer(many=True, read_only=True)
    videos = HomeVideoSerializer(many=True, read_only=True)
    services = ServiceCardSerializer(many=True, read_only=True)
    faqs = FAQItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProviderHomePage
        # Admin CRUD needs all page-level fields + nested read-only children
        fields = [
            "id", "provider_type", "slug", "version", "ab_variant",
            "layout_type", "show_navigation", "show_footer",
            "primary_color", "secondary_color", "background_color", "text_color",
            "seo_title", "seo_description", "seo_keywords",
            "is_published", "publish_at", "created_by", "updated_by",
            "created_at", "updated_at",
            "hero_banners", "banner_slides", "images", "features",
            "testimonials", "videos", "services", "faqs"
        ]
        read_only_fields = ("id", "created_at", "updated_at", "version")

# import logging
# from django.db import transaction
# from django.utils import timezone

# from .models import (
#     ServiceProvider,
#     BusinessDetails,
#     DocumentVerification,
#     VerificationWorkflow,
# )

# logger = logging.getLogger(__name__)
# @transaction.atomic
# def update_provider_profile(verified_user, data):
#     """
#     Update personal details for a service provider.
#     Automatically updates verification workflow stage if profile is completed.
#     """
#     provider, _ = ServiceProvider.objects.get_or_create(verified_user=verified_user)

#     # Update basic info
#     provider.full_name = data.get("full_name", provider.full_name)
#     provider.email = data.get("email", provider.email)
#     provider.phone_number = data.get("phone_number", provider.phone_number)
#     provider.role = data.get("role", provider.role)
#     provider.save()

#     # Update workflow stage
#     workflow, _ = VerificationWorkflow.objects.get_or_create(
#         service_provider=provider, verified_user=verified_user
#     )

#     if workflow.verified_stage == "personal_pending":
#         workflow.verified_stage = "business_pending"
#         workflow.save(update_fields=["verified_stage", "last_updated"])
#         logger.info(f"✅ Profile completed for {verified_user.email}, moved to business_pending")

#     return provider
# @transaction.atomic
# def update_business_details(verified_user, data):
#     """
#     Update or create business details for the service provider.
#     Automatically moves workflow stage to 'documents_pending'.
#     """
#     provider = ServiceProvider.objects.get(verified_user=verified_user)

#     business, _ = BusinessDetails.objects.get_or_create(
#         service_provider=provider, verified_user=verified_user
#     )

#     # Update business info
#     for field in [
#         "business_name", "business_type", "business_description",
#         "gst_number", "pan_number", "address", "city", "state", "pincode"
#     ]:
#         if field in data:
#             setattr(business, field, data[field])

#     business.save()

#     # Update workflow stage
#     workflow, _ = VerificationWorkflow.objects.get_or_create(
#         service_provider=provider, verified_user=verified_user
#     )

#     if workflow.verified_stage == "business_pending":
#         workflow.verified_stage = "documents_pending"
#         workflow.save(update_fields=["verified_stage", "last_updated"])
#         logger.info(f"✅ Business info completed for {verified_user.email}, moved to documents_pending")

#     return business
# @transaction.atomic
# def upload_documents(verified_user, files):
#     """
#     Handles upload of provider verification documents.
#     Moves workflow to 'documents_pending' if all required files are uploaded.
#     """
#     provider = ServiceProvider.objects.get(verified_user=verified_user)

#     docs, _ = DocumentVerification.objects.get_or_create(
#         service_provider=provider, verified_user=verified_user
#     )

#     # Update document fields dynamically
#     for field, file_obj in files.items():
#         if hasattr(docs, field) and file_obj:
#             setattr(docs, field, file_obj)

#     docs.save()

#     workflow, _ = VerificationWorkflow.objects.get_or_create(
#         service_provider=provider, verified_user=verified_user
#     )

#     if workflow.verified_stage == "documents_pending":
#         workflow.manual_verification = True
#         workflow.save(update_fields=["manual_verification", "last_updated"])
#         logger.info(f"📄 Documents uploaded for {verified_user.email}, pending admin verification")

#     return docs
# @transaction.atomic
# def verify_provider_by_admin(verified_user, verified_by):
#     """
#     Called by SuperAdmin after manual document verification.
#     Marks provider as fully verified.
#     """
#     provider = ServiceProvider.objects.get(verified_user=verified_user)
#     docs = DocumentVerification.objects.get(service_provider=provider)
#     workflow = VerificationWorkflow.objects.get(service_provider=provider)

#     docs.is_verified = True
#     docs.verified_by = verified_by
#     docs.verified_at = timezone.now()
#     docs.save()

#     # Update provider and workflow status
#     provider.is_fully_verified = True
#     provider.profile_status = "active"
#     provider.save(update_fields=["is_fully_verified", "profile_status"])

#     workflow.verified_stage = "verified"
#     workflow.save(update_fields=["verified_stage", "last_updated"])

#     logger.info(f"🏁 Provider {provider.email} verified by {verified_by}")

#     return {
#         "message": f"Provider {provider.email} verified successfully.",
#         "verified_by": verified_by,
#         "status": "verified",
#     }
# def auto_check_full_verification(verified_user):
#     """
#     Auto-check if provider is fully verified.
#     """
#     try:
#         provider = ServiceProvider.objects.get(verified_user=verified_user)
#         business = BusinessDetails.objects.filter(
#             verified_user=verified_user, is_business_verified=True
#         ).exists()
#         docs = DocumentVerification.objects.filter(
#             verified_user=verified_user, is_verified=True
#         ).exists()

#         if business and docs:
#             provider.is_fully_verified = True
#             provider.profile_status = "active"
#             provider.save(update_fields=["is_fully_verified", "profile_status"])
#             logger.info(f"✅ Auto verification passed for {provider.email}")
#             return True
#         return False
#     except Exception as e:
#         logger.warning(f"⚠️ Auto verification check failed: {e}")
#         return False

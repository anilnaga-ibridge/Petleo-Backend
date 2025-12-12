import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist
from django.utils.html import strip_tags

from .models import EmailTemplate

logger = logging.getLogger(__name__)

# Allowed static template names
VALID_ROLES = ["admin", "individual", "organization", "superadmin"]


# ------------------------------------------------------------------------------
# Render HTML Template from String (DB templates)
# ------------------------------------------------------------------------------
def render_template_body_from_string(html_content: str, context: dict) -> str:
    """
    Render HTML stored in DB using Django Template/Context.
    If rendering fails, fallback to a simple string replace.
    """
    try:
        tpl = Template(html_content)
        return tpl.render(Context(context))
    except Exception:
        logger.exception("Template rendering from string failed — fallback to simple replace")

        body = html_content
        for k, v in (context or {}).items():
            body = body.replace("{{" + k + "}}", str(v))
        return body


# ------------------------------------------------------------------------------
# Send email using a DB EmailTemplate object
# ------------------------------------------------------------------------------
def send_email_from_template_obj(template_obj: EmailTemplate, to_email: str, context: dict) -> bool:
    try:
        html_message = render_template_body_from_string(template_obj.html_content, context or {})
        plain_message = strip_tags(html_message)

        send_mail(
            template_obj.subject or context.get("subject", "Notification"),
            plain_message,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Email sent to {to_email} using DB template {template_obj.id}")
        return True

    except Exception:
        logger.exception(f"Failed to send email using DB template {template_obj.id}")
        return False


# ------------------------------------------------------------------------------
# Send email using static HTML template file
# ------------------------------------------------------------------------------
def send_email_from_static_template(template_filename: str, to_email: str, context: dict) -> bool:
    try:
        html_message = render_to_string(f"emails/{template_filename}", context or {})
        plain_message = strip_tags(html_message)

        send_mail(
            context.get("subject", "Notification"),
            plain_message,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Email sent to {to_email} using static template {template_filename}")
        return True

    except TemplateDoesNotExist:
        logger.warning(f"Static template not found: {template_filename}")
        return False

    except Exception:
        logger.exception(f"Error sending static template email: {template_filename}")
        return False


# ------------------------------------------------------------------------------
# Automatic Registration Email (with DB + static fallback)
# ------------------------------------------------------------------------------
def send_automatic_registration_email_for_user(user) -> bool:
    """
    Fallback order:
      1) Exact DB template for the user's role
      2) DB template for role='all'
      3) Static template: welcome_<role>.html
      4) Static template: welcome_default.html
    """

    try:
        # Extract role safely
        role_obj = getattr(user, "role", None)
        role_key = (
            role_obj.name.lower().strip()
            if role_obj and getattr(role_obj, "name", None)
            else None
        )

        # Validate role name
        if role_key not in VALID_ROLES:
            logger.warning(f"Invalid or unsupported role '{role_key}' for user {user.id}, using default.")
            role_key = None

        # Email context
        context = {
            "full_name": getattr(user, "full_name", "") or 
                         f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip(),
            "email": user.email,
            "phone_number": getattr(user, "phone_number", ""),
            "role": role_key or "user",
            "user_id": str(user.id),
            "subject": f"Welcome, {getattr(user, 'full_name', 'User')}!",
        }

        # --- 1) Exact DB template for role ---
        template = None
        if role_key:
            logger.info(f"🔍 Searching for DB template: role={role_key}, type=automatic")
            # Try default first
            template = EmailTemplate.objects.filter(
                role=role_key,
                type="automatic",
                is_default=True,
                is_active=True,
            ).first()
            
            if template:
                 logger.info(f"✅ Found DEFAULT template for role={role_key}: {template.id}")

            # Fallback to latest active if no default
            if not template:
                template = EmailTemplate.objects.filter(
                    role=role_key,
                    type="automatic",
                    is_active=True,
                ).order_by('-updated_at').first()
                if template:
                     logger.info(f"✅ Found LATEST template for role={role_key}: {template.id}")

        # --- 2) DB fallback: role='all' ---
        if not template:
            logger.info(f"🔍 Searching for DB template: role=all, type=automatic")
            # Try default first
            template = EmailTemplate.objects.filter(
                role="all",
                type="automatic",
                is_default=True,
                is_active=True,
            ).first()
            
            if template:
                 logger.info(f"✅ Found DEFAULT template for role=all: {template.id}")

            # Fallback to latest active if no default
            if not template:
                template = EmailTemplate.objects.filter(
                    role="all",
                    type="automatic",
                    is_active=True,
                ).order_by('-updated_at').first()
                if template:
                     logger.info(f"✅ Found LATEST template for role=all: {template.id}")

        # Use DB template if found
        if template:
            return send_email_from_template_obj(template, user.email, context)

        # --- 3 & 4) Static template fallback ---
        static_candidates = []
        if role_key:
            static_candidates.append(f"welcome_{role_key}.html")
        static_candidates.append("welcome_default.html")

        for fname in static_candidates:
            if send_email_from_static_template(fname, user.email, context):
                return True

        logger.info(f"No DB or static template found for role={role_key}; email skipped for user {user.id}")
        return False

    except Exception:
        logger.exception("send_automatic_registration_email_for_user failed")
        return False


# ------------------------------------------------------------------------------
# Manual Email (Admin trigger)
# ------------------------------------------------------------------------------
def send_manual_email(template_id, user) -> bool:
    try:
        template = EmailTemplate.objects.get(id=template_id, is_active=True)

        context = {
            "full_name": getattr(user, "full_name", "") or 
                         f"{getattr(user, 'first_name','')} {getattr(user,'last_name','')}".strip(),
            "email": user.email,
            "role": getattr(user.role, "name", "") if getattr(user, "role", None) else "",
            "user_id": str(user.id),
            "subject": template.subject or "Message",
        }

        return send_email_from_template_obj(template, user.email, context)

    except EmailTemplate.DoesNotExist:
        logger.error(f"Manual email failed — template {template_id} not found or inactive")
        return False

    except Exception:
        logger.exception("Manual email sending failed")
        return False



# import logging
# from django.conf import settings
# from django.core.mail import send_mail
# from django.template import Template, Context
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags
# from django.apps import apps

# from .models import EmailTemplate

# logger = logging.getLogger(__name__)


# # -------------------------------------------------------------------
# # ROLE RESOLUTION (works with object, id, uuid, string)
# # -------------------------------------------------------------------
# def get_role_name(role_value):
#     """
#     Convert any input to role name:
#     - Role object
#     - Integer ID
#     - UUID ID
#     - String name
#     """
#     if not role_value:
#         return None

#     # Case 1: Role object
#     if hasattr(role_value, "name"):
#         return role_value.name.lower()

#     # Case 2: String role name
#     if isinstance(role_value, str) and not role_value.replace("-", "").isdigit():
#         return role_value.lower()

#     # Case 3: Numeric, UUID → lookup Role
#     try:
#         Role = apps.get_model("users", "Role")
#         role_obj = Role.objects.filter(id=role_value).first()
#         if role_obj:
#             return role_obj.name.lower()

#         logger.warning(f"⚠️ No role found with ID {role_value}")
#         return None
#     except Exception as e:
#         logger.error(f"⚠️ Role resolution error for value={role_value}: {e}")
#         return None


# # -------------------------------------------------------------------
# # TEMPLATE RENDERING (DB)
# # -------------------------------------------------------------------
# def render_template_body_from_string(html_content: str, context: dict) -> str:
#     """
#     Render HTML stored in DB using Django Template.
#     """
#     try:
#         tpl = Template(html_content)
#         return tpl.render(Context(context))
#     except Exception:
#         logger.exception("Template rendering from string failed — fallback to simple replace")
#         body = html_content
#         for k, v in (context or {}).items():
#             body = body.replace("{{" + k + "}}", str(v))
#         return body


# # -------------------------------------------------------------------
# # SEND USING DB TEMPLATE
# # -------------------------------------------------------------------
# def send_email_from_template_obj(template_obj: EmailTemplate, to_email: str, context: dict) -> bool:
#     try:
#         html_message = render_template_body_from_string(template_obj.html_content, context or {})
#         plain_message = strip_tags(html_message)

#         send_mail(
#             template_obj.subject or context.get("subject", "Notification"),
#             plain_message,
#             getattr(settings, "DEFAULT_FROM_EMAIL", None),
#             [to_email],
#             fail_silently=False,
#             html_message=html_message,
#         )

#         logger.info(f"Email sent to {to_email} using DB template {template_obj.id}")
#         return True

#     except Exception:
#         logger.exception(f"Failed to send email to {to_email} using DB template")
#         return False


# # -------------------------------------------------------------------
# # SEND USING STATIC TEMPLATE (files inside templates/emails/)
# # -------------------------------------------------------------------
# def send_email_from_static_template(template_filename: str, to_email: str, context: dict) -> bool:
#     try:
#         html_message = render_to_string(f"emails/{template_filename}", context or {})
#         plain_message = strip_tags(html_message)

#         send_mail(
#             context.get("subject", "Notification"),
#             plain_message,
#             getattr(settings, "DEFAULT_FROM_EMAIL", None),
#             [to_email],
#             fail_silently=False,
#             html_message=html_message,
#         )

#         logger.info(f"Email sent to {to_email} using static template {template_filename}")
#         return True

#     except Exception:
#         logger.exception(f"Failed to send static template email to {to_email} ({template_filename})")
#         return False


# # -------------------------------------------------------------------
# # AUTOMATIC EMAIL (used on registration)
# # -------------------------------------------------------------------
# def send_automatic_registration_email_for_user(user) -> bool:
#     """
#     Automatic email with fallback priority:
#       1) DB template for role (automatic, is_default=True)
#       2) DB template for 'all'
#       3) templates/emails/welcome_<role>.html
#       4) templates/emails/welcome_default.html
#     """
#     try:
#         # FIXED: Resolve role correctly
#         role_value = getattr(user, "role", None) or getattr(user, "role_id", None)
#         role_key = get_role_name(role_value)

#         context = {
#             "full_name": getattr(user, "full_name", "") or f"{user.first_name} {user.last_name}".strip(),
#             "email": user.email,
#             "role": role_key or "user",
#             "user_id": str(user.id),
#             "subject": f"Welcome, {getattr(user, 'full_name', 'User')}!",
#         }

#         # Step 1 — DB template exact match
#         template = None
#         if role_key:
#             template = EmailTemplate.objects.filter(
#                 role=role_key,
#                 type="automatic",
#                 is_default=True,
#                 is_active=True
#             ).first()

#         # Step 2 — DB template fallback ("all")
#         if not template:
#             template = EmailTemplate.objects.filter(
#                 role="all",
#                 type="automatic",
#                 is_default=True,
#                 is_active=True
#             ).first()

#         if template:
#             return send_email_from_template_obj(template, user.email, context)

#         # Step 3 — static templates folder
#         static_candidates = []
#         if role_key:
#             static_candidates.append(f"welcome_{role_key}.html")
#         static_candidates.append("welcome_default.html")

#         for fname in static_candidates:
#             if send_email_from_static_template(fname, user.email, context):
#                 return True

#         logger.warning(f"No DB/static template found for role={role_key}. Skipping email.")
#         return False

#     except Exception:
#         logger.exception("send_automatic_registration_email_for_user failed")
#         return False


# # -------------------------------------------------------------------
# # MANUAL EMAIL
# # -------------------------------------------------------------------
# def send_manual_email(template_id, user) -> bool:
#     try:
#         template = EmailTemplate.objects.get(id=template_id, is_active=True)

#         context = {
#             "full_name": getattr(user, "full_name", "") or f"{user.first_name} {user.last_name}".strip(),
#             "email": user.email,
#             "role": get_role_name(getattr(user, "role", None)),
#             "user_id": str(user.id),
#             "subject": template.subject or "Message",
#         }

#         return send_email_from_template_obj(template, user.email, context)

#     except EmailTemplate.DoesNotExist:
#         logger.error(f"Template {template_id} not found or inactive")
#         return False
#     except Exception:
#         logger.exception("Failed sending manual email")
#         return False

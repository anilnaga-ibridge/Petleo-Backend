import os
import uuid
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
import requests
import logging

from .models import Invoice, InvoiceSequence, TaxConfiguration, Booking

# ReportLab imports for PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from io import BytesIO

logger = logging.getLogger(__name__)

class AuditSafeSequenceGenerator:
    """
    Ensures unique, sequential, monotonic invoice numbering using select_for_update.
    Format: PO-YYYY-NNNNNN
    """
    @staticmethod
    def get_next_number():
        year = timezone.now().year
        with transaction.atomic():
            sequence, created = InvoiceSequence.objects.select_for_update().get_or_create(year=year)
            sequence.last_number += 1
            sequence.save()
            
            return f"PO-{year}-{sequence.last_number:06d}"


class InvoiceService:
    @staticmethod
    def generate_invoice(booking_id):
        """
        Main entry point to create an invoice for a booking.
        Typically called after payment success.
        """
        try:
            booking = Booking.objects.get(id=booking_id)
            
            # 1. Check if invoice already exists for this booking (unless we allow multiple)
            # For now, one main invoice per booking header
            if Invoice.objects.filter(booking=booking, status__in=['PAID', 'ISSUED']).exists():
                logger.info(f"Invoice already exists for booking {booking_id}")
                return Invoice.objects.filter(booking=booking).first()

            # 2. Collect Snapshots
            provider_data = InvoiceService._fetch_provider_details(booking)
            customer_data = InvoiceService._fetch_customer_details(booking)
            items_data = InvoiceService._snapshot_items(booking)
            
            # 3. Calculate Taxes
            tax_config = TaxConfiguration.objects.filter(key="GST_STANDARD", is_active=True).first()
            tax_rate = tax_config.rate if tax_config else Decimal("18.00")
            
            subtotal = booking.total_price
            tax_amount = (subtotal * (tax_rate / 100)).quantize(Decimal("0.01"))
            total_amount = subtotal + tax_amount
            
            # 4. Create Invoice Record
            invoice_number = AuditSafeSequenceGenerator.get_next_number()
            
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    booking=booking,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    currency=booking.currency,
                    status='ISSUED',
                    provider_snapshot=provider_data,
                    customer_snapshot=customer_data,
                    tax_snapshot={
                        "tax_key": "GST_STANDARD",
                        "rate": str(tax_rate),
                        "mode": "STANDARD"
                    },
                    items_snapshot=items_data
                )
                
                # 5. Background PDF Generation (Simulated here as sync for now)
                # In production, this would be a Celery task
                InvoiceService.generate_pdf_task(invoice.id)
                
                return invoice

        except Exception as e:
            logger.exception(f"Failed to generate invoice for booking {booking_id}: {e}")
            return None

    @staticmethod
    def _fetch_provider_details(booking):
        """Fetch provider billing info from service_provider_service."""
        # Get the first item to find the provider
        item = booking.items.first()
        if not item:
            return {"name": "Unknown Provider", "address": ""}
            
        provider_id = item.provider_id
        url = f"http://localhost:8002/api/provider/resolve-details/?provider_id={provider_id}"
        
        try:
            # We use a timeout to avoid blocking
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": str(provider_id),
                    "name": data.get("provider_name", "PetLeo Partner"),
                    "address": data.get("address", "N/A"),
                    "tax_id": data.get("tax_id", ""),
                    "email": data.get("email", ""),
                    "phone": data.get("phone", "")
                }
        except Exception as e:
            logger.error(f"Failed to resolve provider {provider_id} details: {e}")
            
        return {
            "id": str(provider_id),
            "name": "PetLeo Partner",
            "address": "See booking details",
            "tax_id": ""
        }

    @staticmethod
    def _fetch_customer_details(booking):
        """Snapshot customer info from the profile."""
        owner = booking.owner
        return {
            "name": owner.full_name or "Valued Customer",
            "email": owner.email or "",
            "phone": owner.phone_number or "",
            "address": booking.address_snapshot or {}
        }

    @staticmethod
    def _snapshot_items(booking):
        """Detailed list of items for the invoice line items."""
        items = []
        for item in booking.items.all():
            items.append({
                "service": item.service_snapshot.get("name", "Service"),
                "pet": item.pet.name if item.pet else "Pet",
                "time": item.selected_time.strftime("%Y-%m-%d %H:%M") if item.selected_time else "",
                "price": str(item.price_snapshot.get("price", "0.00"))
            })
        return items

    @staticmethod
    def generate_pdf_task(invoice_id):
        """
        Logic to build the PDF file using ReportLab and save it to the Invoice model.
        """
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            normal_style = styles['Normal']
            
            # --- Header ---
            elements.append(Paragraph(f"INVOICE: {invoice.invoice_number}", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # --- Provider & Customer Info ---
            p_snap = invoice.provider_snapshot
            c_snap = invoice.customer_snapshot
            
            info_data = [
                [Paragraph(f"<b>From:</b><br/>{p_snap['name']}<br/>{p_snap['address']}<br/>GSTIN: {p_snap.get('tax_id', 'N/A')}", normal_style),
                 Paragraph(f"<b>To:</b><br/>{c_snap['name']}<br/>{c_snap['email']}<br/>{c_snap['phone']}", normal_style)]
            ]
            
            info_table = Table(info_data, colWidths=[3*inch, 3*inch])
            elements.append(info_table)
            elements.append(Spacer(1, 0.4*inch))
            
            # --- Items Table ---
            table_data = [['Service', 'Pet', 'Date/Time', 'Price']]
            for item in invoice.items_snapshot:
                table_data.append([
                    item['service'],
                    item['pet'],
                    item['time'],
                    f"{invoice.currency} {item['price']}"
                ])
                
            item_table = Table(table_data, colWidths=[2.5*inch, 1.25*inch, 1.5*inch, 1.25*inch])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(item_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # --- Totals ---
            summary_data = [
                ['Subtotal:', f"{invoice.currency} {invoice.subtotal}"],
                ['Tax (GST):', f"{invoice.currency} {invoice.tax_amount}"],
                ['Total:', f"{invoice.currency} {invoice.total_amount}"]
            ]
            summary_table = Table(summary_data, colWidths=[4.5*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
                ('LINEABOVE', (0, 2), (-1, 2), 1, colors.black)
            ]))
            elements.append(summary_table)
            
            # --- Footer ---
            elements.append(Spacer(1, 1*inch))
            elements.append(Paragraph("Thank you for choosing PetLeo! All services are subject to terms and conditions.", styles['Italic']))
            
            # Build PDF
            doc.build(elements)
            
            # Save to model
            filename = f"invoice_{invoice.invoice_number}.pdf"
            invoice.pdf_file.save(filename, ContentFile(buffer.getvalue()))
            invoice.save()
            
            buffer.close()
            return True
            
        except Exception as e:
            logger.error(f"PDF generation failed for invoice {invoice_id}: {e}")
            return False

import os
from io import BytesIO
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from .models import Invoice, BillingAuditLog

class PDFEngine:
    """
    High-fidelity PDF generation using reportlab.
    """
    @staticmethod
    def generate_invoice_pdf(invoice_id):
        invoice = Invoice.objects.get(id=invoice_id)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        
        styles = getSampleStyleSheet()
        elements = []
        
        # 1. Header (Logo + Title)
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor("#2C3E50"),
            alignment=1,
            spaceAfter=20
        )
        elements.append(Paragraph("TAX INVOICE", header_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # 2. Seller and Buyer Info Table
        info_data = [
            [Paragraph(f"<b>SOLD BY:</b><br/>{invoice.seller_name}<br/>{invoice.seller_address}<br/>GSTIN: {invoice.seller_gstin}<br/>State: {invoice.seller_state_code}", styles['Normal']),
             Paragraph(f"<b>BILL TO:</b><br/>{invoice.buyer_name}<br/>{invoice.buyer_address}<br/>GSTIN: {invoice.buyer_gstin or 'N/A'}<br/>State: {invoice.buyer_state_code}", styles['Normal'])]
        ]
        info_table = Table(info_data, colWidths=[3 * inch, 3 * inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # 3. Invoice Meta (Number, Date)
        meta_data = [
            [f"Invoice Number: {invoice.invoice_number}", f"Date: {invoice.issued_at.strftime('%Y-%m-%d')}"]
        ]
        meta_table = Table(meta_data, colWidths=[3 * inch, 3 * inch])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # 4. Line Items Table
        line_items = [
            ["Description", "Base Price", "Taxable Amt", "Net Amt"]
        ]
        # For simplicity, single item as it is a plan purchase
        line_items.append([
            f"{invoice.purchased_plan.plan.title} - {invoice.purchased_plan.billing_cycle}",
            f"{invoice.base_price}",
            f"{invoice.taxable_amount}",
            f"{invoice.total_amount}"
        ])
        
        items_table = Table(line_items, colWidths=[3 * inch, 1.2 * inch, 1 * inch, 1 * inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ECF0F1")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # 5. Tax Breakdown
        tax_data = []
        if invoice.tax_mode == "INTRA_STATE":
            tax_data.append(["CGST", f"{invoice.cgst_rate}%", f"{invoice.gst_amount / 2}"])
            tax_data.append(["SGST", f"{invoice.sgst_rate}%", f"{invoice.gst_amount / 2}"])
        else:
            tax_data.append(["IGST", f"{invoice.igst_rate}%", f"{invoice.gst_amount}"])
            
        tax_data.append([Paragraph("<b>TOTAL TAX</b>", styles['Normal']), "", f"<b>{invoice.gst_amount}</b>"])
        tax_data.append([Paragraph("<b>GRAND TOTAL</b>", styles['Normal']), "", f"<b>{invoice.currency} {invoice.total_amount}</b>"])
        
        tax_table = Table(tax_data, colWidths=[2 * inch, 1 * inch, 1.2 * inch])
        tax_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        # Wrap tax table in a container to push to right
        wrapper_table = Table([[None, tax_table]], colWidths=[2.2 * inch, 4.2 * inch])
        wrapper_table.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
        
        elements.append(wrapper_table)
        elements.append(Spacer(1, 0.5 * inch))
        
        # 6. Footer
        footer_text = "This is a computer-generated invoice and does not require a signature."
        elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)))
        
        # Build PDF
        doc.build(elements)
        
        # 7. Save to Model
        filename = f"invoice_{invoice.invoice_number}.pdf"
        invoice.pdf_file.save(filename, ContentFile(buffer.getvalue()), save=True)
        
        BillingAuditLog.objects.create(
            invoice=invoice,
            event_type="pdf.generated",
            description="Professional tax invoice PDF generated."
        )
        
        return invoice.pdf_file.url

    @staticmethod
    def generate_migration_record_pdf(recovery_id):
        from .models import LegacyEntitlementRecovery
        recovery = LegacyEntitlementRecovery.objects.get(id=recovery_id)
        plan = recovery.purchased_plan
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        
        styles = getSampleStyleSheet()
        elements = []
        
        # 1. Header (Watermark Emphasis)
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor("#7F8C8D"),
            alignment=1,
            spaceAfter=5
        )
        elements.append(Paragraph("LEGACY ENTITLEMENT RECORD", header_style))
        
        watermark_style = ParagraphStyle(
            'Watermark',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            alignment=1,
            spaceAfter=20
        )
        elements.append(Paragraph("<b>INTERNAL SYSTEM RECORD - NOT A TAX INVOICE</b>", watermark_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Resolve Name
        user_name = "N/A"
        if hasattr(plan.user, 'full_name') and plan.user.full_name:
            user_name = plan.user.full_name
        elif hasattr(plan.user, 'first_name') or hasattr(plan.user, 'last_name'):
            user_name = f"{getattr(plan.user, 'first_name', '')} {getattr(plan.user, 'last_name', '')}".strip() or plan.user.email
        else:
            user_name = getattr(plan.user, 'email', 'Unknown')

        # 2. Entity Info
        info_data = [
            [Paragraph(f"<b>ISSUED TO:</b><br/>{user_name}<br/>Organization: {getattr(plan.user, 'billing_profile', None).legal_name if getattr(plan.user, 'billing_profile', None) else 'N/A'}", styles['Normal']),
             Paragraph(f"<b>STATUS:</b><br/>RECONCILED LEGACY ACCESS<br/><b>RECORD ID:</b> {recovery.migration_record_number}", styles['Normal'])]
        ]
        info_table = Table(info_data, colWidths=[3 * inch, 3 * inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # 3. Entitlement Details
        details = [
            ["Entitlement Detail", "Value"],
            ["Plan Title", plan.plan.title],
            ["Billing Cycle", plan.billing_cycle],
            ["Start Date", plan.start_date.strftime('%Y-%m-%d')],
            ["Sync Source", "MIGRATION_RECOVERY"],
            ["Reconciliation Date", recovery.recovered_at.strftime('%Y-%m-%d')]
        ]
        
        details_table = Table(details, colWidths=[2 * inch, 4 * inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F2F4F4")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.5 * inch))
        
        # 4. Certification
        elements.append(Paragraph("<b>Certification of Entitlement</b>", styles['Heading3']))
        cert_text = (
            "This record confirms that the above entity holds a valid legacy entitlement "
            "migrated from the previous billing system. This document grants access to the "
            "specified platform capabilities but does not represent a new commercial transaction "
            "or a tax-deductible expense."
        )
        elements.append(Paragraph(cert_text, styles['Normal']))
        elements.append(Spacer(1, 1 * inch))
        
        # 5. Footer
        footer_text = f"Record generated by {recovery.administered_by} on {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)))
        
        doc.build(elements)
        
        # Save to metadata JSON instead of a file field on PurchasedPlan (since we aren't adding a FileField there to keep it lean)
        # Actually, let's store it locally and return the buffer for view to handle or we can save it to media/records/
        # To follow existing pattern, let's just return the buffer or handle saving.
        # User requested "generate MR-prefixed record", let's save to a record/ folder.
        
        record_dir = os.path.join(settings.MEDIA_ROOT, "migration_records")
        os.makedirs(record_dir, exist_ok=True)
        filename = f"record_{recovery.migration_record_number}.pdf"
        filepath = os.path.join(record_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
            
        recovery.metadata_json["pdf_record_path"] = f"/media/migration_records/{filename}"
        recovery.save(update_fields=["metadata_json"])
        
        return recovery.metadata_json["pdf_record_path"]

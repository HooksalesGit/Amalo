
from __future__ import annotations
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from core.presets import DISCLAIMER

def build_prequal_pdf(out_path: str, branding: dict, summary: dict, incomes_table: list[list], warnings: list[dict], checklist: list[dict]):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=LETTER, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []
    title = branding.get("title","Prequalification Summary")
    story += [Paragraph(f"<b>{title}</b>", styles['Title']), Spacer(1,6)]
    if branding.get("mlo"): story.append(Paragraph(f"MLO: {branding['mlo']}  |  NMLS: {branding.get('nmls','')}", styles['Normal']))
    if branding.get("contact"): story.append(Paragraph(f"Contact: {branding['contact']}", styles['Normal']))
    story += [Spacer(1, 12)]
    ds = summary.get("deal_snapshot", {})
    deal_rows = [[k, f"{v}"] for k,v in ds.items()]
    if deal_rows:
        t = Table([["Deal Snapshot",""]] + deal_rows, hAlign='LEFT', colWidths=[200, 320])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey),('BOX',(0,0),(-1,-1),1,colors.black),('INNERGRID',(0,0),(-1,-1),0.5,colors.grey)]))
        story += [t, Spacer(1, 12)]
    if incomes_table:
        t = Table(incomes_table, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey),('BOX',(0,0),(-1,-1),1,colors.black),('INNERGRID',(0,0),(-1,-1),0.5,colors.grey)]))
        story += [Paragraph("<b>Income by Borrower (Monthly)</b>", styles['Heading3']), Spacer(1,6), t, Spacer(1,12)]
    totals = summary.get("totals", {})
    tot_rows = [[k, f"{v}"] for k,v in totals.items()]
    if tot_rows:
        t = Table([["Totals",""]] + tot_rows, hAlign='LEFT', colWidths=[200, 320])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey),('BOX',(0,0),(-1,-1),1,colors.black),('INNERGRID',(0,0),(-1,-1),0.5,colors.grey)]))
        story += [t, Spacer(1, 12)]
    if warnings:
        w_rows = [["Code","Severity","Message"]]+[[w.get("code",""), w.get("severity",""), w.get("message","")] for w in warnings]
        t = Table(w_rows, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey),('BOX',(0,0),(-1,-1),1,colors.black),('INNERGRID',(0,0),(-1,-1),0.5,colors.grey)]))
        story += [Paragraph("<b>Warnings</b>", styles['Heading3']), Spacer(1,6), t, Spacer(1,12)]
    if checklist:
        rows = [["Required Document","Status"]]+[[c['label'], "✓" if c.get('checked') else "◻︎"] for c in checklist]
        t = Table(rows, hAlign='LEFT', colWidths=[360, 160])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.lightgrey),('BOX',(0,0),(-1,-1),1,colors.black),('INNERGRID',(0,0),(-1,-1),0.5,colors.grey)]))
        story += [Paragraph("<b>Documentation Checklist</b>", styles['Heading3']), Spacer(1,6), t, Spacer(1,12)]
    story += [Spacer(1, 12), Paragraph(f"<font size=8>{DISCLAIMER}</font>", styles['Normal'])]
    doc.build(story)

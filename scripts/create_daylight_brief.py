"""Render the synthetic Daylight source brief. Requires reportlab."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'frontend/src/demo/daylight-brief.json').read_text())
OUT = ROOT / 'output/pdf/daylight-feature-brief.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
INK, MUTED, ACCENT = map(colors.HexColor, ['#202820', '#576052', '#ba401d'])
styles = {
    'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=30, leading=34, textColor=INK, spaceAfter=13),
    'sub': ParagraphStyle('sub', fontName='Helvetica', fontSize=13, leading=19, textColor=MUTED, spaceAfter=14),
    'h': ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=INK, spaceBefore=12, spaceAfter=6),
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=14, textColor=INK, spaceAfter=7),
    'small': ParagraphStyle('small', fontName='Helvetica', fontSize=8.5, leading=11.5, textColor=MUTED, spaceAfter=4),
    'kicker': ParagraphStyle('kicker', fontName='Helvetica-Bold', fontSize=8, leading=12, textColor=ACCENT, spaceAfter=11),
}
def p(text, style='body'):
    return Paragraph(escape(text), styles[style])
def heading(text):
    story.append(p(text, 'h'))
def body(text):
    story.append(p(text))
def footer(canvas, doc):
    w, h = A4
    canvas.setFillColor(ACCENT)
    canvas.rect(44, h-39, 18, 3, fill=1, stroke=0)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(INK)
    canvas.drawString(70, h-39, 'DAYLIGHT / PRODUCT RESEARCH BRIEF')
    canvas.setStrokeColor(colors.HexColor('#d5dacd'))
    canvas.line(44, 43, w-44, 43)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(44, 29, 'Fictional scenario | My Own Researcher | 15 October 2026')
    canvas.drawRightString(w-44, 29, f'{doc.page} / 3')

story = [p('01 / THE PRODUCT DECISION', 'kicker'), p('Will users welcome\nPlan my week?'.replace('\n', ' '), 'title'), p('Daylight - an opt-in weekly planning assistant', 'sub'), p(data['notice'], 'small')]
heading('The company and the problem')
body(data['companyContext'])
stats = Table([[p(m['value'], 'h') for m in data['metrics']], [p(m['label'], 'small') for m in data['metrics']]], colWidths=[169]*3)
stats.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf0e6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,0),8),('BOTTOMPADDING',(0,-1),(-1,-1),8)]))
story.append(stats)
heading('What the fictional signals do - and do not - say')
body(data['problem'])
heading('The proposed feature')
body(data['proposal'])
heading('The decision to explore')
body(data['question'])
story += [PageBreak(), p('02 / OPTIONS AND PERSPECTIVES', 'kicker'), p('A useful shortcut.\nOr one more thing to manage?'.replace('\n',' '), 'title')]
for option in data['options']:
    story.append(Paragraph('<b>'+escape(option['name'])+'</b> - '+escape(option['detail']), styles['body']))
heading('Six fictional participants')
story.append(p('Opening positions are starting assumptions. The simulation may challenge them; none represents a measured customer segment.', 'small'))
rows=[]
for person in data['participants']:
    rows.append([Paragraph('<b>'+escape(person['name'])+'</b><br/>'+escape(person['role']),styles['small']), p(person['context']+' '+person['position'],'small')])
table=Table(rows, colWidths=[113,394])
table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#d5dacd')),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
story.append(table)
story += [PageBreak(), p('03 / THE RESEARCH AGENDA', 'kicker'), p('What we want to learn', 'title')]
for i, question in enumerate(data['researchQuestions'],1):
    story.append(Paragraph(f'<b>0{i} / {escape(question["title"])}</b><br/>'+escape(question['detail']),styles['body']))
heading('Product guardrails to challenge')
for control in data['controls']:
    story.append(p('- '+control,'small'))
heading('What real validation would look like')
story.append(p(data['validation'],'small'))
story.append(p(data['decisionRules'],'small'))
heading('Scope of this demonstration')
story.append(p(data['runScope'],'small'))
doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=65,bottomMargin=57,title='Daylight - Plan my week: feature research brief',author='My Own Researcher',pageCompression=1)
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)

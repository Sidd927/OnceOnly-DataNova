"""Build the OnceOnly DATANOVA 2026 Round 2 pitch deck (python-pptx).

Every figure on these slides is traced in ../OnceOnly_DataNova_Claim_Evidence_Audit.md.
Screenshots are crops of real captures of the running application (submission/media/).

Usage:  python build_deck.py            (writes ../OnceOnly_DataNova_Pitch_Deck.pptx
                                          and ../OnceOnly_DataNova_Presenter_Guide.md)
"""
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.dml import MSO_PATTERN
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUT_DIR = HERE.parent
PPTX = OUT_DIR / "OnceOnly_DataNova_Pitch_Deck.pptx"
GUIDE = OUT_DIR / "OnceOnly_DataNova_Presenter_Guide.md"

# ---------------------------------------------------------------- design tokens
def rgb(h):
    return RGBColor.from_string(h)

BG, PANEL, PANEL2, LINE = rgb("0C1A1F"), rgb("13262C"), rgb("1A3239"), rgb("2B444B")
TEXT, MUTED, DIM = rgb("EAF1EE"), rgb("A3B7B3"), rgb("71897F")
ACC, ACC_D = rgb("3FD0A0"), rgb("1E6B55")
RED, RED_D = rgb("F2667D"), rgb("6E2333")
AMB, BLUE = rgb("E9B44C"), rgb("6CB4D8")
WHITE = rgb("FFFFFF")
SANS, MONO = "Arial", "Courier New"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
L, R, CW = 0.6, 12.733, 12.133  # left margin, right edge, content width (inches)

NOTES: list[dict] = []  # collected for the presenter guide


# ---------------------------------------------------------------- primitives
def _run_style(run, size, color, bold=False, font=SANS, italic=False, spacing=None):
    f = run.font
    f.size, f.bold, f.italic, f.name = Pt(size), bold, italic, font
    f.color.rgb = color
    if spacing is not None:
        run._r.get_or_add_rPr().set("spc", str(spacing))


def text(slide, x, y, w, h, paras, size=16, color=TEXT, bold=False, font=SANS, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, space_after=6, line=1.1, margin=0.0, spacing=None):
    """paras: str | list of paragraphs; a paragraph is str or list of (text, {style}) runs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(margin))
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        para.line_spacing = line
        runs = [(p, {})] if isinstance(p, str) else p
        for t, st in runs:
            r = para.add_run()
            r.text = t
            _run_style(r, st.get("size", size), st.get("color", color), st.get("bold", bold),
                       st.get("font", font), st.get("italic", False), st.get("spacing", spacing))
    return tb


def box(slide, x, y, w, h, fill=PANEL, line=None, radius=0.06, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.0):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def hatch(slide, x, y, w, h, fore=RED, back=RED_D):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.patterned()
    s.fill.pattern = MSO_PATTERN.WIDE_UPWARD_DIAGONAL
    s.fill.fore_color.rgb = fore
    s.fill.back_color.rgb = back
    s.line.color.rgb = fore
    s.line.width = Pt(1.25)
    s.shadow.inherit = False
    return s


def hline(slide, x1, y1, x2, y2, color=LINE, width=1.0, arrow=False, dash=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    if dash:
        d = ln.makeelement(qn("a:prstDash"), {"val": "dash"})
        ln.append(d)
    if arrow:
        tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
        ln.append(tail)
    return c


def pill(slide, x, y, label, fg=ACC, bg=None, size=11, w=None, bold=True):
    w = w or (0.105 * len(label) * size / 11 + 0.3)
    s = box(slide, x, y, w, 0.3, fill=bg or PANEL2, line=fg, radius=0.5, lw=0.75)
    tf = s.text_frame
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(0.02))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    _run_style(r, size, fg, bold, spacing=60)
    return s


def num_badge(slide, x, y, n, d=0.42, fill=ACC, fg=BG, size=15):
    s = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = s.text_frame
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(0))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    _run_style(r, size, fg, True)
    return s


def picture(slide, path, x, y, w=None, h=None, border=LINE):
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    pic.line.color.rgb = border
    pic.line.width = Pt(1)
    return pic


def new_slide(kicker=None, title=None, number=None, notes=None):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    if kicker:
        text(s, L, 0.42, CW, 0.3, kicker.upper(), size=12, color=ACC, bold=True, spacing=200)
    if title:
        text(s, L, 0.72, CW, 0.9, title, size=29, color=TEXT, bold=True, line=1.0)
    if number is not None:
        text(s, L, 7.05, 8, 0.3, "OnceOnly  ·  Every retired tonne, claimed once  ·  DATANOVA 2026", size=10, color=DIM)
        text(s, R - 1.5, 7.05, 1.5, 0.3, str(number), size=10, color=DIM, align=PP_ALIGN.RIGHT)
    if notes:
        NOTES.append(dict(number=number, title=title or kicker, **notes))
        s.notes_slide.notes_text_frame.text = format_notes(notes)
    return s


def format_notes(n):
    parts = [f"[{n['time']}]  SAY:\n{n['say']}", f"WHY THIS SLIDE: {n['why']}", f"KEY POINT: {n['key']}"]
    if n.get("next"):
        parts.append(f"TRANSITION: {n['next']}")
    return "\n\n".join(parts)


def source(slide, s, y=6.68):
    text(slide, L, y, CW, 0.35, s, size=10, color=DIM, line=1.0)


def style_chart(chart, size=12, legend=True):
    chart.font.size = Pt(size)
    chart.font.name = SANS
    chart.font.color.rgb = MUTED
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.color.rgb = TEXT
        chart.legend.font.size = Pt(size)


def style_axes(chart, value_fmt="#,##0", gridlines=True, show_value_axis=True):
    ca, va = chart.category_axis, chart.value_axis
    for ax in (ca, va):
        ax.format.line.color.rgb = LINE
        ax.tick_labels.font.color.rgb = MUTED
        ax.tick_labels.font.size = Pt(12)
    ca.tick_labels.font.color.rgb = TEXT
    va.has_major_gridlines = gridlines
    if gridlines:
        va.major_gridlines.format.line.color.rgb = PANEL2
    va.tick_labels.number_format = value_fmt
    va.tick_labels.number_format_is_linked = False
    va.visible = show_value_axis


def table(slide, x, y, w, rows, col_w, row_h=0.42, size=13, header_fill=PANEL2, first_col_bold=True):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shp.table
    tblPr = tbl._tbl.tblPr
    style_id = tblPr.find(qn("a:tableStyleId"))
    if style_id is not None:
        style_id.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # "No Style, No Grid"
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (PANEL if r % 2 else BG)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.05)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            runs = val if isinstance(val, list) else [(str(val), {})]
            p = tf.paragraphs[0]
            for t, st in runs:
                run = p.add_run()
                run.text = t
                is_head = r == 0
                _run_style(run, st.get("size", size - 1 if is_head else size),
                           st.get("color", ACC if is_head else TEXT),
                           st.get("bold", is_head or (first_col_bold and c == 0)), st.get("font", SANS))
    return tbl


# ================================================================ SLIDES
# ---------------------------------------------------------------- 1 Title
s = new_slide(notes=dict(
    time="0:00-0:20 · 20 s",
    say="Hi, I'm Siddhant, and this is OnceOnly. A carbon registry can prove that a credit was retired. "
        "What it can't tell you is how many public climate claims are quietly relying on those same retired units. "
        "OnceOnly checks exactly that, unit by unit, on real registry data, and shows its working for every finding.",
    why="Judges see many decks; the opening must state the problem in one sentence a non-specialist understands.",
    key="Retirement is checked once; claims about it are not checked at all.",
    next="Let me show you what that gap looks like on one real registry record."))
s.notes_slide  # ensure exists
text(s, L, 0.55, 9, 0.3, "DATANOVA 2026 GLOBAL DATA-THON  ·  ROUND 2", size=12, color=ACC, bold=True, spacing=200)
text(s, L, 1.45, 9, 1.2, "OnceOnly", size=72, bold=True, color=TEXT, line=0.9)
text(s, L, 2.65, 10, 0.8, "Every retired tonne, claimed once.", size=34, color=ACC, line=1.0)
text(s, L, 3.6, 7.6, 1.4,
     "A registry proves a carbon credit was retired. OnceOnly checks whether two public climate claims "
     "are relying on the same retired units, and explains the evidence behind every finding.",
     size=18, color=MUTED, line=1.2)
# interval motif: a ruler with two overlapping claims
rx, ry, rw = L, 5.35, CW
hline(s, rx, ry + 0.95, rx + rw, ry + 0.95, color=LINE, width=1)
for i in range(41):
    tx = rx + rw * i / 40
    hline(s, tx, ry + 0.95, tx, ry + (0.83 if i % 5 else 0.75), color=LINE, width=1)
box(s, rx, ry + 0.05, rw * 0.50, 0.24, fill=ACC_D, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
box(s, rx + rw * 0.272, ry + 0.4, rw * 0.35, 0.24, fill=None, line=MUTED, shape=MSO_SHAPE.RECTANGLE)
hatch(s, rx + rw * 0.272, ry + 0.05, rw * 0.228, 0.24)
hatch(s, rx + rw * 0.272, ry + 0.4, rw * 0.228, 0.24)
text(s, rx + rw * 0.272, ry - 0.3, 4, 0.3, "the same units, in two claims", size=12, color=RED, bold=True)
text(s, L, 6.55, 6.5, 0.3, "Siddhant Patil", size=14, color=TEXT, bold=True)
text(s, L + 4.2, 6.57, 8, 0.3, [[("Live demo  ", {"color": DIM}), ("onceonly-demo.onrender.com", {"font": MONO, "color": TEXT}),
                                  ("     Code  ", {"color": DIM}), ("github.com/Sidd927/OnceOnly-DataNova", {"font": MONO, "color": TEXT})]],
     size=12)

# ---------------------------------------------------------------- 2 Problem
s = new_slide("The problem", "Retirement is checked once. Claims on it are not.", 2, dict(
    time="0:20-1:00 · 40 s",
    say="Registries such as Verra and Gold Standard make sure a credit is retired only once. But retired units then travel into "
        "sustainability reports, product labels and net-zero statements, often through a broker who splits one retirement among several buyers. "
        "Here is a real Verra retirement from August 2026: 19,999 units, with no beneficiary disclosed. In our demo, two synthetic companies each "
        "publish a claim on that batch: 10,000 units and 7,000 units. Each claim checks out against the registry on its own. "
        "Even the totals look fine: 17,000 is less than 19,999. Yet 4,559 units are being claimed by both. "
        "Double counting is something the market's own integrity standard, the ICVCM's Core Carbon Principles, says must not happen.",
    why="Makes the gap concrete with a real record and shows why the obvious sanity check (totals) passes.",
    key="Each claim is valid alone; the problem only exists between claims.",
    next="So why don't existing checks catch this? Because of three properties of real registry data."))
text(s, L, 1.85, 5.0, 4.6, [
    [("Registries guarantee a credit is retired only once.", {"bold": True, "color": TEXT})],
    [("Retired units then flow into reports, labels and net-zero claims, often split by brokers across several buyers.", {"color": MUTED})],
    [("Two companies can cite the same units and each claim still looks valid on its own.", {"bold": True, "color": TEXT})],
    [("Nothing in the current workflow compares claims with each other at unit level.", {"color": MUTED})],
], size=18, space_after=16, line=1.15)
# diagram
dx = 6.05
reg = box(s, dx, 1.85, 6.65, 1.25, fill=PANEL, line=LINE)
pill(s, dx + 0.2, 1.98, "REAL REGISTRY RECORD", fg=ACC, size=10)
text(s, dx + 0.2, 2.35, 6.3, 0.7, [
    [("Verra batch 18453  ·  19,999 units retired 6 Aug 2026", {"bold": True})],
    [("Wind Power Project in Tamil Nadu (VCS 1904)  ·  beneficiary: not disclosed", {"color": MUTED, "size": 13})]], size=16, space_after=2)
hline(s, dx + 1.7, 3.12, dx + 1.7, 3.55, color=MUTED, width=1.5, arrow=True)
hline(s, dx + 4.95, 3.12, dx + 4.95, 3.55, color=MUTED, width=1.5, arrow=True)
for i, (name, units, sub) in enumerate([("Northwind Foods", "10,000 units", "FY2025 claim · anchored"),
                                        ("Helios Apparel", "7,000 units", "FY2025 claim · submitted")]):
    bx = dx + i * 3.4
    box(s, bx, 3.55, 3.25, 1.72, fill=PANEL, line=LINE)
    pill(s, bx + 0.18, 3.72, "SYNTHETIC CLAIMANT", fg=AMB, size=9)
    text(s, bx + 0.18, 4.07, 2.9, 0.4, [[(name, {})], ], size=17, bold=True)
    text(s, bx + 0.18, 4.42, 2.95, 0.8, [[(units, {"bold": True, "color": TEXT, "size": 15})], [(sub, {"color": MUTED, "size": 12})],
                                         [("Matches the registry on its own", {"color": ACC, "size": 12, "bold": True})]], size=14, space_after=3)
box(s, dx, 5.42, 6.65, 1.1, fill=RED_D, line=RED)
text(s, dx + 0.22, 5.43, 6.25, 1.08, [
    [("Totals pass: 17,000 ≤ 19,999 units.", {"color": TEXT, "bold": True})],
    [("But ", {"color": TEXT}), ("4,559 units", {"color": RED, "bold": True, "size": 22}), (" are claimed by both companies.", {"color": TEXT})]],
     size=17, space_after=4, anchor=MSO_ANCHOR.MIDDLE)
source(s, "Registry record: Berkeley Carbon Trading Project, Voluntary Registry Offsets Database v2026-08 (CC BY 4.0). Claimants and their documents are synthetic demo data, "
          "labelled in the app. Context: ICVCM Core Carbon Principle 8, “No double-counting” (icvcm.org).")

# ---------------------------------------------------------------- 3 Why checks miss it
s = new_slide("Why existing checks miss it", "Real registry data defeats the obvious shortcuts", 3, dict(
    time="1:00-1:40 · 40 s",
    say="We measured three reasons on real data. First, overlapping claims rarely quote the same serial string or the same document, so matching "
        "strings or file hashes caught only a third of the double uses in our 270-pair test. Second, serial numbers restart inside every issuance "
        "batch. Across the full Berkeley database, ignoring the batch would create 159,511 false overlaps. Third, 62.7 percent of the retirements "
        "we analyse don't name a beneficiary at all, so you can't solve this by matching company names.",
    why="Covers Problem Relevance and Data Rigor: the difficulty is shown with measured numbers, not asserted.",
    key="The right unit of analysis is units inside a batch, with explicit handling of unknown beneficiaries.",
    next="That leads to the one idea the whole system is built on."))
cards = [
    ("0.333", RED, "recall of serial-string or document-hash matching",
     "Overlapping claims usually quote different serial strings in different files. Test: 270 synthetic claim pairs citing real Verra ranges."),
    ("159,511", AMB, "false “overlaps” if the batch is ignored",
     "Serial numbers restart inside every issuance batch: 11,631 Verra + 147,880 Gold Standard adjacent record pairs in the full database."),
    ("62.7%", BLUE, "of analysed retirements name no beneficiary",
     "23,400 of 37,335 records. Name matching alone cannot attribute units, and an undisclosed buyer is not evidence of misconduct."),
]
cw3 = (CW - 0.5) / 3
for i, (big, col, head, body) in enumerate(cards):
    x = L + i * (cw3 + 0.25)
    box(s, x, 1.9, cw3, 3.95, fill=PANEL, line=LINE)
    box(s, x, 1.9, 0.09, 3.95, fill=col, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + 0.35, 2.1, cw3 - 0.6, 1.0, big, size=50, bold=True, color=col, line=0.9)
    text(s, x + 0.35, 3.15, cw3 - 0.6, 0.8, head, size=18, bold=True, line=1.1)
    text(s, x + 0.35, 4.05, cw3 - 0.6, 1.7, body, size=14, color=MUTED, line=1.2)
box(s, L, 6.05, CW, 0.5, fill=PANEL2, radius=0.2)
text(s, L + 0.3, 6.05, CW - 0.6, 0.5, [[("So OnceOnly works on ", {}), ("units, inside the right batch", {"bold": True, "color": ACC}),
                                       (", and states explicitly who is and isn't identified.", {})]], size=16, anchor=MSO_ANCHOR.MIDDLE)
source(s, "Sources: eval/results/latest.md (270 pairs) · eval/results/registry_audit.json (full VROD, 493,518 rows) · /api/analytics/population/summary (37,335 records).", y=6.72)

# ---------------------------------------------------------------- 4 Core idea
s = new_slide("The core idea", "Turn every claim into unit intervals inside its batch", 4, dict(
    time="1:40-2:20 · 40 s",
    say="A registry serial isn't just an ID. It encodes a contiguous range of units inside one batch. This is Helios's serial: batch 18453, "
        "first unit 896,315,001, last unit 896,322,000. End minus start plus one is exactly 7,000, which matches the quantity Helios states. "
        "Once every claim is an interval inside its batch, double use becomes interval intersection. Below is the real registry retirement and "
        "the two claims drawn to scale. The overlap is exact: 896,315,001 to 896,319,559, 4,559 units. That works even when the two documents quote "
        "completely different serial strings.",
    why="This is the technical insight judges should remember; everything else builds on it.",
    key="Serials are ranges, not strings: double use = interval intersection within one batch.",
    next="Here is the pipeline we built around that idea."))
box(s, L, 1.72, CW, 2.2, fill=PANEL, line=LINE)
text(s, L + 0.25, 1.8, CW - 0.5, 0.35, [[("Serial quoted in Helios’s document:  ", {"color": DIM}),
     ("18453-896315001-896322000-VCS-VCU-1507-VER-IN-1-1904-01092024-31122024-0", {"font": MONO, "color": MUTED})]], size=13)
tiles = [("18453", ACC, 1.55, 24, "batch", "→ VCS:18453"),
         ("896315001", BLUE, 2.55, 24, "first unit", "896,315,001"),
         ("896322000", BLUE, 2.55, 24, "last unit", "896,322,000"),
         ("VCS-VCU-1507-VER-IN-1-1904-…", MUTED, 4.45, 15, "context", "Verra project 1904 · vintage 2024 · India")]
tx_ = L + 0.25
for t, col, w, fsz, lab, sub in tiles:
    box(s, tx_, 2.25, w, 0.62, fill=BG, line=col, lw=1.5, radius=0.12)
    text(s, tx_, 2.25, w, 0.62, t, size=fsz, color=col, bold=col != MUTED, font=MONO, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, tx_ + 0.05, 2.95, w, 0.6, [[(lab, {"bold": True, "color": col})], [(sub, {"color": MUTED, "size": 12})]], size=13, space_after=0)
    tx_ += w + 0.2
box(s, L + 4.55, 3.5, 7.3, 0.34, fill=PANEL2, radius=0.3)
text(s, L + 4.55, 3.5, 7.3, 0.34, [[("Q = last − first + 1 = 7,000 units", {"bold": True, "color": TEXT}), ("  = the quantity Helios states", {"color": ACC})]],
     size=13, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
# ruler to scale
lo, hi = 896_309_560, 896_329_558
x0, x1 = L + 2.55, L + CW - 0.2
def px(u):
    return x0 + (x1 - x0) * (u - lo) / (hi - lo + 1)
rows = [("Registry retirement", "19,999 units · real", lo, hi, None),
        ("Northwind Foods", "10,000 · anchored", 896_309_560, 896_319_559, ACC_D),
        ("Helios Apparel", "7,000 · this claim", 896_315_001, 896_322_000, "outline")]
ys = [4.25, 4.8, 5.35]
for (name, sub, a_, b_, kind), yy in zip(rows, ys):
    text(s, L, yy - 0.04, 2.45, 0.5, [[(name, {"bold": True})], [(sub, {"color": MUTED, "size": 11})]], size=14, align=PP_ALIGN.RIGHT, space_after=0)
    if kind is None:
        box(s, px(a_), yy, px(b_ + 1) - px(a_), 0.36, fill=PANEL2, line=MUTED, shape=MSO_SHAPE.RECTANGLE)
    elif kind == "outline":
        box(s, px(a_), yy, px(b_ + 1) - px(a_), 0.36, fill=None, line=TEXT, shape=MSO_SHAPE.RECTANGLE, lw=1.5)
    else:
        box(s, px(a_), yy, px(b_ + 1) - px(a_), 0.36, fill=kind, shape=MSO_SHAPE.RECTANGLE)
ov_a, ov_b = 896_315_001, 896_319_559
hatch(s, px(ov_a), ys[1], px(ov_b + 1) - px(ov_a), 0.36)
hatch(s, px(ov_a), ys[2], px(ov_b + 1) - px(ov_a), 0.36)
for u in (ov_a, ov_b + 1):
    hline(s, px(u), 4.15, px(u), 5.95, color=RED, width=1, dash=True)
text(s, px(ov_a) - 1.0, 5.98, 2.0, 0.3, "896,315,001", size=11, color=RED, font=MONO, align=PP_ALIGN.CENTER, bold=True)
text(s, px(ov_b + 1) - 1.0, 5.98, 2.0, 0.3, "896,319,559", size=11, color=RED, font=MONO, align=PP_ALIGN.CENTER, bold=True)
text(s, px(ov_b + 1) + 1.15, 5.9, 4.2, 0.5, [[("4,559 units in both claims", {"bold": True, "color": RED})],
                                            [("65.1% of Helios’s claim", {"color": MUTED, "size": 12})]], size=16, space_after=0)
source(s, "Drawn to scale from the live API (/api/claims/2/reconciliation, /api/reference/lookup). Overlap is computed on closed intervals: Q = e − s + 1.", y=6.72)

# ---------------------------------------------------------------- 5 Pipeline
s = new_slide("What we built", "One pipeline: claim document in, explained result out", 5, dict(
    time="2:20-2:55 · 35 s",
    say="OnceOnly is a working full-stack system. It reads the evidence and fingerprints every document. It reconciles each serial against real "
        "registry retirements. Then come the three stages I built for DATANOVA, highlighted here: entity resolution with allocation classification, "
        "population, timing and cross-registry analytics, and a unified assessment of 16 deterministic rules. Finally, accepted claims are anchored "
        "on a smart contract that refuses overlapping units, and anyone can verify them. The split matters: the analytics stay off-chain where "
        "they can be explained; only one invariant lives on-chain.",
    why="Technical Implementation is 25% of the score; this shows breadth and is honest about what was new for DATANOVA.",
    key="Off-chain: explainable analysis. On-chain: one enforced invariant.",
    next="Let me show you this running in the product."))
steps = [("01", "Read", "SHA-256 every document; deterministic serial parser keeps provenance for every block", False),
         ("02", "Reconcile", "Serials become unit intervals, matched to real Verra and Gold Standard retirements", False),
         ("03", "Resolve and classify", "Entity resolution plus 8 allocation classes: split, broker, related, undisclosed, conflict", True),
         ("04", "Add context", "Disclosure, concentration, fragmentation, timing and cross-registry analytics", True),
         ("05", "Assess", "16 deterministic rules across 6 scopes; evidence, counterevidence, next step", True),
         ("06", "Anchor and verify", "ClaimLedger contract refuses overlapping units; 7 verification checks", False)]
sw = (CW - 5 * 0.16) / 6
for i, (n, head, body, new) in enumerate(steps):
    x = L + i * (sw + 0.16)
    box(s, x, 1.75, sw, 2.9, fill=PANEL2 if new else PANEL, line=ACC if new else LINE, lw=1.5 if new else 1)
    text(s, x + 0.18, 1.88, sw - 0.3, 0.3, n, size=13, color=ACC if new else DIM, bold=True, font=MONO)
    text(s, x + 0.18, 2.2, sw - 0.3, 0.7, head, size=17, bold=True, line=1.0)
    text(s, x + 0.18, 2.9, sw - 0.3, 1.7, body, size=13, color=MUTED, line=1.12)
    if i < 5:
        hline(s, x + sw + 0.01, 3.27, x + sw + 0.15, 3.27, color=MUTED, width=1.25, arrow=True)
box(s, L, 4.78, 0.22, 0.22, fill=PANEL2, line=ACC, radius=0.2, lw=1.5)
text(s, L + 0.32, 4.74, 12, 0.3, "Built for DATANOVA. Steps 01, 02 and 06 extend my earlier claim-ledger core (IEEE ClimateChain hackathon, Oct 2026).",
     size=12, color=MUTED)
bands = [("OFF-CHAIN  ·  explainable, replaceable", "Documents, extraction, reconciliation, analytics, findings, evidence index", BLUE),
         ("ON-CHAIN  ·  ClaimLedger.sol", "Unit ranges per batch, evidence and report hashes, salted claimant commitment, status. Rejects overlaps.", ACC)]
for i, (h, b, col) in enumerate(bands):
    x = L + i * (CW / 2 + 0.1)
    w = CW / 2 - 0.1
    box(s, x, 5.25, w, 1.25, fill=PANEL, line=col)
    text(s, x + 0.25, 5.35, w - 0.5, 1.05, [[(h, {"bold": True, "color": col, "size": 13, "spacing": 100})], [(b, {})]], size=15, space_after=6)
source(s, "Stack: Python 3.12 · FastAPI · SQLite · rapidfuzz · web3.py · Solidity 0.8.24 / Hardhat · React 19 · TypeScript · Vite · Tailwind 4 · bespoke SVG charts · Docker.", y=6.72)

# ---------------------------------------------------------------- 6 Product
s = new_slide("In the product", "4,559 units already back another claim. Blocked.", 6, dict(
    time="2:55-3:40 · 45 s",
    say="This is the live application, not a mock-up. On Helios's claim page, the Ruler draws the real registry record and both claims on the same "
        "unit axis. One: the registry record is real, a Verra wind project in Tamil Nadu. Two: the overlap is computed exactly, 4,559 units, which "
        "is 65 percent of Helios's claim. Three: anchoring is blocked by the double-use rule, and if you send the registration to the chain anyway, "
        "the contract itself reverts with a RangeOverlap error. Note the wording: potential double use, for review. It doesn't say which company is right.",
    why="Proves a working product; ties the abstract idea to a real screen judges can open themselves.",
    key="It works end to end on a real record, and the contract enforces the same rule as the UI.",
    next="But an overlap on its own isn't enough to call something a problem."))
ih = 4.8
iw = ih * 1750 / 1264
picture(s, ASSETS / "ruler.jpg", L, 1.75, h=ih)
# badges on the screenshot (positions mapped from the source crop)
def on_img(px_, py_):
    return L + iw * (px_ - 194) / 1750, 1.75 + ih * (py_ - 173) / 1264
for n, (ox, oy) in enumerate([(250, 920), (660, 872), (1405, 724)], start=1):
    bx, by = on_img(ox, oy)
    num_badge(s, bx - 0.21, by - 0.21, n, d=0.42, fill=ACC, fg=BG)
callouts = [("Real registry record", "Verra batch 18453, one retirement of 19,999 units (Berkeley VROD 2026-08)."),
            ("Exact overlap", "Units 896,315,001–896,319,559: 4,559 units, 65.1% of this claim, shared with an anchored claim."),
            ("Blocked twice", "Anchoring blocked by rule DUP-001. Sent to the chain anyway, ClaimLedger reverts with RangeOverlap.")]
cx = L + iw + 0.35
for i, (h, b) in enumerate(callouts):
    y = 1.8 + i * 1.38
    num_badge(s, cx, y, i + 1)
    text(s, cx + 0.55, y - 0.02, R - cx - 0.55, 1.4, [[(h, {"bold": True, "size": 17})], [(b, {"color": MUTED})]], size=14, space_after=4, line=1.15)
box(s, cx, 5.95, R - cx, 0.6, fill=PANEL2, radius=0.2)
text(s, cx + 0.15, 5.95, R - cx - 0.3, 0.6, "A flag for review. It does not say which claim is right.", size=13, color=AMB, anchor=MSO_ANCHOR.MIDDLE)
source(s, "Screenshot of the live demo (onceonly-demo.onrender.com/claims/2), cropped. Claimants are synthetic; the chain is a local Hardhat chain inside the demo instance.", y=6.72)

# ---------------------------------------------------------------- 7 Overlap is not conflict
s = new_slide("Allocation-aware reconciliation", "An overlap is a question, not a verdict", 7, dict(
    time="3:40-4:25 · 45 s",
    say="Brokers and corporate groups share units legitimately all the time, so a naive overlap check would accuse innocent parties. "
        "OnceOnly combines the interval geometry with who the claimants are. Distinct ranges from one retirement are a legitimate split. "
        "A broker retiring on behalf of a disclosed client is an intermediary attribution. A parent and a subsidiary are related claimants, "
        "never treated as the same entity. If the beneficiary is undisclosed, we say it's unresolved instead of guessing. Only unrelated "
        "companies sharing units become an allocation conflict. Underneath sits entity resolution: legal-suffix normalisation, 'on behalf of' "
        "parsing and explainable matching. On our 124-pair curated benchmark it scores an F1 of 0.982 with zero false positives, against 0.263 for "
        "exact string matching. That benchmark is curated, so it shows the logic works as designed, not real-world accuracy.",
    why="Innovation and Analytical Rigor: this is what separates OnceOnly from a simple interval checker.",
    key="Geometry plus relationships, with 'unresolved' as an explicit honest answer.",
    next="Every one of these signals has to explain itself, which is the next layer."))
rows7 = [["Situation in one batch", "Shared units?", "Classified as"],
         ["Distinct ranges, different claimants", "No", [("LEGITIMATE_SPLIT", {"font": MONO, "color": ACC, "bold": True, "size": 12})]],
         ["Broker for a disclosed client", "Yes", [("INTERMEDIARY_ATTRIBUTION", {"font": MONO, "color": BLUE, "bold": True, "size": 12})]],
         ["Parent and subsidiary", "Yes", [("SAME_UNITS_RELATED_CLAIMANTS", {"font": MONO, "color": BLUE, "bold": True, "size": 12})]],
         ["Same claimant filed twice", "Yes", [("SAME_UNITS_SAME_CLAIMANT", {"font": MONO, "color": AMB, "bold": True, "size": 12})]],
         ["Beneficiary undisclosed", "Either", [("UNRESOLVED_BENEFICIARY", {"font": MONO, "color": AMB, "bold": True, "size": 12})]],
         ["Unrelated claimants", "Yes", [("ALLOCATION_CONFLICT", {"font": MONO, "color": RED, "bold": True, "size": 12})]],
         ["Same numbers, other batch", "No", [("CROSS_NAMESPACE", {"font": MONO, "color": MUTED, "bold": True, "size": 12})]]]
table(s, L, 1.75, 7.0, rows7, [2.95, 0.95, 3.1], row_h=0.52, size=14)
text(s, L, 6.3, 7.0, 0.35, "Plus 6 geometric overlap types. A relationship is never treated as identity.",
     size=12, color=MUTED)
# ER chart
ex = L + 7.35
box(s, ex, 1.85, R - ex, 4.7, fill=PANEL, line=LINE)
text(s, ex + 0.25, 1.98, R - ex - 0.5, 0.9, [[("Entity resolution underneath", {"bold": True, "size": 17})],
     [("Legal-suffix normalisation, “on behalf of” parsing, blocking (99.1% of pair comparisons pruned), explainable matching", {"color": MUTED, "size": 12})]],
     size=14, space_after=4)
cd = CategoryChartData()
cd.categories = ["Exact string", "Token match ≥ 85", "OnceOnly"]
cd.add_series("F1 score", (0.263, 0.629, 0.982))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(ex + 0.15), Inches(3.05), Inches(R - ex - 0.3), Inches(2.4), cd)
ch = gf.chart
style_chart(ch, legend=False)
style_axes(ch, value_fmt="0.0", gridlines=False, show_value_axis=False)
ch.value_axis.maximum_scale = 1.15
ch.value_axis.minimum_scale = 0
pl = ch.plots[0]
pl.gap_width = 55
pl.has_data_labels = True
pl.data_labels.number_format = "0.000"
pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.data_labels.font.size = Pt(14)
pl.data_labels.font.bold = True
pl.data_labels.font.color.rgb = TEXT
ser = pl.series[0]
for i, col in enumerate([DIM, DIM, ACC]):
    pt = ser.points[i]
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = col
text(s, ex + 0.25, 5.45, R - ex - 0.5, 1.05, [[("F1 on 124 curated name pairs. OnceOnly: precision 1.000, recall 0.964, 0 false positives.", {"color": TEXT, "size": 12})],
     [("Curated by the author: shows the method works as designed, not real-world accuracy.", {"color": AMB, "size": 12})]], size=12, space_after=3)
source(s, "Sources: backend/app/reconciliation/engine.py; eval/results/entity_resolution_results.md (124 pairs, 2026-11-10).", y=6.72)

# ---------------------------------------------------------------- 8 Explainable assessment
s = new_slide("Explainable assessment", "Every signal shows its rule, its evidence and its limits", 8, dict(
    time="4:25-5:00 · 35 s",
    say="On top of that, a unified assessment runs 16 versioned, deterministic rules across six scopes: a batch, a project, a claim, an entity, a "
        "cross-registry pair, or an ad-hoc range. Every finding carries its rule ID, the threshold, the metrics it evaluated, supporting evidence, "
        "counterevidence, missing information and a recommended next step. Signals that come from the same underlying records are grouped, so three "
        "findings here count as two independent signals, not three. And the outputs are review priorities such as Review Recommended, never a fraud verdict. "
        "No model is trained here; this is deterministic and auditable by design.",
    why="Explainability is a differentiator for investigators and directly answers 'is this a black box?'.",
    key="Deterministic, versioned rules; correlated signals can't inflate priority; no fraud verdicts.",
    next="The same engine also describes the market population the claim sits in, on real data."))
aw = 7.2
ah = aw * 1069 / 1728
picture(s, ASSETS / "assessment.jpg", L, 1.85, w=aw)
text(s, L, 1.85 + ah + 0.12, aw, 0.6, "Live assessment of Helios’s claim: 3 triggered rules grouped into 2 independent signals.", size=12, color=MUTED)
rx = L + aw + 0.35
rw_ = R - rx
box(s, rx, 1.85, rw_, 3.55, fill=PANEL, line=LINE)
text(s, rx + 0.25, 1.97, rw_ - 0.5, 0.35, "EVERY FINDING CARRIES", size=12, color=ACC, bold=True, spacing=150)
items = ["Rule ID and thresholds applied", "Metrics it evaluated", "Supporting evidence", "Counterevidence, kept separate",
         "Missing information", "A recommended next step"]
for i, it in enumerate(items):
    yy = 2.42 + i * 0.47
    box(s, rx + 0.28, yy + 0.09, 0.13, 0.13, fill=ACC, radius=0.5)
    text(s, rx + 0.55, yy, rw_ - 0.8, 0.4, it, size=15)
stats = [("16", "rules"), ("6", "scopes"), ("5", "review statuses")]
sw3 = (rw_ - 0.3) / 3
for i, (n, l) in enumerate(stats):
    x = rx + i * (sw3 + 0.15)
    box(s, x, 5.55, sw3, 1.0, fill=PANEL2)
    text(s, x, 5.58, sw3, 0.55, n, size=28, bold=True, color=ACC, align=PP_ALIGN.CENTER)
    text(s, x, 6.12, sw3, 0.35, l, size=12, color=MUTED, align=PP_ALIGN.CENTER)
source(s, "Statuses: NO_MATERIAL_SIGNAL · REVIEW_RECOMMENDED · ELEVATED_REVIEW_PRIORITY · INSUFFICIENT_EVIDENCE · CONFLICTING_EVIDENCE. Ruleset 2026.1.0-STAGE4.", y=6.72)

# ---------------------------------------------------------------- 9 Real data
s = new_slide("What the real data shows", "37,335 real retirements: most name no beneficiary", 9, dict(
    time="5:00-5:40 · 40 s",
    say="Everything you've seen runs on a committed subset of the real Berkeley database: 22 Verra and Gold Standard projects, 725 batches, "
        "37,335 retirements and 87.7 million tonnes, from 2010 to 2026. The headline is disclosure. 62.7 percent of retirement records, about 60 "
        "percent of the volume, don't name who the credits were retired for. That's exactly the gap where double claiming can hide, and it's why "
        "'unresolved' is a first-class answer in OnceOnly. Among the disclosed volume, concentration is low: an HHI of 246. Sizes vary enormously "
        "across the portfolio, with a pooled Gini of 0.96, but much less inside a typical batch. And timing analysis flags 51 of 192 months as "
        "retirement bursts. These describe this sample, not the global market, and they're signals, not findings.",
    why="Data and Analytical Rigor (15%): real data, defined populations, and careful interpretation.",
    key="Real data, defined population, honest interpretation: disclosure is the structural blind spot.",
    next="Now, where does the blockchain come in, and where does it not?"))
text(s, L, 1.68, CW, 0.35, "VROD v2026-08 subset  ·  22 projects (16 Verra, 6 Gold Standard)  ·  725 batches  ·  87,668,330 t  ·  Oct 2010 – Sep 2026",
     size=13, color=MUTED)
cd = CategoryChartData()
cd.categories = ["Share of tonnes", "Share of records"]
cd.add_series("Beneficiary disclosed", (40.12, 37.32))
cd.add_series("Explicitly undisclosed", (59.70, 62.66))
cd.add_series("Invalid placeholder", (0.18, 0.02))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(L), Inches(2.2), Inches(7.3), Inches(3.05), cd)
ch = gf.chart
style_chart(ch, size=12)
style_axes(ch, value_fmt='0"%"', gridlines=True)
ch.value_axis.maximum_scale = 100
ch.value_axis.minimum_scale = 0
ch.value_axis.major_unit = 25
pl = ch.plots[0]
pl.gap_width = 45
pl.overlap = 100
for i, col in enumerate([ACC, BLUE, AMB]):
    se = pl.series[i]
    se.format.fill.solid()
    se.format.fill.fore_color.rgb = col
    if i < 2:
        se.data_labels.show_value = True
        se.data_labels.number_format = '0.0"%"'
        se.data_labels.number_format_is_linked = False
        se.data_labels.font.size = Pt(15)
        se.data_labels.font.bold = True
        se.data_labels.font.color.rgb = BG
        se.data_labels.position = XL_LABEL_POSITION.CENTER
text(s, L, 5.35, 7.3, 0.9, [[("Measured: ", {"bold": True, "color": TEXT}), ("beneficiary disclosure on 37,335 retirement records / 87,668,330 t. "
     "Disclosed 13,935 records; explicitly undisclosed 23,393; invalid placeholder 7.", {})],
     [("Not disclosing is not misconduct. It is where claims cannot be attributed.", {"color": AMB})]], size=12, color=MUTED, space_after=4)
mx = L + 7.6
mw = R - mx
mets = [("245.6", "HHI over disclosed volume", "9,931 disclosed labels; top three hold 23.1%. Low concentration.", ACC),
        ("0.96 / 0.49", "Pooled vs within-batch Gini", "Sizes vary hugely across the portfolio, far less inside a typical batch.", BLUE),
        ("51 / 192", "Monthly burst periods", "Leave-one-out MAD, k = 3, 12-month baseline. A reason to look, not proof.", AMB)]
for i, (big, h, b, col) in enumerate(mets):
    y = 2.2 + i * 1.47
    box(s, mx, y, mw, 1.35, fill=PANEL, line=LINE)
    box(s, mx, y, 0.08, 1.35, fill=col, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    text(s, mx + 0.28, y + 0.08, mw - 0.4, 0.5, [[(big, {"bold": True, "color": col, "size": 24}), ("   " + h, {"bold": True, "size": 13})]], size=13)
    text(s, mx + 0.28, y + 0.62, mw - 0.45, 0.7, b, size=12, color=MUTED, line=1.15)
source(s, "Describes this 22-project subset, not the global market. Live API /api/analytics/population/summary and /temporal/bursts; pinned by regression tests.", y=6.72)

# ---------------------------------------------------------------- 10 Blockchain
s = new_slide("The role of the blockchain", "One invariant on-chain. Everything else explainable.", 10, dict(
    time="5:40-6:20 · 40 s",
    say="We use a smart contract for one specific job. ClaimLedger stores each claim's unit ranges per batch, the evidence and report hashes, a salted "
        "claimant commitment and the status, and it refuses any registration that overlaps an active claim, even if someone bypasses our own interface. "
        "Documents and analytics never go on-chain. To keep that check cheap, ranges are kept in a sorted linked list and the client supplies a "
        "predecessor hint, so registration gas stays flat at about 301,000 whether a batch holds 10 or 200 ranges. A naive linear scan reached 833,000. "
        "To be precise about trust: in this prototype it's a local Hardhat chain with one trusted registrar. A hash match shows a document hasn't "
        "changed; it doesn't prove the document is true.",
    why="Pre-empts the most common skeptical question about blockchain in hackathon projects.",
    key="Blockchain = neutral ordering + a non-bypassable no-overlap rule. Not proof of truth.",
    next="So how do we know any of this actually works?"))
cols = [("ON-CHAIN", ACC, ["Unit ranges per (registry, batch)", "Evidence and report hashes", "Salted claimant commitment and status",
                           "Rejects overlaps: RangeOverlap"]),
        ("OFF-CHAIN", BLUE, ["Documents and extraction", "Reconciliation and analytics", "Findings and evidence index"]),
        ("NOT ESTABLISHED", RED, ["That a document is true", "Which overlapping claim is legitimate", "Legal identity of claimants"])]
for i, (h, col, its) in enumerate(cols):
    y = 1.85 + i * 1.6
    hgt = 1.48
    box(s, L, y, 5.6, hgt, fill=PANEL, line=col)
    text(s, L + 0.25, y + 0.1, 5.2, 0.3, h, size=12, color=col, bold=True, spacing=150)
    text(s, L + 0.25, y + 0.42, 5.2, hgt - 0.45, ["–  " + t for t in its], size=13, space_after=2, line=1.05)
gx = L + 5.9
gw = R - gx
cd = CategoryChartData()
cd.categories = ["0", "10", "50", "200"]
cd.add_series("Hinted sorted list (deployed)", (333078, 301452, 301452, 301452))
cd.add_series("Linear scan (v0)", (304108, 314288, 423408, 832608))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(gx), Inches(1.85), Inches(gw), Inches(3.4), cd)
ch = gf.chart
style_chart(ch, size=12)
style_axes(ch, value_fmt='#,##0,"k"')
pl = ch.plots[0]
pl.gap_width = 60
pl.overlap = -10
for i, col in enumerate([ACC, DIM]):
    pl.series[i].format.fill.solid()
    pl.series[i].format.fill.fore_color.rgb = col
lab = pl.series[1].points[3].data_label
lab.has_text_frame = True
lab.text_frame.text = "832,608"
lab.position = XL_LABEL_POSITION.OUTSIDE_END
lab.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
lab.text_frame.paragraphs[0].runs[0].font.bold = True
lab.text_frame.paragraphs[0].runs[0].font.color.rgb = TEXT
text(s, gx, 5.25, gw, 0.4, "Gas per registration: deployed design flat at 301,452 from 10 to 200 existing ranges", size=12, color=MUTED, align=PP_ALIGN.CENTER)
box(s, gx, 5.7, gw, 0.85, fill=PANEL2)
text(s, gx + 0.2, 5.7, gw - 0.4, 0.85, [[("Public verification reports 7 checks separately: ", {"bold": True}),
     ("network, contract bytecode, on-chain record, ranges, evidence commitment, document, claimant. A database match never counts as on-chain proof.", {"color": MUTED})]],
     size=12, anchor=MSO_ANCHOR.MIDDLE, line=1.1)
source(s, "Trust boundary: local Hardhat chain (ID 31337) in the demo instance, one trusted registrar key, claimants don’t sign; not a public network. Source: eval/results/gas.json.", y=6.72)

# ---------------------------------------------------------------- 11 Validation
s = new_slide("Validation", "Tested for what each test can actually show", 11, dict(
    time="6:20-7:00 · 40 s",
    say="We validated each layer and labelled what each test can and can't show. On 270 synthetic claim pairs built on real Verra ranges, the engine "
        "and the contract both catch every double use and agree on every case, while hash or string matching catches only a third, and a batch-blind "
        "interval check produces false alarms. Because the ground truth there uses our own interval definition, it shows the logic is correct, not how "
        "common double claiming is. Entity resolution and allocation classification were tested on curated cases, including held-out ones. The engineering "
        "is tested too: 274 backend tests and 24 contract tests pass today, plus 45 browser tests and a 13-step end-to-end run from the release QA.",
    why="Technical Implementation and Rigor: evidence, with the honesty that makes it believable.",
    key="Measured against baselines, with the limits of each benchmark stated up front.",
    next="Which brings me to what this can't do yet, and where it goes next."))
v_rows = [["Test", "Data", "OnceOnly", "Baseline", "What it shows / does not"],
          ["Double use", "270 synthetic pairs on real Verra ranges", [("P 1.000 · R 1.000", {"color": ACC, "bold": True})],
           "Hash / string: R 0.333\nBatch-blind: P 0.857", "Logic is correct. Circular ground truth: not real-world prevalence"],
          ["Contract replay", "Same 270 pairs, local chain", [("100% agreement", {"color": ACC, "bold": True})], "–", "Contract enforces the same rule as the engine"],
          ["Entity resolution", "124 curated name pairs", [("F1 0.982 · 0 FP", {"color": ACC, "bold": True})], "Exact F1 0.263\nToken F1 0.629",
           "Curated by the author. 3 misses: parent/subsidiary"],
          ["Allocation classes", "36 curated scenarios (11 held out)", [("36 / 36", {"color": ACC, "bold": True})], "Naive interval: detects overlaps, no classes",
           "Value is the classification, not detection"],
          ["Serial extraction", "60 synthetic snippets, 8 layouts", [("100% exact", {"color": ACC, "bold": True})], "–", "In-sample. AI extraction not measured"]]
table(s, L, 1.75, CW, v_rows, [1.9, 2.75, 1.95, 2.45, 3.083], row_h=0.66, size=13)
eng = [("274", "backend tests", "pass · re-run 21 Nov"), ("24", "contract tests", "pass · re-run 21 Nov"),
       ("45", "browser tests", "incl. WCAG · QA 10 Nov"), ("13/13", "end-to-end steps", "pass · QA 10 Nov")]
ew = (CW - 0.45) / 4
for i, (n, l, d) in enumerate(eng):
    x = L + i * (ew + 0.15)
    box(s, x, 5.85, ew, 0.78, fill=PANEL2)
    text(s, x + 0.2, 5.87, 1.15, 0.74, n, size=22, bold=True, color=ACC, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 1.3, 5.87, ew - 1.4, 0.74, [[(l, {"color": TEXT})], [(d, {"size": 10, "color": DIM})]], size=12, space_after=0, anchor=MSO_ANCHOR.MIDDLE)
source(s, "Sources: eval/results/*.md; docs/FINAL_RELEASE_QA_REPORT.md. None of these benchmarks measures real-world fraud-detection accuracy.", y=6.72)

# ---------------------------------------------------------------- 12 Limits and impact
s = new_slide("Limits and path to impact", "Honest about today, concrete about what comes next", 12, dict(
    time="7:00-7:35 · 35 s",
    say="Here's what OnceOnly doesn't do yet. The chain is local with a trusted registrar. The registry data is a static August 2026 snapshot, and "
        "the analytics cover 22 projects. The benchmarks are synthetic or curated, the optional AI extraction isn't evaluated, and we have not "
        "measured how often double claiming happens in the wild. The people it helps are buyers checking a claim before they rely on it, auditors who "
        "need a reviewable trail, and registries and researchers who want claim-level transparency. Next steps: claimant-signed registrations on a "
        "public testnet, per-document Merkle proofs, a refresh pipeline for the full registry, and a pilot on real published claims to measure prevalence.",
    why="Impact and Feasibility (15%) and credibility: stating limits first makes the impact claims believable.",
    key="Clear limits, clear users, a concrete roadmap.",
    next="To close."))
cols = [("LIMITS TODAY", AMB, ["Local chain, trusted registrar; claimants don’t sign yet", "Static registry snapshot (to 31 Aug 2026)",
                               "Analytics on a 22-project subset", "Benchmarks synthetic or curated", "AI extraction implemented, not evaluated",
                               "Real-world prevalence not measured"]),
        ("WHO IT HELPS", BLUE, ["Credit buyers and sustainability teams checking a claim before relying on it",
                                "Auditors and assurance providers who need a reviewable trail",
                                "Registries, standards bodies and researchers studying claim-level transparency"]),
        ("NEXT", ACC, ["Claimant-signed registrations (EIP-712) on a public testnet", "Per-document Merkle commitments and proofs",
                       "Full-registry refresh pipeline; more registries", "Measure AI extraction on real documents",
                       "Pilot on published claims, with consent, to measure prevalence"])]
c3 = (CW - 0.4) / 3
for i, (h, col, its) in enumerate(cols):
    x = L + i * (c3 + 0.2)
    box(s, x, 1.8, c3, 4.1, fill=PANEL, line=LINE)
    box(s, x, 1.8, c3, 0.08, fill=col, radius=0.0, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + 0.25, 2.02, c3 - 0.5, 0.3, h, size=13, color=col, bold=True, spacing=150)
    text(s, x + 0.25, 2.45, c3 - 0.45, 3.45, ["–  " + t for t in its], size=15, space_after=8, line=1.1)
box(s, L, 6.08, CW, 0.5, fill=PANEL2, radius=0.3)
text(s, L + 0.25, 6.08, CW - 0.5, 0.5, [[("Scales today: ", {"bold": True, "color": ACC}),
     ("all 493,518 full-database rows parse into unit ranges; on-chain check cost is flat from 10 to 200 ranges per batch.", {})]],
     size=12, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 13 Close
s = new_slide(number=13, notes=dict(
    time="7:35-7:50 · 15 s",
    say="So: work on units, not strings. Treat an overlap as a question, not a verdict. And put one invariant on-chain while keeping everything else "
        "explainable. Every retired tonne, claimed once. The demo is live, and the code and evidence are public. Thank you, I'm happy to take questions, "
        "or to walk through the live demo.",
    why="Leaves judges with three memorable takeaways and the links.",
    key="Units, not strings. Questions, not verdicts. One invariant on-chain.",
    next=None))
text(s, L, 0.9, CW, 1.2, "Every retired tonne, claimed once.", size=46, bold=True, color=TEXT)
take = [("Units, not strings", "Serials become intervals inside their batch, so overlaps are exact even across different documents."),
        ("Questions, not verdicts", "Overlaps are classified, explained and prioritised for review, with ‘unresolved’ as an honest answer."),
        ("One invariant on-chain", "The contract refuses overlapping units; everything else stays explainable off-chain.")]
for i, (h, b) in enumerate(take):
    x = L + i * (c3 + 0.2)
    box(s, x, 2.45, c3, 2.2, fill=PANEL, line=LINE)
    text(s, x + 0.3, 2.6, 0.6, 0.6, f"0{i + 1}", size=16, color=ACC, bold=True, font=MONO)
    text(s, x + 0.3, 3.0, c3 - 0.6, 0.5, h, size=21, bold=True)
    text(s, x + 0.3, 3.55, c3 - 0.6, 1.1, b, size=14, color=MUTED, line=1.15)
links = [("Live demo", "onceonly-demo.onrender.com", "https://onceonly-demo.onrender.com"),
         ("Code and evidence", "github.com/Sidd927/OnceOnly-DataNova", "https://github.com/Sidd927/OnceOnly-DataNova"),
         ("Deck, Q&A and audit", "…/OnceOnly-DataNova › submission/datanova_final",
          "https://github.com/Sidd927/OnceOnly-DataNova/tree/datanova/phase-0-baseline/submission/datanova_final")]
for i, (k, v, url) in enumerate(links):
    y = 5.0 + i * 0.45
    text(s, L, y, 3.2, 0.4, k, size=14, color=MUTED)
    tb = text(s, L + 3.2, y, 9, 0.4, v, size=14, color=TEXT, font=MONO)
    run = tb.text_frame.paragraphs[0].runs[0]
    run.hyperlink.address = url
    run.font.color.rgb = TEXT
text(s, L, 6.45, CW, 0.4, "Free hosting: the first visit after idle can take about a minute to wake. Registry data: Berkeley Carbon Trading Project, VROD v2026-08, CC BY 4.0.",
     size=11, color=DIM)

# ================================================================ APPENDIX
def appendix(label, title, notes_say):
    return new_slide(f"Appendix {label}", title, label, dict(time="backup", say=notes_say, why="Backup for questions.", key=title, next=None))

# ---------------------------------------------------------------- A1 Architecture
s = appendix("A1", "Architecture", "Use this if asked how the system is put together: React front end, FastAPI backend with separate analytical modules, a read-only registry reference DB, and the ClaimLedger contract on a local chain.")
cols = [("DATA", ["Berkeley VROD v2026-08 (real), CC BY 4.0", "Full: 493,518 rows (local build)", "Committed subset: 38,004 rows, 22 projects",
                  "Non-destructive normalisation: raw values kept", "Synthetic claim documents (labelled)", "Curated benchmarks (124 + 36 cases)"]),
        ("FASTAPI BACKEND  ·  PYTHON 3.12", ["Claim pipeline: serials → rules → findings → report hash", "entity_resolution/ (2A)",
                                                   "reconciliation/ interval algebra (2B)", "analytics/ concentration, fragmentation, temporal, cross-registry",
                                                   "risk_assessment/ 16 rules, 6 scopes", "Verification service; content-addressed evidence store; SQLite"]),
        ("CHAIN AND UI", ["ClaimLedger.sol (Solidity 0.8.24)", "Ranges keyed by keccak(registry:batch)", "Hinted sorted linked list; RangeOverlap revert",
                          "Local Hardhat chain 31337 via web3.py", "React 19 UI: Claims, Cross-Registry, Observatory, Assessment, Verify, Evidence",
                          "One Docker image on Render (public demo, writes disabled)"])]
c3 = (CW - 0.4) / 3
for i, (h, its) in enumerate(cols):
    x = L + i * (c3 + 0.2)
    box(s, x, 1.85, c3, 4.6, fill=PANEL2 if i == 1 else PANEL, line=ACC if i == 1 else LINE)
    text(s, x + 0.25, 2.0, c3 - 0.5, 0.3, h, size=12, color=ACC, bold=True, spacing=120)
    text(s, x + 0.25, 2.45, c3 - 0.45, 3.9, ["–  " + t for t in its], size=14, space_after=9, line=1.1)
    if i < 2:
        hline(s, x + c3 + 0.02, 4.15, x + c3 + 0.18, 4.15, color=MUTED, width=1.5, arrow=True)
source(s, "Sources: backend/app/main.py (API), backend/app/*, contracts/contracts/ClaimLedger.sol, frontend/src/App.tsx, Dockerfile, render.yaml.", y=6.68)

# ---------------------------------------------------------------- A2 Rules
s = appendix("A2", "The 16 assessment rules", "Use this if asked what the rules are. All 16 are deterministic and versioned; each is listed in GET /api/analytics/assessment/rules.")
rules = [("Reconciliation", ["REC-001  Exact serial unit overlap", "REC-002  Partial serial unit overlap", "REC-003  Contained serial unit overlap",
                             "REC-004  Legitimate split allocation"]),
         ("Entity", ["ENT-001  Intermediary attribution ambiguity", "ENT-002  Corporate hierarchy / subsidiary variation"]),
         ("Concentration", ["CON-001  Single-beneficiary portfolio dominance", "CON-002  High beneficiary concentration", "CON-003  Material undisclosed beneficiary share"]),
         ("Fragmentation", ["FRG-001  Anomalous micro-claim fragmentation", "FRG-002  High batch sizing inequality"]),
         ("Temporal", ["TMP-001  Anomalous retirement volume burst", "TMP-002  Prolonged project inactivity gap"]),
         ("Cross-registry", ["XREG-001  Strong cross-registry attribute correlation", "XREG-002  Cross-registry identifier collision",
                             "XREG-003  Contradictory cross-registry attributes"])]
for i, (fam, rs) in enumerate(rules):
    col_, row_ = i % 3, i // 3
    x = L + col_ * (c3 + 0.2)
    y = 1.85 + row_ * 2.35
    box(s, x, y, c3, 2.2, fill=PANEL, line=LINE)
    text(s, x + 0.25, y + 0.12, c3 - 0.5, 0.3, fam.upper(), size=12, color=ACC, bold=True, spacing=120)
    text(s, x + 0.25, y + 0.5, c3 - 0.4, 1.7, [[(r.split("  ")[0], {"font": MONO, "bold": True, "color": TEXT, "size": 12}),
                                               ("  " + r.split("  ")[1], {"color": MUTED, "size": 13})] for r in rs], size=13, space_after=6)
source(s, "Scopes: BATCH, PROJECT, CLAIM, ENTITY, CROSS_REGISTRY, AD_HOC. Dependency groups stop correlated rules from inflating priority. "
          "Rule IDs carry the prefix RULE-. Source: backend/app/analytics/risk_assessment/rules.py.", y=6.68)

# ---------------------------------------------------------------- A3 Data and metrics
s = appendix("A3", "Data provenance and population metrics", "Use this for data questions. Every value is computed by the backend and pinned by a regression test; the earlier Sprint 3.4 figures (HHI 215.17 etc.) were wrong and were corrected by erratum.")
d_rows = [["Item", "Value", "Notes"],
          ["Source", "Berkeley VROD v2026-08, CC BY 4.0", "Records through 31 Aug 2026; registry rights unverified"],
          ["Full database", "493,518 rows", "307,416 Verra + 166,478 GS retirements; 19,624 Verra issuances. All parse to quantity-consistent ranges"],
          ["Committed subset", "38,004 rows", "37,335 retirements + 669 issuances; 22 projects; SHA-256 809bb934…114c018"],
          ["Population", "37,335 records · 87,668,330 t · 725 batches", "Issuances excluded from retirement denominators"],
          ["Disclosure", "13,935 disclosed · 23,393 undisclosed · 7 placeholder", "Unresolved: 23,400 records (62.7%), 59.9% of tonnes"],
          ["Concentration", "HHI 245.64 · entropy 7.5165 bits · equitability 0.5661", "Over disclosed volume, 9,931 labels; Telstra 3,766,034 t (10.7%); top three 23.13%"],
          ["Inequality", "Pooled Gini 0.9605 · mean within-batch 0.4924", "Pooled: all 37,335 allocations; within-batch: 725 batches"],
          ["Within-batch overlaps", "Verra 0 · Gold Standard 5", "Adjacent record pairs in the full database; source data, not interpreted"],
          ["Demo fingerprint", "c544f589…6483b", "Deterministic seeded state, reproduced in release QA"]]
table(s, L, 1.8, CW, d_rows, [2.2, 4.4, 5.533], row_h=0.48, size=12)
source(s, "Sources: eval/results/registry_audit.json; live API /api/analytics/population/summary; docs/FINAL_RELEASE_QA_REPORT.md §3; "
          "docs/DATANOVA_PHASE_3_SPRINT_3_4_1_METRICS_RECONCILIATION_AUDIT.md.", y=6.68)

# ---------------------------------------------------------------- A4 Cross-registry and temporal
s = appendix("A4", "Cross-registry and timing analytics (real data)", "Use this if asked about cross-registry or temporal analysis. Emphasise: identical IDs across registries are flagged as collisions, never as the same project; bursts are signals, not proof.")
picture(s, ASSETS / "xreg.jpg", L, 1.75, h=4.75)
pw = 4.75 * 1148 / 1194
tx = L + pw + 0.3
tw = R - tx
th = 3.45
picture(s, ASSETS / "temporal.jpg", tx, 1.75, h=th)
text(s, tx, 1.75 + th + 0.12, tw, 1.4, [
    [("Cross-registry: ", {"bold": True}), ("all 96 Verra × Gold Standard project pairs scored (0.40 token-set + 0.30 token-sort + 0.30 Jaro-Winkler). "
      "12 reach 0.5: 9 have contradicting attributes, 2 partial correlation, 1 insufficient evidence. None share an identifier.", {"color": MUTED})],
    [("Timing: ", {"bold": True}), ("192 monthly periods; 51 burst periods (leave-one-out MAD, k = 3); 10 zero-activity gaps, longest 91 days.", {"color": MUTED})]],
     size=12, space_after=6)
source(s, "Real screenshots of the running app (cross-registry modal captured on the identical local build). Source: /api/cross-registry/projects/correlations, /api/analytics/temporal/*.", y=6.72)

# ---------------------------------------------------------------- A5 Verification
s = appendix("A5", "What public verification proves, and what it does not", "Use this for 'what does verification actually verify?'. Each check is separate; the claimant check needs the claimant's private salt; nothing here proves a document's contents are true.")
vh = 4.6
vw = vh * 1048 / 983
picture(s, ASSETS / "verify.jpg", L, 1.8, h=vh)
vx = L + vw + 0.3
ver = [["Check", "Proves"],
       ["Network", "RPC chain ID equals the deployment record (31337 = local)"],
       ["Contract code", "Runtime bytecode equals the compiled artifact"],
       ["On-chain record", "Claim exists on the contract; status and ranges read from chain"],
       ["Ranges", "App database ranges equal on-chain ranges"],
       ["Evidence commitment", "Stored digests recompute to the on-chain commitment"],
       ["Document", "Uploaded file’s SHA-256 matches, or proves membership"],
       ["Claimant", "Name + private salt reproduce the commitment"]]
table(s, vx, 1.8, R - vx, ver, [2.0, R - vx - 2.0], row_h=0.5, size=12)
text(s, vx, 5.95, R - vx, 0.6, "Does not prove: that a document is true, that the registrar acted honestly, or which claim is legitimate.", size=12, color=AMB)
source(s, "Live check on OO-2026-0001, 21 Nov 2026: 5 pass; document and claimant not performed (no file or salt supplied). Screenshot shows a run with the seeded document (6/7).", y=6.68)

# ---------------------------------------------------------------- A6 Allocation screen
s = appendix("A6", "Allocation reconciliation in the product", "Use this to show the reconciliation tab: allocation class, entity relationship, match tier and the recommended next step for Helios versus Northwind.")
ah = 4.75
aw = ah * 1220 / 865
picture(s, ASSETS / "alloc.jpg", L, 1.75, h=ah)
text(s, L + aw + 0.35, 1.85, R - L - aw - 0.35, 4.6, [
    [("ALLOCATION_CONFLICT", {"font": MONO, "bold": True, "color": RED})],
    [("Entities: DIFFERENT_ENTITIES. Match tier: INSUFFICIENT_EVIDENCE.", {"color": MUTED})],
    [("Overlap: PARTIAL_OVERLAP, 4,559 units, 65.13% of the candidate, 45.59% of the anchored claim.", {"color": MUTED})],
    [("Next step: ", {"bold": True}), ("request the retiring account holder’s allocation records; if the earlier claim is invalid, challenge it on-chain.", {"color": MUTED})]],
     size=14, space_after=12)
source(s, "Screenshot of onceonly-demo.onrender.com/claims/2 (Allocation Reconciliation tab), cropped. Values from /api/claims/2/reconciliation.", y=6.68)

# ---------------------------------------------------------------- A7 References
s = appendix("A7", "References", "Sources for every external statement and dataset in the deck.")
refs = [
    "Quartson, P., Haya, B.K., Bernard, T., Abayo, A., Rong, X., So, I.S., Elias, M. (2026). Voluntary Registry Offsets Database v2026-08. "
    "Berkeley Carbon Trading Project, UC Berkeley. CC BY 4.0. gspp.berkeley.edu/berkeley-carbon-trading-project/offsets-database",
    "Integrity Council for the Voluntary Carbon Market (ICVCM). Core Carbon Principles: Principle 8, “No double-counting”. icvcm.org/core-carbon-principles",
    "DATANOVA 2026 Global Data-thon: rules and judging criteria. datanova-2026-global-data-thon.devpost.com/rules; datanovathon.com",
    "OnceOnly repository (code, evaluation results, methodology and QA reports). github.com/Sidd927/OnceOnly-DataNova, branch datanova/phase-0-baseline",
    "Claim-evidence audit for every number in this deck: submission/datanova_final/OnceOnly_DataNova_Claim_Evidence_Audit.md",
]
text(s, L, 1.9, CW, 4.6, [[(f"{i + 1}.  ", {"bold": True, "color": ACC}), (r, {})] for i, r in enumerate(refs)], size=14, space_after=14, line=1.15)
text(s, L, 6.1, CW, 0.5, "Registry data © the respective registries, compiled by the Berkeley Carbon Trading Project. Demo claimants and documents are synthetic. "
     "AI coding assistants were used during development.", size=11, color=DIM)

# theme hyperlink colours: keep links legible on the dark background in every viewer
from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
theme_part = prs.slide_master.part.part_related_by(RT.THEME)
theme = etree.fromstring(theme_part.blob)
ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
for tag, col in (("hlink", "EAF1EE"), ("folHlink", "A3B7B3")):
    el = theme.find(f".//a:clrScheme/a:{tag}", ns)
    for child in list(el):
        el.remove(child)
    etree.SubElement(el, qn("a:srgbClr"), val=col)
theme_part._blob = etree.tostring(theme, xml_declaration=True, encoding="UTF-8", standalone=True)

prs.core_properties.title = "OnceOnly: Every retired tonne, claimed once (DATANOVA 2026 Round 2)"
prs.core_properties.author = "Siddhant Patil"
prs.core_properties.subject = "DATANOVA 2026 Global Data-thon pitch deck"
prs.save(PPTX)
print("wrote", PPTX, len(prs.slides), "slides")


# ================================================================ presenter guide
def write_guide():
    main = [n for n in NOTES if n["time"] != "backup"]
    out = ["# OnceOnly: DATANOVA 2026 Round 2 Presenter Guide", "",
           "Generated by `build/build_deck.py` together with the deck, so the speaker notes in the PPTX and this guide are identical.", "",
           "| | |", "|---|---|",
           "| Format (official) | Live online presentation over Google Meet for shortlisted teams, by 25 Nov 2026 (Unstop stage description) |",
           "| Duration | **Not published by the organisers.** The full script is about 1,300 words: about 8 minutes at a brisk 160 words per minute, 8.5–9 minutes at a relaxed pace. Ask the organisers for your slot length and use the cut-down plans below |",
           "| Deck | `OnceOnly_DataNova_Pitch_Deck.pptx` (13 main + 7 appendix slides; notes on every slide) |", "",
           "## Before you start", "",
           "1. Open https://onceonly-demo.onrender.com about 5 minutes before the call. The free instance sleeps and took 93 s to wake on 21 Nov 2026.",
           "2. Keep two tabs ready: `/claims/2` (Helios) and `/verify`. See `OnceOnly_DataNova_Live_Demo_Runbook.md`.",
           "3. Share the presentation window, not the whole screen. Present in slideshow mode so slide numbers and notes stay private.",
           "4. Keep `OnceOnly_DataNova_Judge_QA.md` open on a second screen.", "",
           "## If you have less time", "",
           "- **5 minutes:** skip slides 5 and 8 (say one sentence each: \"It's a full pipeline\" and \"16 explainable rules\"), and shorten slide 9 to the disclosure chart.",
           "- **3 minutes:** slides 1, 2, 4, 6, 10, 13.",
           "- **Live demo instead of slide 6:** if the judges ask for a demo, switch to the browser at slide 6 and follow the runbook (about 3 minutes).", "",
           "## Slide by slide", ""]
    for n in NOTES:
        label = n["number"] if n["number"] is not None else 1
        out += [f"### {label}. {n['title'] or 'Title'}", "", f"**Timing:** {n['time']}", "", f"**Say:** {n['say']}", "",
                f"**Why this slide matters:** {n['why']}", "", f"**Key point to leave with judges:** {n['key']}", ""]
        if n.get("next"):
            out += [f"**Transition:** {n['next']}", ""]
        if n is main[-1]:
            out += ["---", "", "## Appendix slides (backup, use only when asked)", ""]
    out += ["## Full script (main slides, read-through version)", ""]
    for n in main:
        out += [n["say"], ""]
    GUIDE.write_text("\n".join(out))
    print("wrote", GUIDE)


NOTES[0]["title"] = "Title: OnceOnly"
NOTES[0]["number"] = 1
NOTES[12]["title"] = "Close: Every retired tonne, claimed once"
write_guide()

"""Generate the OnceOnly DATANOVA 2026 deck (python-pptx). Every number is taken from repository result files or verified runs."""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(sys.argv[1])
SHOTS = ROOT / "docs/assets/datanova"
OUT = ROOT / "docs/submission/OnceOnly_DATANOVA_Final_Presentation.pptx"

C = {k: RGBColor.from_string(v) for k, v in dict(
    ink="12333A", soft="3B5359", muted="566A6F", night="0D262B", night2="12323A", nline="24464D", ntext="C9D8D5",
    fog="EDF1EF", fog2="E3E9E6", sheet="FFFFFF", rule="D3DCD9", slate="8FA3A6", lichen="2A7253", lbright="6CC49A",
    lwash="E1F0E8", glacier="2B6C8A", gwash="E0EEF4", ochre="8A580C", owash="F6ECD9", crimson="B4233C", cwash="F8E3E7").items()}
SANS, MONO = "Arial", "Courier New"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def box(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, lw=0.75):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
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
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.06
    return s


def text(slide, x, y, w, h, runs, size=14, color=None, bold=False, font=SANS, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.1):
    """runs: str | list of paragraphs; a paragraph is str or list of (text, {opts})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        segs = para if isinstance(para, list) else [(para, {})]
        for seg, o in segs:
            r = p.add_run()
            r.text = seg
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", color or C["ink"])
        if isinstance(para, list) and para and para[0][1].get("space_after"):
            p.space_after = Pt(para[0][1]["space_after"])
    return tb


def header(slide, kicker, title, dark=False, num=None):
    text(slide, 0.6, 0.42, 9, 0.3, kicker.upper(), size=11, bold=True, color=C["lbright"] if dark else C["lichen"])
    text(slide, 0.6, 0.72, 12.1, 0.9, title, size=28, bold=True, color=C["sheet"] if dark else C["ink"])
    if num:
        text(slide, 11.9, 7.0, 0.9, 0.3, f"{num:02d}", size=10, color=C["ntext"] if dark else C["muted"], align=PP_ALIGN.RIGHT, font=MONO)
    text(slide, 0.6, 7.0, 9, 0.3, "OnceOnly · Every retired tonne, claimed once.", size=10, color=C["ntext"] if dark else C["muted"])


def picture(slide, path, x, y, w=None, h=None, border=True):
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    if border:
        pic.line.color.rgb = C["rule"]
        pic.line.width = Pt(0.75)
    return pic


def crop_to(pic, target_w, target_h, top=0.0, left=0.0):
    """Crop a picture to the target aspect ratio, starting at fractional offsets (top, left), and size it."""
    iw, ih = pic.image.size
    ar = target_w / target_h
    if iw / ih > ar:  # too wide: keep full height, crop width
        keep = (ih * ar) / iw
        pic.crop_left = left
        pic.crop_right = max(0.0, 1 - keep - left)
    else:  # too tall: keep full width, crop height
        keep = (iw / ar) / ih
        top = min(top, 1 - keep)
        pic.crop_top = top
        pic.crop_bottom = max(0.0, 1 - keep - top)
    pic.width, pic.height = Inches(target_w), Inches(target_h)


# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK)
bg(s, C["night"])
text(s, 0.7, 0.7, 6, 0.35, "DATANOVA 2026 GLOBAL DATA-THON", size=12, bold=True, color=C["lbright"])
text(s, 0.7, 1.35, 6.6, 1.0, "OnceOnly", size=60, bold=True, color=C["sheet"])
text(s, 0.7, 2.45, 6.4, 1.2, "Every retired tonne,\nclaimed once.", size=30, bold=True, color=C["ntext"], spacing=1.0)
text(s, 0.7, 4.0, 5.9, 1.4, "A carbon-credit claim integrity and investigation platform. It reconciles public climate claims with real registry retirements, explains every signal with its evidence and limits, and anchors claims on a contract that refuses to register the same unit twice.", size=15, color=C["ntext"], spacing=1.2)
text(s, 0.7, 5.75, 6, 0.9, [[("Siddhant Patil", {"bold": True, "color": C["sheet"]})], [("github.com/Sidd927/OnceOnly-DataNova", {"font": MONO, "size": 12, "color": C["ntext"]})]], size=14)
p = picture(s, SHOTS / "03-claim-overlap.jpg", 7.35, 1.35, border=False)
crop_to(p, 5.4, 3.375)
p.line.color.rgb = C["nline"]
text(s, 7.35, 4.85, 5.4, 0.9, "Real Verra retirement (Berkeley VROD 2026-08, batch 18453). Synthetic claimants. Local Hardhat development chain.", size=11, color=C["ntext"])

# ---------------------------------------------------------------- 2 problem
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "The problem", "A retirement happens once. Claims about it happen everywhere.", num=2)
text(s, 0.6, 1.75, 5.2, 3.6, [
    [("Registries stop a credit being retired twice. ", {"bold": True}), ("Nothing checks whether the same retired units then back two companies' public climate claims.", {})],
    [("", {})],
    [("Brokers split one retirement across many buyers, ", {"bold": True}), ("and claims cite it in reports, labels and websites, each one valid when read alone.", {})],
    [("", {})],
    [("Hashes and string matching miss it: ", {"bold": True}), ("overlapping claims usually cite different serial strings in different documents.", {})],
], size=16, color=C["ink"], spacing=1.15)
# interval diagram from real numbers
X0, X1 = 6.3, 12.7
lo, hi = 896_309_560, 896_329_558
def ux(u): return X0 + (u - lo) / (hi - lo) * (X1 - X0)
box(s, 6.0, 1.75, 6.95, 4.6, fill=C["sheet"], line=C["rule"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, 6.3, 1.9, 6.4, 0.35, [[("VCS:18453", {"font": MONO, "bold": True}), ("  real Verra retirement · 19,999 units", {})]], size=12, color=C["soft"])
rows = [("Registry retirement", lo, hi, C["fog2"], C["slate"]), ("Northwind Foods · claim A (anchored)", 896_309_560, 896_319_559, C["lichen"], None),
        ("Helios Apparel · claim B", 896_315_001, 896_322_000, C["sheet"], C["ink"])]
for i, (lab, a, b, f, l) in enumerate(rows):
    y = 2.55 + i * 0.95
    text(s, 6.3, y, 6.4, 0.3, lab, size=12, bold=True, color=C["ink"])
    box(s, ux(a), y + 0.33, ux(b) - ux(a), 0.38, fill=f, line=l)
for yy in (3.5, 4.45):
    box(s, ux(896_315_001), yy + 0.33, ux(896_319_559) - ux(896_315_001), 0.38, fill=C["crimson"], line=C["crimson"])
text(s, ux(896_315_001), 5.25, 3.2, 0.6, [[("4,559 units claimed twice", {"bold": True, "color": C["crimson"]})], [("896,315,001 – 896,319,559", {"font": MONO, "size": 11, "color": C["crimson"]})]], size=13)
text(s, 6.3, 5.85, 6.4, 0.4, "The contract reverts claim B: RangeOverlap(…, 896315001, 896319559)", size=10.5, color=C["soft"], font=MONO)

# ---------------------------------------------------------------- 3 why existing approaches fall short
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Why simple checks fail", "The evidence is fragmented, and the obvious shortcuts break", num=3)
cards = [
    ("0.333", "recall of exact serial / document-hash matching", "It misses every reformatted, partial, contained or superset overlap in the 270-pair evaluation.", C["crimson"]),
    ("159,511", "spurious overlaps if the batch is ignored", "Unit numbers restart in every issuance batch (11,631 Verra + 147,880 Gold Standard adjacent pairs). Ranges must be keyed by registry and batch.", C["ochre"]),
    ("62.7 %", "of analysed retirements name no beneficiary", "Undisclosed is a disclosure fact, not misconduct, but it limits who can be linked to which units.", C["glacier"]),
    ("2 roles", "broker vs principal, parent vs subsidiary", "\"Retired on behalf of\" and related companies look like conflicts to a naive interval check, and similar names are not legal identity.", C["lichen"]),
]
for i, (big, lab, body, col) in enumerate(cards):
    x = 0.6 + i * 3.08
    box(s, x, 1.85, 2.9, 4.4, fill=C["sheet"], line=C["rule"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    box(s, x, 1.85, 2.9, 0.09, fill=col)
    text(s, x + 0.25, 2.15, 2.5, 0.8, big, size=34, bold=True, color=col)
    text(s, x + 0.25, 3.0, 2.5, 0.8, lab, size=13, bold=True, color=C["ink"])
    text(s, x + 0.25, 3.85, 2.45, 2.4, body, size=12.5, color=C["soft"], spacing=1.15)
text(s, 0.6, 6.55, 12, 0.35, "Sources: eval/results/latest.json and registry_audit.json (full Berkeley VROD 2026-08: 493,518 rows); beneficiary share from the 37,335-retirement demo subset.", size=10, color=C["muted"])

# ---------------------------------------------------------------- 4 solution
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Our solution", "From a claim document to an explained, verifiable result", num=4)
steps = [
    ("Read", "Deterministic serial parser with provenance on every block; SHA-256 of each document"),
    ("Reconcile", "Serials become unit intervals in (registry, batch) namespaces, matched to real retirements"),
    ("Allocate", "Interval geometry + entity resolution: split, broker, related parties or conflict"),
    ("Profile", "Disclosure, concentration, fragmentation, timing and cross-registry context"),
    ("Assess", "16 deterministic rules, 6 scopes; evidence, counterevidence, missing data, next step"),
    ("Anchor, verify", "ClaimLedger refuses overlapping units; per-check public verification"),
]
for i, (t, d) in enumerate(steps):
    x = 0.6 + i * 2.06
    box(s, x, 1.9, 1.9, 2.45, fill=C["night"] if i in (2, 4) else C["sheet"], line=C["rule"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    dark = i in (2, 4)
    text(s, x + 0.18, 2.05, 1.6, 0.3, f"{i + 1:02d}", size=11, font=MONO, color=C["lbright"] if dark else C["muted"])
    text(s, x + 0.18, 2.38, 1.65, 0.45, t, size=15, bold=True, color=C["sheet"] if dark else C["ink"])
    text(s, x + 0.18, 2.95, 1.6, 1.4, d, size=11.5, color=C["ntext"] if dark else C["soft"], spacing=1.12)
    if i < 5:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 1.92), Inches(3.0), Inches(0.12), Inches(0.22))
        a.fill.solid(); a.fill.fore_color.rgb = C["slate"]; a.line.fill.background()
users = [("Sustainability auditors", "check a client's claim against registry records and other claims"),
         ("Registry / standards reviewers", "see how retirements are split, disclosed and timed"),
         ("Carbon-market analysts", "triage projects, batches and entities with explainable signals")]
text(s, 0.6, 4.75, 4, 0.35, "WHO IT IS FOR", size=11, bold=True, color=C["lichen"])
for i, (u, d) in enumerate(users):
    x = 0.6 + i * 4.12
    text(s, x, 5.15, 3.9, 1.2, [[(u, {"bold": True, "size": 14})], [(d, {"color": C["soft"]})]], size=12.5, spacing=1.15)
text(s, 0.6, 6.45, 12, 0.35, "Highlighted steps (Allocate, Assess) are the DATANOVA additions to the original claim-ledger core.", size=10.5, color=C["muted"])

# ---------------------------------------------------------------- 5 architecture
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Architecture", "Explainable analytics off-chain; one invariant on-chain", num=5)
def layer(x, y, w, h, title, items, fill, tcol, icol):
    box(s, x, y, w, h, fill=fill, line=C["rule"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 0.2, y + 0.15, w - 0.4, 0.35, title, size=13, bold=True, color=tcol)
    text(s, x + 0.2, y + 0.55, w - 0.4, h - 0.6, [[("· " + it, {})] for it in items], size=11.5, color=icol, spacing=1.12)
layer(0.6, 1.8, 3.0, 4.6, "Data", ["Berkeley VROD 2026-08 (real): 493,518 rows; demo subset 38,004 rows, 22 projects", "Non-destructive normalization: raw values kept", "Synthetic claim documents", "Curated benchmarks (124 + 36 cases)"], C["sheet"], C["ink"], C["soft"])
layer(3.85, 1.8, 5.4, 4.6, "FastAPI backend · Python 3.12", ["Claim pipeline: serials → registry rules → findings → report hash", "2A entity resolution: normalization, intermediaries, blocking, matching", "2B allocation reconciliation: interval algebra, 8 allocation classes", "2C concentration · fragmentation · temporal · cross-registry", "Stage 4 assessment: 16 rules, dependency groups", "Verification: on-chain vs off-chain checks reported separately", "SQLite (claims, read-only registry DB) · content-addressed evidence"], C["night"], C["sheet"], C["ntext"])
layer(9.5, 1.8, 3.25, 2.15, "ClaimLedger.sol", ["Ranges keyed by keccak(registry:batch)", "O(1) hinted sorted list; RangeOverlap revert", "Local Hardhat chain 31337"], C["sheet"], C["ink"], C["soft"])
layer(9.5, 4.2, 3.25, 2.2, "React 19 UI", ["Overview · Claims · Cross-Registry", "Observatory · Assessment", "Verify · Evidence", "Bespoke SVG charts, no chart library"], C["sheet"], C["ink"], C["soft"])
text(s, 0.6, 6.55, 12.2, 0.35, "Deployment: one Docker image (private chain, contract, seeded demo, API serving the UI), about 280 MB of memory; Render blueprint prepared.", size=10.5, color=C["muted"])

# ---------------------------------------------------------------- 6 differentiation
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Technical differentiation", "Intervals, not hashes. Classes, not one red flag.", num=6)
diffs = [
    ("Allocation-aware reconciliation", "Six geometric and eight allocation classes separate a legitimate split, a broker acting for a disclosed principal, related companies and an unresolved beneficiary from a conflict between unrelated claimants."),
    ("Namespace isolation", "Every comparison is inside one (registry, batch). Identical numbers or project IDs across registries are an identifier collision, never the same asset."),
    ("Defensible statistics", "HHI and entropy over disclosed volume only; pooled vs within-batch Gini reported separately; leave-one-out MAD bursts; absolute vs relative small allocations."),
    ("Explainability by construction", "16 versioned deterministic rules; each finding carries thresholds, counterevidence, missing data and a next step; correlated signals grouped so they cannot double-count."),
    ("Verification you can redo", "Document, commitment, ranges, network and deployed bytecode checked separately; database lookups never counted as on-chain proof."),
    ("A contract that scales", "Registration gas flat at 301,452 from 10 to 200 active ranges per batch (linear v0: 832,608); a bad hint reverts, it never skips the check."),
]
for i, (t, d) in enumerate(diffs):
    col, row = i % 3, i // 3
    x, y = 0.6 + col * 4.12, 1.8 + row * 2.4
    box(s, x, y, 3.95, 2.2, fill=C["sheet"], line=C["rule"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 0.22, y + 0.18, 3.5, 0.4, t, size=14.5, bold=True, color=C["ink"])
    text(s, x + 0.22, y + 0.68, 3.55, 1.5, d, size=11.5, color=C["soft"], spacing=1.13)

# ---------------------------------------------------------------- 7 evidence & validation
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Evidence and validation", "Measured, and labelled for what each test measures", num=7)
cd = CategoryChartData()
cd.categories = ["OnceOnly engine", "ClaimLedger contract", "Batch-blind interval", "Hash / exact string"]
cd.add_series("Recall", (1.0, 1.0, 1.0, 0.333))
cd.add_series("Precision", (1.0, 1.0, 0.857, 1.0))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(2.15), Inches(6.2), Inches(3.4), cd)
ch = gf.chart
ch.has_legend = True
ch.legend.include_in_layout = False
from pptx.enum.chart import XL_LEGEND_POSITION
ch.legend.position = XL_LEGEND_POSITION.BOTTOM
ch.legend.font.size = Pt(11)
ch.legend.font.name = SANS
ch.value_axis.maximum_scale = 1.0
ch.value_axis.minimum_scale = 0.0
ch.value_axis.has_major_gridlines = False
ch.value_axis.tick_labels.font.size = Pt(10)
ch.category_axis.tick_labels.font.size = Pt(11)
ch.category_axis.tick_labels.font.name = SANS
ch.category_axis.reverse_order = True
for i, col in enumerate((C["lichen"], C["glacier"])):
    ser = ch.plots[0].series[i]
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
plot = ch.plots[0]
plot.has_data_labels = True
plot.data_labels.font.size = Pt(10)
plot.data_labels.number_format = "0.000"
plot.data_labels.number_format_is_linked = False
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
text(s, 0.6, 1.75, 6.2, 0.4, "Double use on 270 synthetic claim pairs citing real Verra ranges", size=13, bold=True)
text(s, 0.6, 5.6, 6.2, 0.9, "Ground truth uses the engine's interval definition, so 1.000 verifies the implementation; the finding is what the simpler methods miss. Not real-world accuracy.", size=11, color=C["soft"], spacing=1.12)
rows = [("Registry serials → unit ranges (full VROD)", "493,518 / 493,518"), ("Overlaps inside one batch (Verra)", "0 of 307,416"),
        ("Entity resolution, 124 curated pairs", "P 1.000 · R 0.964"), ("Allocation class, 36 curated scenarios", "36 / 36"),
        ("Serial extraction, 60 synthetic snippets", "100 % in-sample"), ("Population metrics, independent SQL re-run", "exact match")]
text(s, 7.2, 1.75, 5.6, 0.4, "Data and analysis checks", size=13, bold=True)
for i, (k, v) in enumerate(rows):
    y = 2.2 + i * 0.47
    box(s, 7.2, y, 5.55, 0.42, fill=C["sheet"] if i % 2 == 0 else C["fog2"])
    text(s, 7.35, y + 0.07, 3.5, 0.3, k, size=11.5)
    text(s, 10.75, y + 0.07, 1.9, 0.3, v, size=11.5, bold=True, align=PP_ALIGN.RIGHT)
text(s, 7.2, 5.15, 5.6, 0.4, "Software tests (this release)", size=13, bold=True)
text(s, 7.2, 5.55, 5.6, 0.9, [[("274", {"bold": True}), (" backend  ·  ", {}), ("24", {"bold": True}), (" contract  ·  ", {}), ("45", {"bold": True}), (" browser  ·  ", {}), ("13/13", {"bold": True}), (" end-to-end", {})],
                              [("Demo state fingerprint reproduced: c544f589…6483b", {"font": MONO, "size": 10.5, "color": C["soft"]})]], size=13, spacing=1.2)

# ---------------------------------------------------------------- 8 product demonstration
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Product demonstration", "One real retirement, two synthetic claims, every step explained", num=8)
shots = [("03-claim-overlap.jpg", 0.52, "1 · The Ruler: 4,559 units already back Northwind's anchored claim; the contract rejects the second registration"),
         ("04-claim-reconciliation.jpg", 0.12, "2 · Allocation reconciliation: ALLOCATION_CONFLICT between different entities, with a next step"),
         ("05-assessment.jpg", 0.30, "3 · Assessment: RULE-REC-002 with metrics, limitations and grouped concentration signals"),
         ("09-verify.jpg", 0.30, "4 · Verification: seven separate checks, including deployed bytecode and the document commitment")]
for i, (f, top, cap) in enumerate(shots):
    col, row = i % 2, i // 2
    x, y = 0.6 + col * 6.2, 1.65 + row * 2.62
    p = picture(s, SHOTS / f, x, y)
    crop_to(p, 5.95, 2.05, top=top)
    text(s, x, y + 2.1, 5.95, 0.5, cap, size=11, color=C["soft"])

# ---------------------------------------------------------------- 9 trust, limitations, responsible use
s = prs.slides.add_slide(BLANK)
bg(s, C["night"])
header(s, "Trust, limitations and responsible use", "What it verifies, what it flags, what it cannot conclude", dark=True, num=9)
cols = [
    ("VERIFIES", C["lbright"], ["Serial strings parse into exact unit ranges and match registry retirement records (snapshot 2026-08-31)", "Two claims share specific units in the same registry batch", "A document is byte-identical to what was committed on chain", "The deployed contract code matches the compiled artifact"]),
    ("FLAGS FOR REVIEW", RGBColor.from_string("E8B35A"), ["Potential double use, classified by allocation type", "Concentration, fragmentation, timing anomalies", "Candidate cross-registry project links", "Missing beneficiary information (reported, never imputed)"]),
    ("CANNOT CONCLUDE", C["crimson"].__class__.from_string("EF7A8C"), ["Fraud, intent, or which claim is legitimate", "Legal identity from similar names or parent/subsidiary links", "Credit quality, additionality or permanence", "Anything about the whole market: analytics cover a 22-project subset"]),
]
for i, (t, col, items) in enumerate(cols):
    x = 0.6 + i * 4.12
    box(s, x, 1.85, 3.95, 3.75, fill=C["night2"], line=C["nline"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x + 0.25, 2.05, 3.5, 0.35, t, size=13, bold=True, color=col)
    text(s, x + 0.25, 2.5, 3.5, 3.0, [[("· " + it, {"space_after": 6})] for it in items], size=12.5, color=C["ntext"], spacing=1.12)
text(s, 0.6, 5.8, 12.2, 1.0, [
    [("Trust boundaries: ", {"bold": True, "color": C["sheet"]}), ("local Hardhat development chain (31337), not a public network · one trusted registrar key, no claimant signatures · synthetic claimants · static registry snapshot · AI extraction implemented but not measured · benchmarks synthetic or curated, not real-world accuracy.", {})],
], size=12, color=C["ntext"], spacing=1.15)

# ---------------------------------------------------------------- 10 impact & future
s = prs.slides.add_slide(BLANK)
bg(s, C["fog"])
header(s, "Impact and next steps", "From a working prototype to a usable integrity check", num=10)
text(s, 0.6, 1.75, 5.9, 0.4, "Practical value", size=15, bold=True)
text(s, 0.6, 2.2, 5.9, 3.6, [
    [("Catches what document review and hashing miss: ", {"bold": True}), ("partial and reformatted overlaps of the same retired units.", {})],
    [("Makes analysis reviewable: ", {"bold": True}), ("every signal shows its rule, threshold, counterevidence and next step, so an auditor can defend or reject it.", {})],
    [("Reproducible: ", {"bold": True}), ("public data, open code, one-command container, deterministic demo state.", {})],
    [("Neutral ordering: ", {"bold": True}), ("a contract invariant that the operator's own UI cannot bypass.", {})],
], size=13, color=C["soft"], spacing=1.25)
text(s, 6.9, 1.75, 5.9, 0.4, "Credible path forward", size=15, bold=True)
nxt = ["Public testnet deployment with claimant-signed registrations (EIP-712)", "Per-document Merkle commitments and proofs", "Registry data beyond the 2026-08 snapshot; more registries", "Measure AI extraction (accuracy, cost, latency) on real documents", "Pilot with real published claims, with consent, to measure prevalence"]
for i, n in enumerate(nxt):
    y = 2.2 + i * 0.62
    box(s, 6.9, y, 0.42, 0.42, fill=C["night"], shape=MSO_SHAPE.OVAL)
    text(s, 6.9, y + 0.07, 0.42, 0.3, str(i + 1), size=12, bold=True, color=C["sheet"], align=PP_ALIGN.CENTER)
    text(s, 7.5, y + 0.05, 5.3, 0.5, n, size=12.5, color=C["ink"])
box(s, 0.6, 5.6, 12.15, 1.05, fill=C["night"], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, 0.9, 5.72, 11.6, 0.85, [
    [("Run it: ", {"bold": True, "color": C["sheet"]}), ("make docker-build && make docker-run  →  http://127.0.0.1:7860", {"font": MONO, "color": C["lbright"]})],
    [("Code, data notes and methodology: ", {"bold": True, "color": C["sheet"]}), ("github.com/Sidd927/OnceOnly-DataNova", {"font": MONO, "color": C["ntext"]}),
     ("   ·   Registry data: Berkeley Carbon Trading Project, VROD v2026-08 (CC BY 4.0)", {"color": C["ntext"], "size": 11})],
], size=13, spacing=1.3)

prs.core_properties.title = "OnceOnly — Every retired tonne, claimed once (DATANOVA 2026)"
prs.core_properties.author = "Siddhant Patil"
prs.save(OUT)
print(OUT)

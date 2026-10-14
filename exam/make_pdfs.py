#!/usr/bin/env python3
"""Step 5: build the PDFs from the SVG charts and the seated roster.

    python exam/make_pdfs.py --data data/sample

<out>/pdf/handout.pdf          course header; overview chart; assigned-seats chart; students sorted by
                               name; students sorted by seat (extra-room students listed last)
<out>/pdf/seat_charts.pdf      overview, left-handed map, then one page per planned seat (bookmarked)
<out>/pdf/seat_pdfs.zip        one single-page PDF per planned seat, named <seat_id>.pdf

All pages are US Letter portrait with 1/2" margins; charts are vector (SVG -> PDF via cairosvg).
"""
import io, zipfile
import cairosvg, pandas as pd
from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from settings import args, load_config

PW, PH, M = 612, 792, 36          # Letter, points; 1/2" margins
SECTIONS = ["Main Left", "Main Center", "Main Right", "Balcony Left", "Balcony Center", "Balcony Right"]

def svg_page(svg_path, header=None, page_no=None):
    """Place an SVG chart on a Letter page (width-fitted, a little below center), optional header/footer."""
    src = PdfReader(io.BytesIO(cairosvg.svg2pdf(url=str(svg_path)))).pages[0]
    top_reserve = 26 if header else 0
    sc = min((PW - 2 * M) / float(src.mediabox.width), (PH - 2 * M - top_reserve) / float(src.mediabox.height))
    cw, ch = float(src.mediabox.width) * sc, float(src.mediabox.height) * sc
    avail_top = M + top_reserve; top = avail_top + ((PH - M - avail_top) - ch) * 0.4
    p = PageObject.create_blank_page(width=PW, height=PH)
    p.merge_transformed_page(src, Transformation().scale(sc).translate(M + ((PW - 2 * M) - cw) / 2, PH - top - ch))
    if header or page_no:
        buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=letter)
        if header:
            c.setFont("Helvetica-Bold", 15); c.setFillColor(colors.HexColor("#111111")); c.drawCentredString(PW / 2, PH - M - 12, header)
        if page_no:
            c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#666666")); c.drawRightString(PW - 0.5 * inch, 0.32 * inch, f"Page {page_no}")
        c.save(); p.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
    return p

def finish(w, path, title):
    for pg in w.pages: pg.compress_content_streams(level=9)
    w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    w.add_metadata({"/Title": title}); w.write(path)

def table_pages(df, cols, title, subtitle, footer_txt, first_page_no, course, extra_room):
    note = lambda x: {"Left": "Left-handed desk", "Accom": extra_room}.get(x, "")
    hdr = {"last": "Last", "first": "First", "netid": "NetID", "precept": "Precept", "Seat": "Seat"}
    widths = {"last": 1.75, "first": 1.55, "netid": 0.75, "precept": 0.7, "Seat": 0.85}
    rows = [["#"] + [hdr[c] for c in cols] + ["Notes"]]
    for i, x in enumerate(df.itertuples(), 1):
        rows.append([str(i)] + [(getattr(x, c) or "—") for c in cols] + [note(x.Special)])
    t = Table(rows, colWidths=[0.4 * inch] + [widths[c] * inch for c in cols] + [1.5 * inch], repeatRows=1)
    si = cols.index("Seat") + 1
    ts = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5), ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("ALIGN", (0, 0), (0, -1), "RIGHT"), ("FONT", (si, 1), (si, -1), "Helvetica-Bold", 9),
          ("TOPPADDING", (0, 0), (-1, -1), 1.7), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.7),
          ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i in range(1, len(rows)):
        if i % 2 == 0: ts.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F3F3F3")))
        if rows[i][-1] == "Left-handed desk": ts.append(("TEXTCOLOR", (-1, i), (-1, i), colors.HexColor("#1B7F4B")))
        if rows[i][-1] == extra_room: ts.append(("TEXTCOLOR", (1, i), (-1, i), colors.HexColor("#9A3412")))
    t.setStyle(TableStyle(ts))
    st = getSampleStyleSheet()
    H = ParagraphStyle("h", parent=st["Title"], fontName="Helvetica-Bold", fontSize=18, spaceAfter=4)
    S = ParagraphStyle("s", parent=st["Normal"], fontSize=9.5, textColor=colors.HexColor("#444444"), alignment=1, spaceAfter=10)
    buf = io.BytesIO()
    def foot(c, doc):
        c.saveState(); c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#666666"))
        c.drawString(0.5 * inch, 0.32 * inch, f"{course} · seat assignments, {footer_txt}")
        c.drawRightString(letter[0] - 0.5 * inch, 0.32 * inch, f"Page {doc.page + first_page_no - 1}"); c.restoreState()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.5 * inch, rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.6 * inch)
    doc.build([Paragraph(title, H), Paragraph(subtitle, S), t], onFirstPage=foot, onLaterPages=foot)
    return PdfReader(io.BytesIO(buf.getvalue())).pages

def main():
    a = args(__doc__.splitlines()[0]); cfg = load_config()["exam"]
    course, extra = cfg["course"], cfg["extra_room"]
    out = a.out / "pdf"; out.mkdir(exist_ok=True)
    plan = pd.read_csv(a.out / "exam_plan.csv")
    planned = plan[plan.exam_plan].copy(); planned["so"] = planned.section.map(SECTIONS.index)
    planned = planned.sort_values(["so", "row", "seat"])

    # handout
    r = pd.read_csv(a.out / "students_seated.csv", dtype=str, keep_default_na=False)
    r = r.merge(plan[["seat_id", "section", "row", "seat"]], how="left", left_on="Seat", right_on="seat_id")
    r["so"] = r.section.map(lambda s: SECTIONS.index(s) if isinstance(s, str) else 99)
    by_name = r.sort_values(["last", "first"], key=lambda c: c.str.lower()).reset_index(drop=True)
    by_seat = r.sort_values(["so", "row", "seat", "last", "first"]).reset_index(drop=True)
    n_seat, n_l, n_a = (r.Seat != "").sum(), (r.Special == "Left").sum(), (r.Special == "Accom").sum()
    summary = f"{len(r)} students: {n_seat} seated in the room ({n_l} at left-handed desks); {n_a} in {extra}."
    A = table_pages(by_name, ["last", "first", "netid", "precept", "Seat"], "Seat Assignments by Student",
                    f"{course}. Sorted by last name, first name. {summary}", "sorted by last name", 3, course, extra)
    B = table_pages(by_seat, ["Seat", "last", "first", "netid", "precept"], "Seat Assignments by Seat",
                    f"{course}. Sorted by section (ML, MC, MR, BL, BC, BR), row, seat. Students in {extra} listed last.",
                    "sorted by seat", 3 + len(A), course, extra)
    w = PdfWriter()
    w.add_page(svg_page(a.out / "charts" / "overview.svg", course, 1))
    w.add_page(svg_page(a.out / "charts" / "assigned.svg", course, 2))
    for pg in list(A) + list(B): w.add_page(pg)
    w.add_outline_item("Seating chart", 0); w.add_outline_item("Assigned seats", 1)
    w.add_outline_item("By student (A-Z)", 2); w.add_outline_item("By seat", 2 + len(A))
    finish(w, out / "handout.pdf", f"{course}: seat assignments")

    # combined seat charts with bookmarks
    w = PdfWriter(); w.add_page(svg_page(a.out / "charts" / "overview.svg")); w.add_outline_item("Overall map", 0)
    w.add_page(svg_page(a.out / "charts" / "lefthanded.svg")); w.add_outline_item("Left-handed desks", 1)
    parents = {}
    for s in planned.itertuples():
        w.add_page(svg_page(a.out / "seats" / f"{s.seat_id}.svg")); n = len(w.pages) - 1
        if s.section not in parents: parents[s.section] = w.add_outline_item(s.section, n)
        w.add_outline_item(s.seat_id, n, parent=parents[s.section])
    w.page_mode = "/UseOutlines"
    finish(w, out / "seat_charts.pdf", f"{course}: seat charts")

    # one PDF per seat, zipped
    with zipfile.ZipFile(out / "seat_pdfs.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for s in planned.itertuples():
            w = PdfWriter(); w.add_page(svg_page(a.out / "seats" / f"{s.seat_id}.svg"))
            b = io.BytesIO(); finish(w, b, f"{cfg['room_title']}: seat {s.seat_id}"); z.writestr(f"{s.seat_id}.pdf", b.getvalue())
    print(f"handout.pdf ({2 + len(A) + len(B)} pages), seat_charts.pdf ({2 + len(planned)} pages), "
          f"seat_pdfs.zip ({len(planned)} files) -> {out}")

if __name__ == "__main__":
    main()

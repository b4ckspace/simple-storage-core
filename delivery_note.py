#!/usr/bin/env python3
import datetime
import math
import re
import zlib
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parent / "Lieferschein_Vorlage.pdf"
MAX_DELIVERY_NOTE_ITEMS = 10
MEDIA_BOX = "[0.000 0.000 595.280 841.890]"

DEFAULT_SENDER = {
    "name": "Firmenname",
    "street": "Strasse 1",
    "city": "12345 Musterstadt",
    "email": "info@example.com",
}


def build_delivery_note_rows(order_items):
    return [row for row in order_items if not row.get("external_fulfillment")]


def format_delivery_address_lines(order):
    lines = []

    if order.get("shipping_name"):
        lines.append(order["shipping_name"])
    if order.get("shipping_address1"):
        lines.append(order["shipping_address1"])

    zip_city = " ".join(
        part for part in [order.get("shipping_zip") or "", order.get("shipping_city") or ""] if part
    ).strip()
    if zip_city:
        lines.append(zip_city)

    if order.get("shipping_country"):
        lines.append(order["shipping_country"])

    return lines or ["Keine Lieferadresse"]


def build_delivery_note_pdf(template_path, output_path, order, order_items, sender=None):
    template_bytes = Path(template_path).read_bytes()
    objects = _parse_pdf_objects(template_bytes)
    rows = build_delivery_note_rows(order_items)
    regular_font_obj_id = max(objects) + 1
    bold_font_obj_id = regular_font_obj_id + 1
    objects[regular_font_obj_id] = _build_builtin_font_object("Helvetica")
    objects[bold_font_obj_id] = _build_builtin_font_object("Helvetica-Bold")
    resources_body = _augment_resources_with_builtin_fonts(
        _extract_page_resources(objects[3]),
        regular_font_obj_id,
        bold_font_obj_id,
    )
    objects[3] = _build_pages_object([6], resources_body)
    objects[5] = _build_info_object()
    objects[6] = _build_page_object(7)
    objects[7] = _build_stream_object(build_delivery_note_content_stream(order, rows, 1, 1, sender=sender))

    if rows:
        page_count = math.ceil(len(rows) / MAX_DELIVERY_NOTE_ITEMS)
    else:
        page_count = 1

    if page_count > 1:
        next_obj_id = max(objects) + 1
        page_ids = []
        for page_index in range(page_count):
            page_obj_id = 6 if page_index == 0 else next_obj_id
            content_obj_id = 7 if page_index == 0 else next_obj_id + 1
            page_ids.append(page_obj_id)
            page_rows = rows[page_index * MAX_DELIVERY_NOTE_ITEMS : (page_index + 1) * MAX_DELIVERY_NOTE_ITEMS]
            objects[page_obj_id] = _build_page_object(content_obj_id)
            objects[content_obj_id] = _build_stream_object(
                build_delivery_note_content_stream(order, page_rows, page_index + 1, page_count, sender=sender)
            )
            if page_index > 0:
                next_obj_id += 2

        objects[3] = _build_pages_object(page_ids, resources_body)

    pdf_bytes = _assemble_pdf(objects)
    Path(output_path).write_bytes(pdf_bytes)
    return Path(output_path)


def build_delivery_note_content_stream(order, rows, page_number=1, page_count=1, sender=None):
    order_name = order.get("order_name") or "-"
    created_at = order.get("created_at")
    sender = _normalized_sender(sender)

    if hasattr(created_at, "strftime"):
        order_date = created_at.strftime("%d.%m.%Y")
    else:
        order_date = str(created_at or "")

    commands = [
        "1.000 1.000 1.000 rg",
        "60.000 75.000 490.280 732.874 re f",
        "q",
        "150.000 0 0 43.500 60.000 764.374 cm /I2 Do",
        "Q",
        "0.129 0.169 0.212 rg",
        _text_cmd(441.652, 778.669, "F4", 15.8, "Lieferschein"),
        _text_cmd(416.426, 750.808, "F4", 10.5, f"Bestellung: {order_name}"),
        _text_cmd(447.779, 737.363, "F3", 10.5, f"Datum: {order_date}"),
        _text_cmd(447.779, 723.919, "F3", 10.5, f"Seite: {page_number} von {page_count}"),
    ]

    sender_line_y = 697.548
    commands.append(_text_cmd(60.000, sender_line_y, "F3", 7.5, _build_sender_line(sender)))
    commands.append("0.129 0.169 0.212 RG")
    commands.append("0.33 w 0 J [  ] 0 d")
    commands.append("60.000 696.037 m 272.273 696.037 l S")

    address_y = 677.372
    for index, line in enumerate(format_delivery_address_lines(order)):
        commands.append(_text_cmd(60.000, address_y - (index * 13.444), "F3", 10.5, line))

    sender_block_y = 694.475
    for index, line in enumerate(_build_sender_block_lines(sender)):
        commands.append(_text_cmd(437.856, sender_block_y - (index * 13.444), "F3", 10.5, line))

    commands.extend(
        [
            "q",
            "60.000 565.712 m 60.000 564.712 l 132.535 564.712 l 132.535 565.712 l 132.535 566.462 l 60.000 566.462 l W n",
            "0.75 w 0 J [  ] 0 d",
            "60.000 566.087 m 132.535 566.087 l S",
            "Q",
            "/GS1 gs",
            "/GS2 gs",
            "0.129 0.169 0.212 rg",
            _text_cmd(65.000, 574.151, "F4", 10.5, "Position"),
            "q",
            "132.535 565.712 m 132.535 564.712 l 487.975 564.712 l 487.975 565.712 l 487.975 566.462 l 132.535 566.462 l W n",
            "0.129 0.169 0.212 RG",
            "0.75 w 0 J [  ] 0 d",
            "132.535 566.087 m 487.975 566.087 l S",
            "Q",
            "/GS1 gs",
            "/GS2 gs",
            "0.129 0.169 0.212 rg",
            _text_cmd(137.535, 574.151, "F4", 10.5, "Artikel"),
            "q",
            "487.975 565.712 m 487.975 564.712 l 550.280 564.712 l 550.280 565.712 l 550.280 566.462 l 487.975 566.462 l W n",
            "0.129 0.169 0.212 RG",
            "0.75 w 0 J [  ] 0 d",
            "487.975 566.087 m 550.280 566.087 l S",
            "Q",
            "/GS1 gs",
            "/GS2 gs",
            "0.129 0.169 0.212 rg",
            _text_cmd(505.401, 574.151, "F4", 10.5, "Anzahl"),
        ]
    )

    base_y = 543.235
    row_step = 36.889
    position_offset = (page_number - 1) * MAX_DELIVERY_NOTE_ITEMS
    for index, row in enumerate(rows, start=1):
        row_y = base_y - ((index - 1) * row_step)
        title = _truncate_text(row.get("title") or "-", 56)
        sku = _truncate_text(row.get("sku") or "-", 32)
        qty = str(row.get("quantity") or 0)
        commands.append(_text_cmd(65.000, row_y, "F3", 10.5, str(position_offset + index)))
        commands.append(_text_cmd(137.535, row_y + 6.722, "F3", 10.5, title))
        commands.append(_text_cmd(137.535, row_y - 6.722, "F3", 10.5, sku))
        commands.append(_text_cmd(538.602, row_y, "F3", 10.5, qty))

    commands.append(_text_cmd(60.000, 156.073, "F3", 10.5, "Vielen Dank für Ihre Bestellung!"))
    return "\n".join(commands) + "\n"


def _truncate_text(value, length):
    if len(value) <= length:
        return value
    if length <= 3:
        return value[:length]
    return value[: length - 3] + "..."


def _text_cmd(x, y, font, size, text):
    escaped = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    return f"BT {x:.3f} {y:.3f} Td /{font} {size} Tf ({escaped}) Tj ET"


def _normalized_sender(sender):
    normalized = DEFAULT_SENDER.copy()
    normalized.update(sender or {})
    return normalized


def _build_sender_line(sender):
    parts = [sender["name"], sender["street"], sender["city"]]
    return " - ".join(part for part in parts if part)


def _build_sender_block_lines(sender):
    return [part for part in [sender["name"], sender["street"], sender["city"], sender["email"]] if part]


def _extract_page_resources(pages_object_body):
    resources_start = pages_object_body.index(b"/Resources <<")
    media_box_start = pages_object_body.index(b"/MediaBox", resources_start)
    return pages_object_body[resources_start:media_box_start].rstrip()


def _augment_resources_with_builtin_fonts(resources_body, regular_font_obj_id, bold_font_obj_id):
    marker = b"/Font <<"
    insert_at = resources_body.index(b">>", resources_body.index(marker))
    font_refs = (
        f"\n/F3 {regular_font_obj_id} 0 R\n/F4 {bold_font_obj_id} 0 R".encode("ascii")
    )
    return resources_body[:insert_at] + font_refs + resources_body[insert_at:]


def _build_pages_object(page_ids, resources_body):
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    return (
        b"<< /Type /Pages\n"
        + f"/Kids [{kids}]\n".encode("ascii")
        + f"/Count {len(page_ids)}\n".encode("ascii")
        + resources_body
        + b"\n"
        + f"/MediaBox {MEDIA_BOX}\n".encode("ascii")
        + b">>"
    )


def _build_page_object(content_obj_id):
    return (
        b"<< /Type /Page\n"
        + f"/MediaBox {MEDIA_BOX}\n".encode("ascii")
        + b"/Parent 3 0 R\n"
        + f"/Contents {content_obj_id} 0 R\n".encode("ascii")
        + b">>"
    )


def _build_builtin_font_object(base_font_name):
    return (
        b"<< /Type /Font\n"
        b"/Subtype /Type1\n"
        + f"/BaseFont /{base_font_name}\n".encode("ascii")
        + b"/Encoding /WinAnsiEncoding\n"
        b">>"
    )


def _parse_pdf_objects(pdf_bytes):
    objects = {}
    matches = list(re.finditer(rb"(\d+) 0 obj\b", pdf_bytes))
    for index, match in enumerate(matches):
        obj_id = int(match.group(1))
        body_start = match.end()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(pdf_bytes)
        body = pdf_bytes[body_start:next_start]
        endobj_pos = body.rfind(b"endobj")
        if endobj_pos != -1:
            body = body[:endobj_pos]
        objects[obj_id] = body.strip()
    return objects


def _build_info_object():
    timestamp = datetime.datetime.now().strftime("D:%Y%m%d%H%M%S+01'00'")
    return (
        b"<<\n"
        b"/Producer (Lagerverwaltung)\n"
        + f"/CreationDate ({timestamp})\n".encode("ascii")
        + f"/ModDate ({timestamp})\n".encode("ascii")
        + b"/Title (\xfe\xff\x00L\x00i\x00e\x00f\x00e\x00r\x00s\x00c\x00h\x00e\x00i\x00n)\n"
        b">>"
    )


def _build_stream_object(stream_text):
    compressed = zlib.compress(stream_text.encode("cp1252"))
    return (
        b"<< /Filter /FlateDecode\n"
        + f"/Length {len(compressed)} >>\n".encode("ascii")
        + b"stream\n"
        + compressed
        + b"\nendstream"
    )


def _assemble_pdf(objects):
    highest = max(objects)
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}

    for obj_id in range(1, highest + 1):
        body = objects[obj_id]
        offsets[obj_id] = len(output)
        output.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        output.extend(body)
        if not body.endswith(b"\n"):
            output.extend(b"\n")
        output.extend(b"endobj\n")

    startxref = len(output)
    output.extend(f"xref\n0 {highest + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, highest + 1):
        output.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {highest + 1}\n/Root 1 0 R\n/Info 5 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(output)

import io

import qrcode


def build_qr_image(data: str):
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#39495B", back_color="white")


def build_qr_png_bytes(data: str) -> bytes:
    image = build_qr_image(data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

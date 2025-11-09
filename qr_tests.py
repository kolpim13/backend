from PIL import Image, ImageDraw, ImageFont
import qrcode

def make_qr_with_logo(
    data: str,
    logo_path: str,
    out_path: str = "qr_with_logo_balanced.png",
    box_size: int = 12,
    border: int = 2,
    logo_scale: float = 0.22,
    add_label: bool = True,
    label_text: str = "SCAN ME",
):
    # 1) Build QR with high error correction
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # 2) Centered logo with white padding ring
    logo = Image.open(logo_path).convert("RGBA")
    qr_w, qr_h = qr_img.size
    target_logo_w = int(qr_w * logo_scale)
    ratio = target_logo_w / logo.width
    logo = logo.resize((target_logo_w, int(logo.height * ratio)), Image.LANCZOS)

    pad = int(target_logo_w * 0.18)
    bg_w, bg_h = logo.width + pad*2, logo.height + pad*2
    bg = Image.new("RGBA", (bg_w, bg_h), (255, 255, 255, 255))
    mask = Image.new("L", (bg_w, bg_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, bg_w, bg_h), radius=int(min(bg_w,bg_h)*0.12), fill=255)
    padded = Image.new("RGBA", (bg_w, bg_h))
    padded.paste(bg, (0, 0), mask)
    padded.paste(logo, (pad, pad), logo)

    x = (qr_w - padded.width)//2
    y = (qr_h - padded.height)//2
    qr_img.paste(padded, (x, y), padded)

    # 3) Add thick black border frame
    frame_thickness = int(qr_w * 0.04)
    framed_size = qr_w + 2 * frame_thickness
    framed = Image.new("RGB", (framed_size, framed_size), "black")
    framed.paste(qr_img, (frame_thickness, frame_thickness))
    qr_img = framed
    qr_w, qr_h = qr_img.size

    # 4) Medium-sized label below
    if add_label and label_text:
        label_height = int(qr_h * 0.18)  # balanced label height (≈ between small and large)
        label_width = qr_w
        total_height = qr_h + int(label_height * 1.2)
        canvas = Image.new("RGB", (label_width, total_height), "white")

        # paste QR on top
        canvas.paste(qr_img, (0, 0))

        # draw the black rounded label background
        label_y = qr_h
        label = Image.new("RGB", (label_width, label_height), "black")
        rmask = Image.new("L", label.size, 0)
        draw_mask = ImageDraw.Draw(rmask)

        # smaller radius: about 10–12% of label height (previously 20%)
        corner_radius = 10
        draw_mask.rounded_rectangle(
            (0, 0, int(label_width*0.8), int(label_height*0.8)),
            radius=corner_radius,
            fill=255
        )

        canvas.paste(label, (0, label_y), rmask)

        # centered text
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", size=int(label_height * 0.5))
        except:
            font = ImageFont.load_default()

        # Pillow 10+ compatibility
        try:
            bbox = draw.textbbox((0, 0), label_text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(label_text, font=font)

        tx = (label_width - tw)//2
        ty = label_y + (label_height - th)//2
        draw.text((tx, ty), label_text, fill="white", font=font)

        qr_img = canvas

    qr_img.save(out_path)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    make_qr_with_logo(
        data="https://example.com",
        logo_path="logo_1.jpg",
        out_path="qr_with_logo_balanced.png",
        add_label=True,
        label_text="SCAN ME",
    )

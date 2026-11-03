"""Build the business-card files from the details below.

    pip install segno
    python tools/make_card.py

Writes:
  contact.vcf   - the contact people save ("Save contact" on card.html)
  card-qr.svg   - QR code containing the same contact, so scanning it with
                  any phone camera offers "Add to contacts" - no app or
                  internet needed

Change a detail here, run it again, commit the two files.
"""
import pathlib
import segno

CARD = {
    "first": "Thomas",
    "last": "Dyson",
    "title": "Assistant Site Manager",
    "org": "Cyden Homes",
    "site": "The Hyde",
    "phone": "+447471355743",
    "email": "thomas@fenbyhall.co.uk",
}

ROOT = pathlib.Path(__file__).resolve().parent.parent


def esc(v):
    """vCard text escaping (RFC 6350 s3.4)."""
    return v.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def vcard(c):
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{esc(c['last'])};{esc(c['first'])};;;",
        f"FN:{esc(c['first'])} {esc(c['last'])}",
        f"ORG:{esc(c['org'])};{esc(c['site'])}",
        f"TITLE:{esc(c['title'])}",
        f"TEL;TYPE=CELL:{c['phone']}",
        f"EMAIL;TYPE=WORK:{c['email']}",
        "END:VCARD",
    ]
    return "\r\n".join(lines) + "\r\n"


def main():
    text = vcard(CARD)
    (ROOT / "contact.vcf").write_bytes(text.encode("utf-8"))
    qr = segno.make(text, error="m", micro=False)
    qr.save(str(ROOT / "card-qr.svg"), scale=8, border=2, dark="#0d0d0d", light="#ffffff",
            xmldecl=False, svgns=True, title="Scan to save Thomas Dyson's contact")
    print(f"QR version {qr.version} ({qr.designator}), {len(text)} bytes -> contact.vcf, card-qr.svg")


if __name__ == "__main__":
    main()

import qrcode

# The URL to encode
url = "http://localhost:8501/"

# Generate QR
qr = qrcode.make(url)

# Save the image
qr.save("client_app_qr_local.png")

print("✅ QR code saved as client_app_qr.png")

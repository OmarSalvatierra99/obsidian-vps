import imaplib
import email
import os

# ===== CONFIGURACIÓN =====
USER = "omargabrielsalvatierragarcia@gmail.com"
PASS = "ypig tlxg tghu yhzl"  # NO tu contraseña normal
IMAP_SERVER = "imap.gmail.com"
SAVE_DIR = "xml_cfdi"

# Crear carpeta si no existe
os.makedirs(SAVE_DIR, exist_ok=True)

# Conexión con Gmail
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(USER, PASS)
mail.select("inbox")

# Buscar todos los correos del remitente con CFDI adjuntos
query = '(FROM "correspondencia.ofs.tlax@gmail.com" SUBJECT "CFDI" SINCE "01-Jan-2025")'
result, data = mail.search(None, query)

print(f"Correos encontrados: {len(data[0].split())}")

for num in data[0].split():
    result, msg_data = mail.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    for part in msg.walk():
        filename = part.get_filename()
        if filename and filename.endswith(".xml"):
            filepath = os.path.join(SAVE_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(part.get_payload(decode=True))
            print(f"Descargado: {filename}")

mail.logout()
print("Descarga completada.")


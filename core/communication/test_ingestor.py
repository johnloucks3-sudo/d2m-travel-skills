import imaplib
print("Testing IMAP connection...")
try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    print("Connection successful")
    mail.login("d2mconcierge@gmail.com", "Falcons4me!")
    print("Login successful")
    mail.select("inbox")
    print("Inbox selected")
    mail.logout()
    print("Logout successful")
except Exception as e:
    print(f"Error: {e}")

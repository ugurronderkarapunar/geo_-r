"""
generate_passwords.py
─────────────────────
config.yaml için bcrypt hashlenmiş şifreler üretir.
Kullanım:
    pip install streamlit-authenticator
    python generate_passwords.py
"""

import sys

try:
    import streamlit_authenticator as stauth
except ImportError:
    sys.exit("❌  streamlit-authenticator yüklü değil: pip install streamlit-authenticator")

# ── Hashlenecek şifreler (config.yaml ile eşleştirin) ─────────────────────────
PLAIN_PASSWORDS = {
    "admin":    "Admin@2024!",   # → admin kullanıcısı
    "premium1": "Premium@2024!", # → premium kullanıcı
    "free1":    "Free@2024!",    # → ücretsiz kullanıcı
}

print("\n🔐  Şifre hashleri oluşturuluyor…\n")
hashed = stauth.Hasher(list(PLAIN_PASSWORDS.values())).generate()

for (user, plain), hashed_pw in zip(PLAIN_PASSWORDS.items(), hashed):
    print(f"  Kullanıcı : {user}")
    print(f"  Şifre     : {plain}")
    print(f"  Hash      : {hashed_pw}")
    print()

print("─" * 60)
print("📋  config.yaml içine kopyalanmaya hazır YAML parçacığı:\n")
print("credentials:")
print("  usernames:")

roles = {"admin": "premium", "premium1": "premium", "free1": "free"}
emails = {
    "admin":    "admin@example.com",
    "premium1": "premium@example.com",
    "free1":    "free@example.com",
}
names = {"admin": "Admin User", "premium1": "Premium User", "free1": "Free User"}

for (user, plain), hashed_pw in zip(PLAIN_PASSWORDS.items(), hashed):
    print(f"    {user}:")
    print(f"      email:    {emails[user]}")
    print(f"      name:     {names[user]}")
    print(f"      password: {hashed_pw}")
    print(f"      role:     {roles[user]}")

print()
print("cookie:")
print("  expiry_days: 30")
print("  key:         geopolitical_pulse_secret_key_change_this_in_production")
print("  name:        geopolitical_pulse_session")

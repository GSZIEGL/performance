
import hashlib
import secrets
import string

LICENSE_SALT = "CSERELD_EROS_TITKOS_SALTRA"  # ugyanaz legyen, mint Streamlit Secrets-ben

def make_code(prefix="PS"):
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return prefix + "-" + "-".join(parts)

def hash_license_key(raw_key: str) -> str:
    return hashlib.sha256((LICENSE_SALT + "::" + raw_key.strip()).encode("utf-8")).hexdigest()

if __name__ == "__main__":
    code = make_code()
    print("LICENSE CODE:", code)
    print("LICENSE HASH:", hash_license_key(code))

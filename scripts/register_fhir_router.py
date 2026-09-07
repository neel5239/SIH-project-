from pathlib import Path

path = Path(r".\services\m6_platform\main.py")
text = path.read_text(encoding="utf-8")

if "from .api.fhir import router as fhir_router" not in text:
    marker = "from .api.admin import router as admin_router"
    if marker not in text:
        raise RuntimeError("Could not find admin router import")
    text = text.replace(
        marker,
        marker + "\nfrom .api.fhir import router as fhir_router",
        1
    )

if "app.include_router(fhir_router, prefix=prefix)" not in text:
    marker = "app.include_router(admin_router, prefix=prefix)"
    if marker not in text:
        raise RuntimeError("Could not find admin router registration")
    text = text.replace(
        marker,
        marker + "\napp.include_router(fhir_router, prefix=prefix)",
        1
    )

path.write_text(text, encoding="utf-8")
print("FHIR router registered successfully.")

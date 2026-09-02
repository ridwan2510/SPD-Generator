from services.api_service import (
    get_all_ppk
)

print(
    "=== TEST PPK API ==="
)

try:

    data = get_all_ppk()

    print(
        "Jumlah PPK:",
        len(data)
    )

    print(
        "Data:",
        data
    )

except Exception as e:

    print(
        "ERROR:",
        repr(e)
    )
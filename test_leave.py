import requests

BASE = "http://localhost:8000"


def run_leave_uat():
    s = requests.Session()

    # 1. Get CSRF cookie
    r = s.get(f"{BASE}/api/demo-auth/users/")
    print("CSRF GET:", r.status_code)

    csrf = s.cookies.get("csrftoken")
    print("CSRF:", csrf)

    if not csrf:
        raise SystemExit("ERROR: No CSRF cookie received")

    # 2. Login
    r = s.post(
        f"{BASE}/api/demo-auth/login/",
        json={"username": "demo.hr.admin"},
        headers={"X-CSRFToken": csrf},
    )

    print("\nLOGIN:", r.status_code)
    print(r.text)
    print("COOKIES:", s.cookies.get_dict())

    if r.status_code != 200:
        raise SystemExit("STOP: Login failed")

    # 3. Verify authenticated session
    r = s.get(f"{BASE}/api/employees/me/")

    print("\nME:", r.status_code)
    print(r.text)

    if r.status_code != 200:
        raise SystemExit("STOP: Session authentication failed")

    # 4. Create leave request
    body = {
        "leave_type": 1,
        "start_date": "2026-09-21",
        "end_date": "2026-09-25",
        "reason": "UAT leave creation test",
        "contact_during_leave": "Demo contact",
        "emergency_contact_name": "Demo contact",
        "emergency_contact_phone": "0000000000",
        "handover_contact": "Demo Manager",
        "handover_notes": "UAT handover",
    }

    csrf = s.cookies.get("csrftoken")

    r = s.post(
        f"{BASE}/api/leave-requests/",
        json=body,
        headers={
            "X-CSRFToken": csrf,
            "Referer": f"{BASE}/",
        },
    )

    print("\nLEAVE CREATE:", r.status_code)
    print(r.text)


if __name__ == "__main__":
    run_leave_uat()

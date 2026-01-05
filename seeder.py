import sys

import requests
from tqdm import tqdm

from payload_factory import generate_category_payload, generate_business_payload

# --- KONFIGURACJA API ---
BASE_URL = "http://localhost:8071/core-api"

# --- KONFIGURACJA DANYCH LOGOWANIA ---
CREDENTIALS = {
    "ADMIN": {
        "url": f"{BASE_URL}/auth/admin/login",
        "payload": {
            "firstName": "admin",
            "lastName": "admin",
            "email": "admin@kalendar.com",
            "password": "K4fO4co3uln5Iz2"
        }
    },
    "BUSINESS": {
        "url": f"{BASE_URL}/auth/business/login",
        "payload": {
            "email": "Agatka@gmail.com",
            "password": "!Kretadroga12345"
        }
    }
}


def login_and_get_token(role):
    """Loguje się i zwraca czysty string tokena JWT"""
    print(f"🔑 Logowanie jako {role}...")
    creds = CREDENTIALS.get(role)
    try:
        response = requests.post(creds["url"], json=creds["payload"])
        if response.status_code == 200:
            data = response.json()
            token = data.get("accessToken") or data.get("token") or data.get("access_token")
            if token:
                print(f"  [OK] Zalogowano pomyślnie.")
                return token
    except Exception as e:
        print(f"  [WYJĄTEK] Błąd logowania: {e}")

    print(f"  [BŁĄD KRYTYCZNY] Nie udało się zalogować jako {role}. Sprawdź dane.")
    sys.exit(1)


def extract_id_from_response(response):
    """Próbuje wyciągnąć ID zasobu z Location header lub body"""
    location = response.headers.get('Location')
    if location:
        return location.split('/')[-1]
    try:
        data = response.json()
        return data.get('id')
    except:
        return None


def fetch_existing_categories(session):
    """Pobiera listę ID istniejących kategorii"""
    print("  🔍 Sprawdzam, czy kategorie już istnieją...")
    try:
        # Zakładam standardowy endpoint GET /business-category (może wymagać paginacji w przyszłości)
        response = session.get(f"{BASE_URL}/business-category")

        if response.status_code == 200:
            data = response.json()

            # Obsługa różnych formatów odpowiedzi (List vs Page)
            # Jeśli Spring Data zwraca stronę, dane mogą być w 'content'
            items = data.get('content', data) if isinstance(data, dict) else data

            if isinstance(items, list) and len(items) > 0:
                # Wyciągamy same ID
                ids = [item['id'] for item in items if 'id' in item]
                return ids
    except Exception as e:
        print(f"  [!] Nie udało się pobrać kategorii: {e}")

    return []


def seed_data(num_categories=5, num_businesses=20):
    print("--- ROZPOCZYNAM SEEDOWANIE (SMART MODE) ---")

    session = requests.Session()
    category_ids = []

    # =========================================================
    # KROK 1: Obsługa Kategorii (ADMIN)
    # =========================================================
    admin_jwt = login_and_get_token("ADMIN")
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_jwt}"
    })

    # A. Sprawdź czy już są kategorie
    existing_ids = fetch_existing_categories(session)

    if existing_ids:
        print(f"  [SKIP] Znaleziono {len(existing_ids)} istniejących kategorii w bazie.")
        print(f"  -> Używam istniejących ID, nie tworzę nowych.")
        category_ids = existing_ids
    else:
        # B. Jeśli pusto, stwórz nowe
        print(f"\n[KROK 1] Baza kategorii pusta. Tworzenie {num_categories} nowych...")
        for i in range(num_categories):
            payload = generate_category_payload()
            try:
                resp = session.post(f"{BASE_URL}/business-category", json=payload)
                if resp.status_code in [200, 201]:
                    cat_id = extract_id_from_response(resp)
                    if cat_id:
                        category_ids.append(cat_id)
                        print(f"  [+] Utworzono kategorię: {payload['name']}")
                else:
                    print(f"  [-] Błąd kategorii: {resp.status_code}")
            except Exception as e:
                print(f"  [!] Wyjątek: {e}")

    if not category_ids:
        print("\n[STOP] Brak kategorii (ani w bazie, ani nowych). Nie mogę tworzyć firm.")
        sys.exit(1)

    # =========================================================
    # KROK 2: Tworzenie Biznesów + Przypisywanie Właściciela (BUSINESS)
    # =========================================================
    business_jwt = login_and_get_token("BUSINESS")

    print(f"\n[KROK 2] Tworzenie {num_businesses} biznesów...")
    session.headers.update({"Authorization": f"Bearer {business_jwt}"})

    success_count = 0

    for i in tqdm(range(num_businesses), desc="Tworzenie biznesów"):
        payload = generate_business_payload(category_ids)

        try:
            # A. Tworzenie Biznesu
            resp = session.post(f"{BASE_URL}/business", json=payload)

            if resp.status_code in [200, 201]:
                biz_id = extract_id_from_response(resp)

                if biz_id:
                    print(f"  [+] ({i + 1}/{num_businesses}) Biznes OK: {payload['name']}")

                    # B. Dodawanie siebie jako pracownika
                    employee_url = f"{BASE_URL}/business/{biz_id}/employees/self"
                    emp_resp = session.post(employee_url)

                    if emp_resp.status_code in [200, 201]:
                        # print(f"      -> [Employee] Właściciel dodany.")
                        success_count += 1
                    else:
                        print(f"      -> [Employee BŁĄD] Status: {emp_resp.status_code}")
                else:
                    print(f"  [?] Brak ID biznesu.")
            else:
                # Wypiszemy błąd tylko jeśli to nie jest walidacja (żeby nie śmiecić logów przy losowych błędach)
                if resp.status_code >= 500:
                    print(f"  [-] Błąd serwera: {resp.status_code}")
                elif resp.status_code == 400:
                    print(f"  [-] Błąd walidacji: {resp.text}")

        except Exception as e:
            print(f"  [!] Wyjątek: {e}")

    print(f"\n--- ZAKOŃCZONO ---")
    print(f"Pełen sukces (Biznes + Pracownik): {success_count}/{num_businesses}")


if __name__ == "__main__":
    seed_data(num_categories=15, num_businesses=20)

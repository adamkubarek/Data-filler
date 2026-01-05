import random

from locust import HttpUser, task, between, LoadTestShape

# --- KONFIGURACJA ---
# Jeśli search wymaga tokena (np. zalogowany klient), wklej go tu.
# Jeśli jest publiczny, możesz zostawić pusty lub usunąć nagłówek Authorization.
JWT_TOKEN = ""

# Lista słów, których będziemy szukać w findValue
# Powinny pokrywać się z tym, co generuje Twój seeder (payload_factory.py)
SEARCH_TERMS = [
    "Salon", "Studio", "Gabinet", "Centrum", "Zakład",  # Prefiksy nazw
    "Fryzjer", "Barber", "Kosmetyka", "Masaż", "SPA",  # Kategorie tekstowo
    "Anna", "Tomek", "Ewa", "Jan",  # Imiona (bo nazwy to "Studio Anna")
    "Katowice", "Slaskie"  # Lokalizacje
]


class BooksySearchUser(HttpUser):
    # Symulacja czasu myślenia użytkownika (1-3 sekundy między wyszukiwaniami)
    wait_time = between(1, 3)

    # Współdzielona pamięć na kategorie (pobieramy je tylko raz dla wszystkich userów)
    category_ids_cache = []

    def on_start(self):
        """Uruchamiane przy starcie każdego użytkownika"""
        self.setup_headers()
        self.ensure_categories_loaded()

    def setup_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if len(JWT_TOKEN) > 10:
            headers["Authorization"] = f"Bearer {JWT_TOKEN}"

        self.client.headers.update(headers)

    def ensure_categories_loaded(self):
        """
        Pobiera kategorie z API tylko jeśli cache jest pusty.
        Dzięki temu test 'wie', jakich ID używać w filtrach.
        """
        if not BooksySearchUser.category_ids_cache:
            try:
                # Zakładam, że endpoint kategorii jest publiczny lub dostępny dla Usera
                with self.client.get("/core-api/business-category", catch_response=True, name="Init: Get Categories") as response:
                    if response.status_code == 200:
                        data = response.json()
                        # Obsługa paginacji (gdyby Spring zwracał 'content')
                        items = data.get('content', data) if isinstance(data, dict) else data

                        if items:
                            BooksySearchUser.category_ids_cache = [c['id'] for c in items]
                            print(f"✅ Załadowano {len(BooksySearchUser.category_ids_cache)} kategorii do testów.")
                        else:
                            print("⚠️ Pobrałem kategorie, ale lista jest pusta!")
                    else:
                        print(f"❌ Błąd pobierania kategorii: {response.status_code}")
            except Exception as e:
                print(f"❌ Wyjątek przy pobieraniu kategorii: {e}")

    @task(3)  # Waga 3: Częściej szukamy po kategorii (klikanie w ikonki)
    def search_by_category(self):
        if not BooksySearchUser.category_ids_cache:
            return  # Nie mamy ID, nie możemy testować

        # Losujemy kategorię
        cat_id = random.choice(BooksySearchUser.category_ids_cache)

        # Wywołanie GET z parametrem
        self.client.get(
            f"/core-api/business?businessCategoryId={cat_id}",
            name="/business?catId=[id]"  # Grupujemy w raporcie Locusta jako jeden wpis
        )

    @task(1)  # Waga 1: Rzadziej wpisujemy tekst ręcznie
    def search_by_text(self):
        # Losujemy słowo kluczowe
        term = random.choice(SEARCH_TERMS)

        # Wywołanie GET z findValue
        self.client.get(
            f"/core-api/business?findValue={term}",
            name="/business?findValue=[term]"
        )


# --- SCENARIUSZ OBCIĄŻENIA (Load Shape) ---
class StepLoadShape(LoadTestShape):
    """
    Scenariusz:
    1. Rozgrzewka (10 userów)
    2. Średni ruch (50 userów)
    3. Szczyt (200 userów)
    4. Wygaszanie
    """
    stages = [
        {"duration": 30, "users": 10, "spawn_rate": 2},
        {"duration": 60, "users": 50, "spawn_rate": 5},
        {"duration": 120, "users": 200, "spawn_rate": 20},  # Test wytrzymałości bazy!
        {"duration": 150, "users": 0, "spawn_rate": 50},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None

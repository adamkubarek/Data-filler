import random

from faker import Faker

fake = Faker('pl_PL')

# Lista realnych kategorii pasujących do klona Booksy
REAL_CATEGORIES = [
    "Fryzjer damski", "Barber Shop", "Salon Kosmetyczny", "Manicure i Pedicure",
    "Masaż i SPA", "Fizjoterapia", "Trener Personalny", "Dietetyk",
    "Stomatologia", "Psychoterapia", "Tatuaż i Piercing", "Depilacja",
    "Medycyna Estetyczna", "Groomer (Psi Fryzjer)", "Mechanik Samochodowy",
    "Wulkanizacja", "Myjnia Ręczna", "Sprzątanie Domów", "Hydraulik",
    "Serwis Rowerowy", "Korepetycje", "Szkoła Tańca"
]


def generate_polish_phone_number():
    """Generuje poprawny polski numer komórkowy: +48XXXXXXXXX"""
    prefixes = ['50', '51', '53', '60', '66', '69', '72', '78', '79', '88']
    prefix = random.choice(prefixes)
    rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
    return f"+48{prefix}{rest}"


def generate_category_payload():
    """Generuje JSON dla kategorii z listy realnych usług"""
    # Losujemy jedną z przygotowanych nazw
    category_name = random.choice(REAL_CATEGORIES)
    return {
        "name": category_name
    }


def generate_business_payload(available_category_ids):
    if not available_category_ids:
        raise ValueError("Brak kategorii!")

    # Generujemy nazwę firmy pasującą do kontekstu
    # Np. "Salon Urody - Anna" zamiast "Pol-Bud - Jan"
    prefix = random.choice(["Salon", "Studio", "Gabinet", "Centrum", "Pracownia", "Zakład"])
    company_name = f"{prefix} {fake.first_name()}"

    # Bezpieczny numer budynku
    safe_building_number = str(random.randint(1, 200))
    if random.choice([True, False]):
        safe_building_number += random.choice(["A", "B", "C"])

    payload = {
        "name": company_name,
        "description": fake.bs().capitalize(),  # Losowy opis biznesowy
        "status": "ACTIVE",
        "intervalPeriodValue": random.choice([15, 30, 45, 60]),
        "taxIdentifier": fake.nip(),
        "calendarViewType": random.choice(["WEEKLY", "DAILY"]),
        "businessCategoryIds": [
            random.choice(available_category_ids)
        ],
        "address": {
            "street": fake.street_name(),
            "buildingNumber": safe_building_number,
            "apartmentNo": str(random.randint(1, 100)),
            "city": fake.city(),
            "state": "Slaskie",
            "zipCode": fake.postcode(),
            "country": "PL",
            "phoneNumber": generate_polish_phone_number(),
            "secondaryPhoneNumber": generate_polish_phone_number(),
            "contactEmail": fake.email()
        }
    }
    return payload

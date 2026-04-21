# 50 capitais de província de Espanha
SPAIN_CITIES = [
    "Madrid",           # Madrid
    "Barcelona",        # Barcelona
    "Valencia",         # Valencia
    "Sevilla",          # Sevilla
    "Zaragoza",         # Zaragoza
    "Málaga",           # Málaga
    "Murcia",           # Murcia
    "Palma",            # Baleares
    "Las Palmas de Gran Canaria",  # Las Palmas
    "Bilbao",           # Vizcaya
    "Alicante",         # Alicante
    "Córdoba",          # Córdoba
    "Valladolid",       # Valladolid
    "Vigo",             # Pontevedra
    "Gijón",            # Asturias (capital de facto)
    "Granada",          # Granada
    "Oviedo",           # Asturias
    "Vitoria-Gasteiz",  # Álava
    "Pamplona",         # Navarra
    "San Sebastián",    # Guipúzcoa
    "Santander",        # Cantabria
    "Almería",          # Almería
    "Burgos",           # Burgos
    "Albacete",         # Albacete
    "Castellón de la Plana",  # Castellón
    "Logroño",          # La Rioja
    "Badajoz",          # Badajoz
    "Salamanca",        # Salamanca
    "Huelva",           # Huelva
    "Tarragona",        # Tarragona
    "Lleida",           # Lleida
    "Marbella",         # Málaga (turístico de alto volume)
    "León",             # León
    "Cádiz",            # Cádiz
    "Jaén",             # Jaén
    "Ourense",          # Ourense
    "Lugo",             # Lugo
    "Girona",           # Girona
    "Toledo",           # Toledo
    "Cáceres",          # Cáceres
    "Ciudad Real",      # Ciudad Real
    "Cuenca",           # Cuenca
    "Guadalajara",      # Guadalajara
    "Huesca",           # Huesca
    "Palencia",         # Palencia
    "Pontevedra",       # Pontevedra
    "Segovia",          # Segovia
    "Soria",            # Soria
    "Teruel",           # Teruel
    "Zamora",           # Zamora
    "Santa Cruz de Tenerife",  # Santa Cruz de Tenerife
    "Ávila",            # Ávila
]

SEARCH_QUERY = "estudio de tatuaje"

# Busca até 60 candidatos por cidade (3 páginas Google Places)
# para ter margem suficiente após filtrar por MIN_REVIEWS
RESULTS_PER_CITY = 60
MAX_LEADS_PER_CITY = 20
MIN_REVIEWS = 300

REQUEST_DELAY = 1.5  # seconds between requests to avoid rate limiting
EMAIL_TIMEOUT = 8    # seconds to wait for website response

# Firecrawl
FIRECRAWL_API_URL = "http://localhost:3002"

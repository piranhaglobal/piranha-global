# Espanha: capitais de província + cidades fortes secundárias
SPAIN_CITIES = [
    "Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga", "Murcia", "Palma",
    "Las Palmas de Gran Canaria", "Bilbao", "Alicante", "Córdoba", "Valladolid", "Vigo",
    "Gijón", "Granada", "Oviedo", "Vitoria-Gasteiz", "Pamplona", "San Sebastián",
    "Santander", "Almería", "Burgos", "Albacete", "Castellón de la Plana", "Logroño",
    "Badajoz", "Salamanca", "Huelva", "Tarragona", "Lleida", "Marbella", "León", "Cádiz",
    "Jaén", "Ourense", "Lugo", "Girona", "Toledo", "Cáceres", "Ciudad Real", "Cuenca",
    "Guadalajara", "Huesca", "Palencia", "Pontevedra", "Segovia", "Soria", "Teruel",
    "Zamora", "Santa Cruz de Tenerife", "Ávila",
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

export interface Country {
  code: string
  name: string
  flag: string
  cities: string[]
}

export const EUROPEAN_COUNTRIES: Country[] = [
  {
    code: 'ES',
    name: 'Espanha',
    flag: '🇪🇸',
    cities: [
      'Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Zaragoza', 'Málaga', 'Murcia', 'Palma',
      'Las Palmas de Gran Canaria', 'Bilbao', 'Alicante', 'Córdoba', 'Valladolid', 'Vigo',
      'Gijón', 'Granada', 'Oviedo', 'Vitoria-Gasteiz', 'Pamplona', 'San Sebastián',
      'Santander', 'Almería', 'Burgos', 'Albacete', 'Castellón de la Plana', 'Logroño',
      'Badajoz', 'Salamanca', 'Huelva', 'Tarragona', 'Lleida', 'Marbella', 'León', 'Cádiz',
      'Jaén', 'Ourense', 'Lugo', 'Girona', 'Toledo', 'Cáceres', 'Ciudad Real', 'Cuenca',
      'Guadalajara', 'Huesca', 'Palencia', 'Pontevedra', 'Segovia', 'Soria', 'Teruel',
      'Zamora', 'Santa Cruz de Tenerife', 'Ávila',
    ],
  },
  {
    code: 'PT',
    name: 'Portugal',
    flag: '🇵🇹',
    cities: [
      'Lisboa', 'Porto', 'Braga', 'Coimbra', 'Aveiro', 'Faro', 'Setúbal', 'Funchal',
      'Ponta Delgada', 'Viseu', 'Leiria', 'Évora', 'Beja', 'Viana do Castelo', 'Guimarães',
      'Vila Nova de Gaia', 'Amadora', 'Almada', 'Loures', 'Matosinhos',
    ],
  },
  {
    code: 'FR',
    name: 'França',
    flag: '🇫🇷',
    cities: [
      'Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes', 'Strasbourg', 'Montpellier',
      'Bordeaux', 'Lille', 'Rennes', 'Reims', 'Le Havre', 'Saint-Étienne', 'Toulon',
      'Grenoble', 'Dijon', 'Angers', 'Nîmes', 'Villeurbanne', 'Aix-en-Provence', 'Brest',
      'Amiens', 'Perpignan', 'Tours',
    ],
  },
  {
    code: 'IT',
    name: 'Itália',
    flag: '🇮🇹',
    cities: [
      'Roma', 'Milano', 'Napoli', 'Torino', 'Palermo', 'Genova', 'Bologna', 'Firenze',
      'Bari', 'Catania', 'Venezia', 'Verona', 'Messina', 'Padova', 'Trieste', 'Taranto',
      'Brescia', 'Prato', 'Parma', 'Modena', 'Reggio Calabria', 'Reggio Emilia', 'Perugia',
    ],
  },
  {
    code: 'DE',
    name: 'Alemanha',
    flag: '🇩🇪',
    cities: [
      'Berlin', 'Hamburg', 'München', 'Köln', 'Frankfurt am Main', 'Stuttgart', 'Düsseldorf',
      'Leipzig', 'Dortmund', 'Essen', 'Bremen', 'Dresden', 'Hannover', 'Nürnberg', 'Duisburg',
      'Bochum', 'Wuppertal', 'Bielefeld', 'Bonn', 'Münster', 'Karlsruhe', 'Mannheim',
      'Augsburg', 'Freiburg', 'Kiel',
    ],
  },
  {
    code: 'GB',
    name: 'Reino Unido',
    flag: '🇬🇧',
    cities: [
      'London', 'Birmingham', 'Manchester', 'Glasgow', 'Liverpool', 'Leeds', 'Edinburgh',
      'Bristol', 'Sheffield', 'Cardiff', 'Leicester', 'Coventry', 'Bradford', 'Belfast',
      'Nottingham', 'Newcastle upon Tyne', 'Southampton', 'Portsmouth', 'Brighton', 'Reading',
    ],
  },
  {
    code: 'NL',
    name: 'Países Baixos',
    flag: '🇳🇱',
    cities: [
      'Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht', 'Eindhoven', 'Tilburg',
      'Groningen', 'Almere', 'Breda', 'Nijmegen', 'Apeldoorn', 'Haarlem', 'Arnhem',
    ],
  },
  {
    code: 'BE',
    name: 'Bélgica',
    flag: '🇧🇪',
    cities: [
      'Brussels', 'Antwerp', 'Ghent', 'Charleroi', 'Liège', 'Bruges', 'Namur',
      'Leuven', 'Mons', 'Mechelen',
    ],
  },
  {
    code: 'CH',
    name: 'Suíça',
    flag: '🇨🇭',
    cities: [
      'Zurich', 'Geneva', 'Basel', 'Bern', 'Lausanne', 'Winterthur', 'Lucerne', 'St. Gallen',
    ],
  },
  {
    code: 'AT',
    name: 'Áustria',
    flag: '🇦🇹',
    cities: ['Vienna', 'Graz', 'Linz', 'Salzburg', 'Innsbruck', 'Klagenfurt', 'Villach'],
  },
  {
    code: 'PL',
    name: 'Polónia',
    flag: '🇵🇱',
    cities: [
      'Warsaw', 'Kraków', 'Łódź', 'Wrocław', 'Poznań', 'Gdańsk', 'Szczecin',
      'Bydgoszcz', 'Lublin', 'Katowice', 'Białystok', 'Gdynia',
    ],
  },
  {
    code: 'CZ',
    name: 'República Checa',
    flag: '🇨🇿',
    cities: ['Prague', 'Brno', 'Ostrava', 'Plzeň', 'Liberec', 'Olomouc', 'České Budějovice'],
  },
  {
    code: 'HU',
    name: 'Hungria',
    flag: '🇭🇺',
    cities: ['Budapest', 'Debrecen', 'Miskolc', 'Szeged', 'Pécs', 'Győr', 'Nyíregyháza'],
  },
  {
    code: 'RO',
    name: 'Roménia',
    flag: '🇷🇴',
    cities: ['Bucharest', 'Cluj-Napoca', 'Timișoara', 'Iași', 'Constanța', 'Craiova', 'Brașov'],
  },
  {
    code: 'GR',
    name: 'Grécia',
    flag: '🇬🇷',
    cities: ['Athens', 'Thessaloniki', 'Patras', 'Piraeus', 'Larissa', 'Heraklion', 'Volos'],
  },
  {
    code: 'SE',
    name: 'Suécia',
    flag: '🇸🇪',
    cities: [
      'Stockholm', 'Gothenburg', 'Malmö', 'Uppsala', 'Västerås', 'Örebro',
      'Linköping', 'Helsingborg', 'Norrköping', 'Jönköping',
    ],
  },
  {
    code: 'NO',
    name: 'Noruega',
    flag: '🇳🇴',
    cities: ['Oslo', 'Bergen', 'Trondheim', 'Stavanger', 'Drammen', 'Fredrikstad', 'Kristiansand'],
  },
  {
    code: 'DK',
    name: 'Dinamarca',
    flag: '🇩🇰',
    cities: ['Copenhagen', 'Aarhus', 'Odense', 'Aalborg', 'Esbjerg', 'Randers'],
  },
  {
    code: 'FI',
    name: 'Finlândia',
    flag: '🇫🇮',
    cities: ['Helsinki', 'Espoo', 'Tampere', 'Vantaa', 'Oulu', 'Turku', 'Jyväskylä'],
  },
  {
    code: 'IE',
    name: 'Irlanda',
    flag: '🇮🇪',
    cities: ['Dublin', 'Cork', 'Limerick', 'Galway', 'Waterford', 'Drogheda'],
  },
]

export function getCitiesForCountries(codes: string[]): string[] {
  return EUROPEAN_COUNTRIES
    .filter(c => codes.includes(c.code))
    .flatMap(c => c.cities)
}

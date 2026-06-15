"""
Canonical team name normalisation across all data sources.

Canonical name = the name used in results.csv (martj42 dataset), which is
the primary training data source. All other sources are mapped onto it.

WC 2026 qualified teams are tagged so they can be filtered easily.
"""

# ── Canonical → aliases from other sources ─────────────────────────────────

# Keys are canonical names (as used in results.csv / martj42).
# Values are lists of alternative spellings found in:
#   - FIFA ranking CSVs (cashncarry)
#   - Fjelstul worldcup DB
#   - Elo ratings (eloratings.net 2-letter codes)
#   - API-Football / common abbreviations

ALIASES: dict[str, list[str]] = {
    # ── CONCACAF ──────────────────────────────────────────────────────────
    "United States":        ["USA", "United States of America", "US", "U.S.A.", "US Soccer"],
    "Mexico":               ["MEX", "MX"],
    "Canada":               ["CAN", "CA"],
    "Jamaica":              ["JAM", "JM"],
    "Panama":               ["PAN", "PA"],
    "Honduras":             ["HON", "HND"],
    "Costa Rica":           ["CRC", "CR"],
    "El Salvador":          ["SLV", "SV"],
    "Trinidad and Tobago":  ["TRI", "TTO"],
    "Cuba":                 ["CUB", "CU"],
    "Guatemala":            ["GUA", "GTM"],
    "Haiti":                ["HAI", "HTI"],
    "Curaçao":              ["Curacao", "Curaçao", "CUW", "CW"],
    "Bosnia and Herzegovina": ["BIH", "Bosnia", "Bosnia & Herzegovina"],
    "Suriname":             ["SUR", "SR"],
    "Guyana":               ["GUY", "GY"],

    # ── CONMEBOL ──────────────────────────────────────────────────────────
    "Argentina":            ["ARG", "AR"],
    "Brazil":               ["BRA", "BR"],
    "Colombia":             ["COL", "CO"],
    "Uruguay":              ["URU", "URY", "UY"],
    "Ecuador":              ["ECU", "EC"],
    "Chile":                ["CHI", "CHL", "CL"],
    "Paraguay":             ["PAR", "PRY", "PY"],
    "Peru":                 ["PER", "PE"],
    "Bolivia":              ["BOL", "BO"],
    "Venezuela":            ["VEN", "VE"],

    # ── UEFA ──────────────────────────────────────────────────────────────
    "Spain":                ["ESP", "ES"],
    "France":               ["FRA", "FR"],
    "England":              ["ENG", "EN", "Three Lions"],
    "Germany":              ["GER", "DE"],
    "Portugal":             ["POR", "PT"],
    "Netherlands":          ["NED", "NL", "Holland"],
    "Belgium":              ["BEL", "BE"],
    "Italy":                ["ITA", "IT"],
    "Croatia":              ["CRO", "HRV", "HR"],
    "Denmark":              ["DEN", "DNK", "DK"],
    "Switzerland":          ["SUI", "SWI", "CHE", "CH"],
    "Poland":               ["POL", "PL"],
    "Austria":              ["AUT", "AT"],
    "Serbia":               ["SRB", "RS"],
    "Scotland":             ["SCO", "SC"],
    "Czech Republic":       ["CZE", "CZ", "Czechia"],
    "Hungary":              ["HUN", "HU"],
    "Romania":              ["ROU", "RO"],
    "Ukraine":              ["UKR", "UA"],
    "Turkey":               ["TUR", "TR", "Turkiye", "Türkiye"],
    "Sweden":               ["SWE", "SE"],
    "Norway":               ["NOR", "NO"],
    "Wales":                ["WAL"],
    "Slovakia":             ["SVK", "SK"],
    "Slovenia":             ["SVN", "SI"],
    "Albania":              ["ALB", "AL"],
    "Greece":               ["GRE", "GRC", "GR"],
    "Georgia":              ["GEO", "GE"],
    "Iceland":              ["ISL", "IS"],
    "Finland":              ["FIN", "FI"],
    "Bosnia and Herzegovina": ["BIH", "BIH", "Bosnia"],
    "North Macedonia":      ["MKD", "MK", "Macedonia", "FYR Macedonia"],
    "Montenegro":           ["MNE", "ME"],
    "Kosovo":               ["XKX"],
    "Republic of Ireland":  ["IRL", "Ireland", "IE"],
    "Northern Ireland":     ["NIR"],
    "Luxembourg":           ["LUX", "LU"],
    "Bulgaria":             ["BUL", "BGR", "BG"],
    "Israel":               ["ISR", "IL"],
    "Kazakhstan":           ["KAZ", "KZ"],

    # ── CAF ───────────────────────────────────────────────────────────────
    "Morocco":              ["MAR", "MOR", "MA"],
    "Senegal":              ["SEN", "SN"],
    "Cameroon":             ["CMR", "CM"],
    "Ghana":                ["GHA", "GH"],
    "Mali":                 ["MLI", "ML"],
    "Egypt":                ["EGY", "EG"],
    "South Africa":         ["RSA", "ZA", "SAF"],
    "Tunisia":              ["TUN", "TN"],
    "DR Congo":             ["COD", "Congo DR", "Congo DRC", "Congo, DR",
                             "Democratic Republic of the Congo", "Zaire", "CD"],
    "Nigeria":              ["NGA", "NG"],
    "Ivory Coast":          ["CIV", "Côte d'Ivoire", "Cote d'Ivoire", "CI"],
    "Algeria":              ["ALG", "DZA", "DZ"],
    "Kenya":                ["KEN", "KE"],
    "Tanzania":             ["TAN", "TZA", "TZ"],
    "Zambia":               ["ZAM", "ZMB", "ZM"],
    "Uganda":               ["UGA", "UG"],
    "Zimbabwe":             ["ZIM", "ZWE", "ZW"],
    "Ethiopia":             ["ETH", "ET"],
    "Burkina Faso":         ["BFA", "BF"],
    "Gabon":                ["GAB", "GA"],
    "Cape Verde":           ["CPV", "CV", "Cabo Verde"],
    "Gambia":               ["GAM", "GMB", "GM", "The Gambia"],
    "Guinea":               ["GUI", "GIN", "GN"],
    "Rwanda":               ["RWA", "RW"],
    "Mozambique":           ["MOZ", "MZ"],
    "Benin":                ["BEN", "BJ"],
    "Comoros":              ["COM", "KM"],
    "Equatorial Guinea":    ["EQG", "GNQ", "GQ"],
    "Madagascar":           ["MAD", "MDG", "MG"],
    "Malawi":               ["MWI", "MW"],
    "Mauritania":           ["MTN", "MRT", "MR"],
    "Namibia":              ["NAM", "NA"],
    "Niger":                ["NIG", "NER", "NE"],
    "Sierra Leone":         ["SLE", "SL"],
    "Sudan":                ["SDN", "SD"],

    # ── AFC ───────────────────────────────────────────────────────────────
    "Japan":                ["JPN", "JP"],
    "South Korea":          ["KOR", "Korea Republic", "KR"],
    "Iran":                 ["IRN", "IR Iran", "IR"],
    "Australia":            ["AUS", "AU"],
    "Saudi Arabia":         ["KSA", "SAU", "SA"],
    "Uzbekistan":           ["UZB", "UZ"],
    "Qatar":                ["QAT", "QA"],
    "Jordan":               ["JOR", "JO"],
    "Iraq":                 ["IRQ", "IQ"],
    "United Arab Emirates": ["UAE", "ARE", "AE"],
    "Oman":                 ["OMA", "OMN", "OM"],
    "Bahrain":              ["BHR", "BH"],
    "Kuwait":               ["KUW", "KWT", "KW"],
    "China":                ["CHN", "China PR", "PRC", "CN"],
    "India":                ["IND", "IN"],
    "Indonesia":            ["IDN", "ID"],
    "Thailand":             ["THA", "TH"],
    "Vietnam":              ["VIE", "VNM", "VN"],
    "Malaysia":             ["MAS", "MYS", "MY"],
    "Philippines":          ["PHI", "PHL", "PH"],
    "North Korea":          ["PRK", "Korea DPR", "KP"],
    "Taiwan":               ["TPE", "Chinese Taipei", "TW"],
    "Tajikistan":           ["TJK", "TJ"],
    "Kyrgyzstan":           ["KGZ", "KG", "Kyrgyz Republic"],
    "Palestine":            ["PSE", "PS"],
    "Lebanon":              ["LBN", "LB"],
    "Syria":                ["SYR", "SY"],
    "Brunei":               ["BRU", "BRN", "BN", "Brunei Darussalam"],
    "Singapore":            ["SIN", "SGP", "SG"],
    "Hong Kong":            ["HKG", "HK"],
    "Turkmenistan":         ["TKM", "TM"],

    # ── OFC ───────────────────────────────────────────────────────────────
    "New Zealand":          ["NZL", "NZ"],
    "Papua New Guinea":     ["PNG", "PG"],
    "Tahiti":               ["PYF"],
    "New Caledonia":        ["NCL"],
    "Solomon Islands":      ["SOL", "SLB", "SB"],
    "Fiji":                 ["FIJ", "FJI", "FJ"],
    "Vanuatu":              ["VAN", "VUT", "VU"],
    "Samoa":                ["SAM", "WSM", "WS"],

    # ── Misc / Caribbean ──────────────────────────────────────────────────
    "Puerto Rico":          ["PUR", "PRI"],
    "Guatemala":            ["GUA", "GTM"],
    "Dominican Republic":   ["DOM", "DO"],
    "Barbados":             ["BAR", "BRB", "BB"],
    "Antigua and Barbuda":  ["ATG", "AG"],
    "Saint Kitts and Nevis": ["SKN", "KNA", "KN",
                              "St Kitts and Nevis", "St. Kitts and Nevis"],
    "Saint Lucia":          ["LCA", "LC", "St Lucia", "St. Lucia"],
    "Saint Vincent and the Grenadines": [
                             "VIN", "VC", "St Vincent and the Grenadines"],
    "Grenada":              ["GRN", "GRD", "GD"],
    "Dominica":             ["DMA", "DM"],
    "Nicaragua":            ["NCA", "NIC", "NI"],
    "Belize":               ["BLZ", "BZ"],
    "São Tomé and Príncipe": ["STP", "Sao Tome and Principe", "ST"],
    "Djibouti":             ["DJI", "DJ"],
}

# ── Reverse lookup: alias → canonical ──────────────────────────────────────

_REVERSE: dict[str, str] = {}
for canonical, aliases in ALIASES.items():
    _REVERSE[canonical.lower()] = canonical
    for alias in aliases:
        _REVERSE[alias.lower()] = canonical


def normalise(name: str) -> str:
    """Return canonical team name; falls back to the input if unknown."""
    return _REVERSE.get(name.strip().lower(), name.strip())


def normalise_series(series):
    """Vectorised normalise for a pandas Series."""
    return series.map(lambda x: normalise(x) if isinstance(x, str) else x)


# ── WC 2026 qualified teams (48) — confirmed from tournament draw ────────────
# Groups sourced from the official tournament draw.

WC2026_TEAMS: dict[str, str] = {
    # Group A
    "Czech Republic":           "UEFA",
    "Mexico":                   "CONCACAF",
    "South Africa":             "CAF",
    "South Korea":              "AFC",

    # Group B
    "Bosnia and Herzegovina":   "UEFA",
    "Canada":                   "CONCACAF",
    "Qatar":                    "AFC",
    "Switzerland":              "UEFA",

    # Group C
    "Brazil":                   "CONMEBOL",
    "Haiti":                    "CONCACAF",
    "Morocco":                  "CAF",
    "Scotland":                 "UEFA",

    # Group D
    "Australia":                "AFC",
    "Paraguay":                 "CONMEBOL",
    "Turkey":                   "UEFA",
    "United States":            "CONCACAF",

    # Group E
    "Curaçao":                  "CONCACAF",
    "Ecuador":                  "CONMEBOL",
    "Germany":                  "UEFA",
    "Ivory Coast":              "CAF",

    # Group F
    "Japan":                    "AFC",
    "Netherlands":              "UEFA",
    "Sweden":                   "UEFA",
    "Tunisia":                  "CAF",

    # Group G
    "Belgium":                  "UEFA",
    "Egypt":                    "CAF",
    "Iran":                     "AFC",
    "New Zealand":              "OFC",

    # Group H
    "Cape Verde":               "CAF",
    "Saudi Arabia":             "AFC",
    "Spain":                    "UEFA",
    "Uruguay":                  "CONMEBOL",

    # Group I
    "France":                   "UEFA",
    "Iraq":                     "AFC",
    "Norway":                   "UEFA",
    "Senegal":                  "CAF",

    # Group J
    "Algeria":                  "CAF",
    "Argentina":                "CONMEBOL",
    "Austria":                  "UEFA",
    "Jordan":                   "AFC",

    # Group K
    "Colombia":                 "CONMEBOL",
    "DR Congo":                 "CAF",
    "Portugal":                 "UEFA",
    "Uzbekistan":               "AFC",

    # Group L
    "Croatia":                  "UEFA",
    "England":                  "UEFA",
    "Ghana":                    "CAF",
    "Panama":                   "CONCACAF",
}

WC2026_TEAM_NAMES: set[str] = set(WC2026_TEAMS.keys())


def is_wc2026_team(name: str) -> bool:
    return normalise(name) in WC2026_TEAM_NAMES


def confederation(name: str) -> str | None:
    return WC2026_TEAMS.get(normalise(name))

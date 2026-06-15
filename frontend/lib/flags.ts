// Maps canonical team names → ISO 3166-1 alpha-2 (or subdivision) codes
// for use with flagcdn.com: https://flagcdn.com/w40/{code}.png

const FLAG_CODES: Record<string, string> = {
  // Group A
  "Czech Republic":         "cz",
  "Mexico":                 "mx",
  "South Africa":           "za",
  "South Korea":            "kr",
  // Group B
  "Bosnia and Herzegovina": "ba",
  "Canada":                 "ca",
  "Qatar":                  "qa",
  "Switzerland":            "ch",
  // Group C
  "Brazil":                 "br",
  "Haiti":                  "ht",
  "Morocco":                "ma",
  "Scotland":               "gb-sct",
  // Group D
  "Australia":              "au",
  "Paraguay":               "py",
  "Turkey":                 "tr",
  "United States":          "us",
  // Group E
  "Curaçao":                "cw",
  "Ecuador":                "ec",
  "Germany":                "de",
  "Ivory Coast":            "ci",
  // Group F
  "Japan":                  "jp",
  "Netherlands":            "nl",
  "Sweden":                 "se",
  "Tunisia":                "tn",
  // Group G
  "Belgium":                "be",
  "Egypt":                  "eg",
  "Iran":                   "ir",
  "New Zealand":            "nz",
  // Group H
  "Cape Verde":             "cv",
  "Saudi Arabia":           "sa",
  "Spain":                  "es",
  "Uruguay":                "uy",
  // Group I
  "France":                 "fr",
  "Iraq":                   "iq",
  "Norway":                 "no",
  "Senegal":                "sn",
  // Group J
  "Algeria":                "dz",
  "Argentina":              "ar",
  "Austria":                "at",
  "Jordan":                 "jo",
  // Group K
  "Colombia":               "co",
  "DR Congo":               "cd",
  "Portugal":               "pt",
  "Uzbekistan":             "uz",
  // Group L
  "Croatia":                "hr",
  "England":                "gb-eng",
  "Ghana":                  "gh",
  "Panama":                 "pa",
};

export function getFlagUrl(teamName: string, width: 20 | 40 | 80 | 160 = 40): string {
  const code = FLAG_CODES[teamName];
  if (!code) return "";
  return `https://flagcdn.com/w${width}/${code}.png`;
}

export default FLAG_CODES;

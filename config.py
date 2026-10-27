"""Edit this file to tune what the scraper keeps and how it ranks things."""

# Final round / event must be at least this many days from today.
MIN_DAYS_TO_FINAL = 15

# Days before the registration deadline to get calendar reminders.
REMINDER_DAYS_BEFORE = [3, 1]

# Anything scoring at or above this lands on the "Top Picks" sheet.
TOP_PICK_SCORE = 60

# Unstop is an India-first platform: online events there carry no address, so we
# tag them with this country. Set to "" to leave them unlabelled instead.
UNSTOP_DEFAULT_COUNTRY = "India"

# ---------------------------------------------------------------- themes
# Matched (case-insensitive) against title + description + category.
THEMES = {
    "Case / Business": [
        "case comp", "case competition", "case study", "case challenge", "case-study",
        "consulting", "strategy", "b-plan", "business plan", "bplan", "marketing",
        "product management", "prodman", "finance case", "valuation", "stock pitch",
        "venture capital", "pitch", "ideathon", "policy", "hr case", "brand",
        "innovation challenge", "management consulting", "business analysis",
        "investment research", "corporate finance", "founder’s office", "founder's office",
        "human resources", "business development",
    ],
    "Hackathon": [
        "hackathon", "hack-a-thon", "hacka", "hackday", "hackfest", "hack fest", "hacktopia",
        "hacknova", "buildathon", "datathon", "data-thon", "designathon", "makeathon",
        "codeathon", "innovathon", "buildfest",
    ],
    "Psychology": [
        "psycholog", "mental health", "mental-health", "behavioural science", "behavioral science",
        "behavioural econom", "behavioral econom", "cognitive science", "neuroscience",
        "neuromarketing", "counselling", "counseling", "emotional intelligence", "consumer behav",
        "consumer psych", "mindfulness", "organisational behav", "organizational behav",
        "human behaviour", "human behavior", "well-being", "wellbeing",
    ],
}
# Case / Hackathon are matched on title + category only (descriptions are too noisy).
# Psychology also checks the description, but needs this many distinct keyword hits there.
PSYCH_DESC_MIN_HITS = 2

# Organisers matching these are never counted as companies (student chapters etc.).
NOT_CORPORATE = ["developer group", "student", "club", "society", "chapter", "community", "gdg"]

# Organiser keywords -> (label, score). First match wins, so order matters.
# Matched case-insensitively against the organiser name.
PRESTIGE = [
    # Top B-schools
    ("iim ahmedabad", "Top B-school", 100), ("iim bangalore", "Top B-school", 100),
    ("iim calcutta", "Top B-school", 100), ("(iim), ahmedabad", "Top B-school", 100),
    ("(iim), bangalore", "Top B-school", 100), ("(iim) bangalore", "Top B-school", 100),
    ("(iim), calcutta", "Top B-school", 100), ("(iim) calcutta", "Top B-school", 100),
    # look-alikes first (first match wins)
    ("indian school of business & finance", "Other org", 25),
    ("indian school of business and finance", "Other org", 25),
    ("indian school of business", "Top B-school", 100), ("isb", "Top B-school", 100),
    ("xlri), delhi", "Top B-school", 80), ("xlri delhi", "Top B-school", 80),
    ("xlri", "Top B-school", 92), ("faculty of management studies", "Top B-school", 95),
    ("fms", "Top B-school", 95), ("spjimr", "Top B-school", 92), ("s.p. jain institute", "Top B-school", 92),
    ("management development institute", "Top B-school", 88), ("mdi", "Top B-school", 88),
    ("jamnalal bajaj", "Top B-school", 88), ("jbims", "Top B-school", 88),
    ("indian institute of foreign trade", "Top B-school", 85), ("iift", "Top B-school", 85),
    ("indian institute of management", "Top B-school", 85), ("iim", "Top B-school", 85),
    ("department of management studies", "Top B-school", 80),
    ("nmims", "Good B-school", 70), ("narsee monjee institute", "Good B-school", 70),
    ("symbiosis institute of business", "Good B-school", 70), ("sibm", "Good B-school", 70),
    ("imt", "Good B-school", 65), ("institute of management technology", "Good B-school", 65),
    ("great lakes", "Good B-school", 65), ("tapmi", "Good B-school", 62),
    ("xavier institute", "Good B-school", 65), ("ximb", "Good B-school", 70),
    # Top DU colleges
    ("shri ram college of commerce", "Top DU", 95), ("srcc", "Top DU", 95),
    ("st. stephen", "Top DU", 92), ("st stephen", "Top DU", 92),
    ("lady shri ram", "Top DU", 90), ("lsr", "Top DU", 90),
    ("hindu college", "Top DU", 88), ("hansraj", "Top DU", 85),
    ("miranda house", "Top DU", 85), ("kirori mal", "Top DU", 80),
    ("ramjas", "Top DU", 80), ("shaheed sukhdev", "Top DU", 85), ("sscbs", "Top DU", 85),
    ("sri venkateswara", "Top DU", 80), ("jesus and mary", "Top DU", 75),
    ("gargi", "Top DU", 72), ("indraprastha college", "Top DU", 72),
    ("daulat ram", "Top DU", 72), ("kamala nehru", "Top DU", 70),
    ("deshbandhu", "Top DU", 65), ("sgtb khalsa", "Top DU", 75), ("sri guru tegh bahadur", "Top DU", 75),
    ("delhi college of arts", "Top DU", 70), ("dcac", "Top DU", 70),
    ("maitreyi", "Top DU", 65), ("ramanujan college", "Top DU", 60), ("kalindi", "Top DU", 60),
    ("ram lal anand", "DU (other)", 58), ("aryabhatta college", "DU (other)", 58),
    ("shaheed bhagat singh", "DU (other)", 58), ("motilal nehru", "DU (other)", 58),
    ("dyal singh", "DU (other)", 58), ("pgdav", "DU (other)", 58), ("rajdhani college", "DU (other)", 58),
    ("acharya narendra dev", "DU (other)", 58), ("keshav mahavidyalaya", "DU (other)", 60),
    ("shyama prasad", "DU (other)", 55), ("atma ram sanatan", "DU (other)", 62),
    ("sri aurobindo college", "DU (other)", 58), ("zakir husain", "DU (other)", 58),
    ("lakshmibai college", "DU (other)", 55), ("hans raj", "Top DU", 85),
    ("university of delhi", "DU (other)", 58), ("delhi university", "DU (other)", 58),
    ("(du)", "DU (other)", 58),
    # Other strong institutions
    ("indian institute of technology", "IIT / Top Uni", 72), ("(iit)", "IIT / Top Uni", 72),
    ("bits pilani", "IIT / Top Uni", 70), ("ashoka university", "IIT / Top Uni", 70),
    ("st. xavier's college", "IIT / Top Uni", 68), ("christ university", "IIT / Top Uni", 60),
    ("narsee monjee college", "IIT / Top Uni", 62), ("delhi technological", "IIT / Top Uni", 60),
    ("plaksha", "IIT / Top Uni", 60), ("nift", "IIT / Top Uni", 60),
    ("national institute of mental health", "IIT / Top Uni", 75), ("nimhans", "IIT / Top Uni", 75),
    ("tata institute of social sciences", "IIT / Top Uni", 75), ("tiss", "IIT / Top Uni", 75),
]

# Known companies -> "Corporate" tier.
CORPORATES = [
    "hindustan unilever", "hul", "unilever", "itc", "procter", "p&g", "nestle", "l'oreal", "loreal",
    "tata", "reliance", "mahindra", "aditya birla", "godrej", "marico", "dabur", "asian paints",
    "bajaj", "hero", "maruti", "flipkart", "amazon", "google", "microsoft", "meta", "apple", "adobe",
    "walmart", "myntra", "zomato", "swiggy", "paytm", "razorpay", "cred", "meesho", "nykaa", "ola",
    "uber", "phonepe", "zepto", "infosys", "wipro", "tcs", "hcl", "cognizant", "capgemini", "accenture",
    "deloitte", "kpmg", "pwc", "ernst", "ey ", "mckinsey", "bcg", "boston consulting", "bain",
    "goldman", "jp morgan", "jpmorgan", "morgan stanley", "american express", "amex", "mastercard",
    "visa", "hdfc", "icici", "axis bank", "kotak", "sbi", "airtel", "jio", "samsung", "coca-cola",
    "pepsico", "diageo", "pidilite", "titan", "bosch", "siemens", "shell", "nvidia", "intel", "ibm",
    "oracle", "salesforce", "cisco", "qualcomm", "media.net", "de shaw", "d. e. shaw", "jane street",
    "barclays", "citi", "hsbc", "standard chartered", "ab inbev", "colgate", "cadbury", "mondelez",
    "nebius", "paypal", "openai", "anthropic", "aws", "databricks", "mongodb", "github",
]
CORPORATE_SCORE = 75

# Score for organisers that don't match anything above.
DEFAULT_COLLEGE_SCORE = 30
DEFAULT_ORG_SCORE = 25
PSYCHOLOGY_BONUS = 25  # psychology-themed comps get pushed up

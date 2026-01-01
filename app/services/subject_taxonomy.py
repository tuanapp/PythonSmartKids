"""
Subject Taxonomy - Hierarchical Structure for All Subjects
Subject -> Topic -> SubTopic -> Concept

This taxonomy supports granular question categorization across all subjects.
"""

SUBJECT_TAXONOMY = {
    "Math": {
        "Number Operations": {
            "Number Sense": [
                "Place value", "Writing numbers in words", "Number forms",
                "Comparing and ordering numbers"
            ],
            "Basic Arithmetic": [
                "Addition single digit", "Addition multi-digit", "Subtraction single digit",
                "Subtraction multi-digit", "Multiplication tables", "Multiplication multi-digit",
                "Division basic", "Division with remainders"
            ],
            "Advanced Operations": [
                "Order of operations (PEMDAS)", "Mental math strategies",
                "Estimation and rounding", "Prime factorization"
            ]
        },
        "Fractions & Decimals": {
            "Fractions": [
                "Understanding fractions", "Equivalent fractions", "Simplifying fractions",
                "Adding fractions", "Subtracting fractions", "Multiplying fractions",
                "Dividing fractions", "Mixed numbers", "Improper fractions",
                "Fraction to decimal conversion"
            ],
            "Decimals": [
                "Place value decimals", "Adding decimals", "Subtracting decimals",
                "Multiplying decimals", "Dividing decimals", "Decimal to fraction conversion"
            ],
            "Percentages": [
                "Understanding percentages", "Percentage calculations",
                "Percentage increase/decrease", "Finding percentages of quantities"
            ],
            "Ratios & Proportions": [
                "Understanding ratios", "Simplifying ratios", "Equivalent ratios",
                "Solving ratio problems", "Proportions", "Recipe and mixture problems"
            ]
        },
        "Geometry": {
            "2D Shapes": [
                "Identifying shapes", "Properties of triangles", "Properties of quadrilaterals",
                "Properties of rectangles and squares", "Circles and their properties",
                "Perimeter calculations", "Area calculations"
            ],
            "3D Shapes": [
                "Identifying 3D shapes", "Surface area", "Volume calculations",
                "Nets of 3D shapes"
            ],
            "Angles & Lines": [
                "Types of angles (acute, right, obtuse, straight, reflex)",
                "Measuring angles", "Angle relationships",
                "Parallel and perpendicular lines", "Symmetry"
            ]
        },
        "Algebra": {
            "Expressions": [
                "Variables and constants", "Algebraic expressions", "Simplifying expressions",
                "Evaluating expressions"
            ],
            "Equations": [
                "Solving linear equations", "Word problems with equations",
                "Inequalities", "Systems of equations"
            ]
        },
        "Measurement": {
            "Units": [
                "Length measurements", "Weight/mass measurements", "Capacity/volume measurements",
                "Time calculations", "Unit conversions"
            ],
            "Money": [
                "Counting money", "Making change", "Word problems with money"
            ]
        },
        "Data & Statistics": {
            "Data Representation": [
                "Reading bar graphs", "Reading line graphs", "Reading pie charts",
                "Creating graphs", "Interpreting tables"
            ],
            "Statistics": [
                "Mean (average)", "Median", "Mode", "Range", "Probability basics"
            ]
        },
        "Word Problems": {
            "Application Problems": [
                "Single-step word problems", "Multi-step word problems",
                "Real-world applications", "Problem-solving strategies"
            ]
        }
    },
    "English": {
        "Grammar": {
            "Parts of Speech": [
                "Nouns (common, proper)", "Pronouns", "Verbs (action, linking)",
                "Adjectives", "Adjective order", "Adverbs", "Adverb placement",
                "Prepositions", "Conjunctions", "Interjections"
            ],
            "Tenses": [
                "Simple present", "Simple past", "Simple future",
                "Present continuous", "Past continuous", "Present perfect",
                "Past perfect", "Tense consistency"
            ],
            "Sentence Structure": [
                "Subject and predicate", "Simple sentences", "Compound sentences",
                "Complex sentences", "Subject-verb agreement", "Verb forms"
            ],
            "Punctuation": [
                "Periods and capitals", "Question marks", "Exclamation marks",
                "Commas", "Apostrophes", "Quotation marks"
            ]
        },
        "Vocabulary": {
            "Word Meaning": [
                "Synonyms", "Antonyms", "Homonyms", "Context clues",
                "Multiple meanings", "Prefixes", "Suffixes", "Root words"
            ],
            "Word Usage": [
                "Commonly confused words", "Idioms", "Figurative language",
                "Academic vocabulary"
            ]
        },
        "Reading Comprehension": {
            "Literal Understanding": [
                "Main idea", "Supporting details", "Sequence of events",
                "Cause and effect", "Compare and contrast"
            ],
            "Inferential Understanding": [
                "Making inferences", "Drawing conclusions", "Predicting outcomes",
                "Author's purpose", "Point of view"
            ],
            "Text Types": [
                "Fiction comprehension", "Non-fiction comprehension",
                "Poetry analysis", "Drama/dialogue"
            ]
        },
        "Writing": {
            "Composition": [
                "Paragraph structure", "Essay organization", "Topic sentences",
                "Supporting details", "Conclusions"
            ],
            "Writing Types": [
                "Narrative writing", "Descriptive writing", "Expository writing",
                "Persuasive writing", "Creative writing"
            ],
            "Mechanics": [
                "Spelling", "Capitalization", "Grammar in writing",
                "Sentence variety", "Editing and revising"
            ]
        },
        "Phonics & Spelling": {
            "Phonics": [
                "Letter sounds", "Blending", "Digraphs", "Vowel patterns",
                "Silent letters"
            ],
            "Spelling Patterns": [
                "CVC words", "Long vowel patterns", "Spelling rules",
                "Irregular spellings", "High-frequency words"
            ]
        }
    },
    "Science": {
        "Life Science": {
            "Living Things": [
                "Characteristics of life", "Classification of organisms",
                "Life cycles", "Habitats and ecosystems"
            ],
            "Plant Life": [
                "Plant parts and functions", "Photosynthesis",
                "Pollination process", "Self-pollination vs cross-pollination",
                "Pollinators (bees, butterflies, wind, water)", "Pollen and reproduction",
                "Attracting pollinators", "Pollination and food production",
                "Factors affecting pollination", "Human impact on pollination"
            ],
            "Human Body": [
                "Body systems overview", "Digestive system", "Respiratory system",
                "Circulatory system", "Skeletal system", "Muscular system",
                "Nervous system", "Health and nutrition"
            ],
            "Ecology": [
                "Food chains", "Food webs", "Producers and consumers",
                "Decomposers", "Ecosystems", "Biodiversity",
                "Adaptations", "Ecosystem health"
            ]
        },
        "Physical Science": {
            "Matter": [
                "States of matter", "Properties of matter", "Physical changes",
                "Chemical changes", "Mixtures and solutions", "Atoms and molecules"
            ],
            "Energy": [
                "Forms of energy", "Energy transfer", "Heat energy",
                "Light energy", "Sound energy", "Electrical energy",
                "Conservation of energy"
            ],
            "Forces & Motion": [
                "Types of forces", "Gravity", "Friction", "Magnetism",
                "Speed and velocity", "Simple machines", "Newton's laws"
            ]
        },
        "Earth & Space Science": {
            "Earth Systems": [
                "Rocks and minerals", "Soil formation", "Water cycle",
                "Weather patterns", "Climate", "Natural resources"
            ],
            "Space": [
                "Solar system", "Planets", "Sun and stars", "Moon phases",
                "Earth's rotation and revolution", "Day and night", "Seasons"
            ]
        },
        "Scientific Inquiry": {
            "Process Skills": [
                "Observing", "Measuring", "Classifying", "Predicting",
                "Experimenting", "Collecting data", "Drawing conclusions"
            ],
            "Tools & Safety": [
                "Scientific tools", "Lab safety", "Making models"
            ]
        }
    },
    "General Knowledge": {
        "Geography": {
            "World Geography": [
                "Continents", "Oceans", "Countries and capitals",
                "Landforms", "Maps and globes"
            ],
            "Sri Lanka Geography": [
                "Provinces", "Districts", "Major cities", "Rivers and mountains",
                "Cultural sites"
            ]
        },
        "History": {
            "World History": [
                "Ancient civilizations", "Historical figures",
                "Major events", "Inventions"
            ],
            "Sri Lankan History": [
                "Ancient kingdoms", "Colonial period", "Independence",
                "National heroes"
            ]
        },
        "Current Affairs": {
            "General Knowledge": [
                "World events", "Sports", "Technology", "Environment",
                "Famous personalities"
            ]
        }
    },
    "History": {
        "Ancient History": {
            "Ancient Civilizations": [
                "Mesopotamian civilizations", "Ancient Egypt", "Ancient Greece",
                "Ancient Rome", "Indus Valley civilization", "Ancient China"
            ],
            "Sri Lankan Ancient History": [
                "Anuradhapura kingdom", "Polonnaruwa kingdom", "Sigiriya",
                "Ancient kings", "Buddhist arrival"
            ]
        },
        "Medieval & Modern History": {
            "Medieval Period": [
                "Middle Ages", "Knights and castles", "Feudal system",
                "Renaissance", "Sri Lankan medieval kingdoms"
            ],
            "Colonial Period": [
                "European exploration", "Colonial empires", "Portuguese in Sri Lanka",
                "Dutch in Sri Lanka", "British in Sri Lanka"
            ],
            "Modern History": [
                "World Wars", "Independence movements", "Sri Lankan independence",
                "Cold War", "Contemporary history"
            ]
        },
        "Historical Figures": {
            "World Leaders": [
                "Kings and queens", "Presidents", "Revolutionary leaders",
                "Inventors and scientists", "Explorers"
            ],
            "Sri Lankan Heroes": [
                "National heroes", "Freedom fighters", "Cultural figures",
                "Historical rulers"
            ]
        }
    },
    "Geography": {
        "Physical Geography": {
            "Landforms": [
                "Mountains", "Rivers", "Valleys", "Plains",
                "Deserts", "Islands", "Peninsulas"
            ],
            "Water Bodies": [
                "Oceans", "Seas", "Lakes", "Rivers",
                "Waterfalls", "Glaciers"
            ],
            "Climate & Weather": [
                "Climate zones", "Weather patterns", "Seasons",
                "Natural disasters", "Temperature and rainfall"
            ]
        },
        "Political Geography": {
            "World Geography": [
                "Continents", "Countries and capitals", "Major cities",
                "Flags", "Borders and boundaries"
            ],
            "Sri Lankan Geography": [
                "Provinces and capitals", "Districts", "Major cities",
                "Administrative divisions", "National symbols"
            ],
            "Administrative Divisions": [
                "Grama Niladhari Division", "Divisional Secretariat",
                "Administrative hierarchy", "School location identification"
            ],
            "Map Skills & Directions": [
                "Cardinal directions (North, South, East, West)",
                "Finding directions without compass", "Using the sun for direction",
                "Reading maps", "School premises mapping", "Symbols and plans"
            ]
        },
        "Human Geography": {
            "Population & Culture": [
                "Population distribution", "Languages", "Religions",
                "Cultural diversity", "Traditions"
            ],
            "Economic Geography": [
                "Resources", "Industries", "Agriculture",
                "Trade", "Tourism"
            ]
        }
    },
    "Nature": {
        "Animals": {
            "Animal Classification": [
                "Mammals", "Birds", "Reptiles", "Amphibians",
                "Fish", "Insects", "Invertebrates"
            ],
            "Animal Habitats": [
                "Forest animals", "Desert animals", "Ocean animals",
                "Arctic animals", "Rainforest animals", "Sri Lankan wildlife"
            ],
            "Animal Behavior": [
                "Feeding habits", "Migration", "Hibernation",
                "Reproduction", "Social behavior", "Camouflage"
            ]
        },
        "Plants": {
            "Plant Types": [
                "Trees", "Shrubs", "Herbs", "Flowering plants",
                "Non-flowering plants", "Aquatic plants"
            ],
            "Plant Parts & Functions": [
                "Roots", "Stems", "Leaves", "Flowers",
                "Fruits and seeds", "Photosynthesis"
            ],
            "Plant Habitats": [
                "Forest plants", "Desert plants", "Wetland plants",
                "Sri Lankan flora", "Medicinal plants"
            ]
        },
        "Ecosystems": {
            "Biomes": [
                "Rainforests", "Deserts", "Grasslands",
                "Tundra", "Wetlands", "Ocean ecosystems"
            ],
            "Food Chains & Webs": [
                "Producers", "Consumers", "Decomposers",
                "Food chains", "Energy flow"
            ],
            "Conservation": [
                "Endangered species", "Wildlife protection",
                "Habitat conservation", "Environmental issues"
            ]
        }
    },
    "Space": {
        "Solar System": {
            "Sun & Planets": [
                "The Sun", "Inner planets (Mercury, Venus, Earth, Mars)",
                "Outer planets (Jupiter, Saturn, Uranus, Neptune)",
                "Planet characteristics", "Planetary orbits"
            ],
            "Moons & Other Objects": [
                "Earth's Moon", "Moons of other planets",
                "Asteroids", "Comets", "Dwarf planets"
            ]
        },
        "Stars & Galaxies": {
            "Stars": [
                "Star formation", "Star types", "Constellations",
                "Star life cycles", "Famous stars"
            ],
            "Galaxies & Universe": [
                "Milky Way", "Galaxy types", "The Universe",
                "Big Bang theory", "Black holes"
            ]
        },
        "Space Exploration": {
            "Missions & Technology": [
                "Moon landing", "Mars missions", "Space stations",
                "Satellites", "Space telescopes", "Rockets and spacecraft"
            ],
            "Astronauts & Discoveries": [
                "Famous astronauts", "Space achievements",
                "Life in space", "Future of space exploration"
            ]
        }
    },
    "Technology": {
        "Computer Basics": {
            "Hardware": [
                "Input devices", "Output devices", "Processing unit",
                "Storage devices", "Parts of computer", "Peripherals"
            ],
            "Software": [
                "Operating systems", "Applications", "System software",
                "File management", "User interfaces"
            ]
        },
        "Internet & Digital World": {
            "Internet Basics": [
                "World Wide Web (www)", "Web browsers", "Search engines",
                "Email", "Online communication", "Internet Service Providers (ISP)"
            ],
            "Digital Literacy & Safety": [
                "Digital citizenship", "Responsible online behavior",
                "Cybersecurity", "Phishing and suspicious emails",
                "Online privacy", "Public Wi-Fi safety", "Digital footprint"
            ]
        },
        "Digital Tools & Applications": {
            "Productivity Software": [
                "Spreadsheet software (Excel)", "Data analysis tools",
                "Graphics editors", "Databases"
            ],
            "Computer Graphics": [
                "Pixels and images", "Display technology",
                "Image editing"
            ]
        },
        "Inventions & Innovation": {
            "Historical Inventions": [
                "Ancient inventions", "Industrial revolution inventions",
                "Modern inventions", "Famous inventors"
            ],
            "Modern Technology": [
                "Smartphones", "Artificial Intelligence", "Robotics",
                "Virtual Reality", "3D Printing", "Renewable energy"
            ],
            "Programming & Coding": [
                "Algorithms", "Sorting algorithms", "Sequences and loops",
                "Step-by-step procedures", "Conditionals",
                "Variables", "Basic programming concepts"
            ],
            "Robotics & Artificial Intelligence": [
                "Robots in manufacturing", "Industrial robotics",
                "Artificial Intelligence basics", "AI applications in everyday life",
                "Future technology trends"
            ]
        }
    },
    "IT": {
        "Computer Basics": {
            "Hardware": [
                "Input devices", "Output devices", "Processing unit (CPU)",
                "Storage devices", "Parts of computer", "Motherboard", "Mouse", "Printer"
            ],
            "Software": [
                "Operating systems", "Applications", "System software",
                "File management", "Folders and files"
            ]
        },
        "Internet & Digital Literacy": {
            "Internet Basics": [
                "World Wide Web (www)", "Web browsers", "Search engines",
                "Email", "Internet Service Providers (ISP)", "Online communication"
            ],
            "Digital Safety & Citizenship": [
                "Digital citizenship", "Responsible online behavior",
                "Cybersecurity", "Phishing and suspicious emails",
                "Public Wi-Fi safety", "Online privacy", "Protecting personal data"
            ]
        },
        "Digital Tools & Applications": {
            "Productivity Software": [
                "Spreadsheet software (Microsoft Excel)", "Data analysis and presentation",
                "Graphics editors", "Databases and data management"
            ],
            "Computer Graphics": [
                "Pixels and image display", "Display technology", "Screen resolution"
            ]
        },
        "Programming & Technology": {
            "Programming Concepts": [
                "Algorithms", "Sorting algorithms", "Loops in programming",
                "Step-by-step procedures", "Sequences", "Conditionals"
            ],
            "Robotics & AI": [
                "Robots in manufacturing", "Industrial robotics",
                "Artificial Intelligence basics", "AI applications in everyday life"
            ]
        }
    },
    "French": {
        "Vocabulary": {
            "Basic Words": [
                "Numbers (nombres)", "Colors (couleurs)", "Days of week (jours)",
                "Months (mois)", "Family (famille)", "Animals (animaux)"
            ],
            "Common Phrases": [
                "Greetings (salutations)", "Introductions (présentations)",
                "Polite expressions", "Questions (questions)", "Common responses"
            ],
            "Thematic Vocabulary": [
                "Food (nourriture)", "Clothing (vêtements)", "House (maison)",
                "School (école)", "Weather (temps)", "Body parts (corps)"
            ],
            "Numbers & Technology": [
                "Numbers (nombres 0-100)", "Digital vocabulary (website, mouse, email)",
                "Technology terms (ordinateur, internet)"
            ]
        },
        "Grammar": {
            "Nouns & Articles": [
                "Masculine and feminine nouns", "Definite articles (le, la, les)",
                "Indefinite articles (un, une, des)", "Plural forms"
            ],
            "Verbs": [
                "Present tense (présent)", "Common verbs (être, avoir, aller)",
                "Regular -er verbs", "Regular -ir verbs", "Regular -re verbs",
                "Reflexive verbs (s'appeler, se lever)", "Verb conjugation"
            ],
            "Sentence Structure": [
                "Subject-verb-object order", "Questions formation",
                "Negation (ne...pas)", "Adjectives agreement"
            ]
        },
        "Pronunciation & Reading": {
            "Alphabet & Sounds": [
                "French alphabet", "Vowel sounds", "Consonant sounds",
                "Accents (é, è, ê, ë)", "Silent letters"
            ],
            "Reading Skills": [
                "Simple words", "Short sentences", "Basic texts",
                "Comprehension"
            ]
        }
    },
    "Sinhala": {
        "Alphabet & Writing": {
            "Sinhala Alphabet": [
                "Vowels (ස්වර)", "Consonants (ව්යඤ්ජන)",
                "Combined letters (සංයුක්ත අක්ෂර)", "Letter combinations"
            ],
            "Writing Practice": [
                "Letter formation", "Word writing", "Simple sentences",
                "Reading practice"
            ]
        },
        "Vocabulary": {
            "Basic Words": [
                "Numbers (සංඛ්යා)", "Colors (වර්ණ)", "Days (දින)",
                "Months (මාස)", "Family (පවුල)", "Animals (සත්ත්ව)"
            ],
            "Common Phrases": [
                "Greetings (ආචාර)", "Introductions", "Polite expressions",
                "Questions", "Common responses"
            ],
            "Thematic Vocabulary": [
                "Food (ආහාර)", "Clothing (ඇඳුම්)", "House (ගෙදර)",
                "School (පාසල)", "Body parts (ශරීර)", "Nature"
            ]
        },
        "Grammar": {
            "Nouns & Gender": [
                "Common nouns", "Proper nouns", "Plural forms",
                "Gender"
            ],
            "Verbs & Tenses": [
                "Present tense", "Past tense", "Future tense",
                "Common verbs", "Verb conjugation"
            ],
            "Sentence Structure": [
                "Basic sentence formation", "Questions",
                "Subject-object-verb order", "Adjectives"
            ]
        },
        "Reading & Comprehension": {
            "Reading Skills": [
                "Letter recognition", "Word reading", "Simple sentences",
                "Short passages", "Comprehension"
            ]
        }
    }
}

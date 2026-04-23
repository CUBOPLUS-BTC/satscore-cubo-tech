"""
Static test fixtures and reference data for the Magma Bitcoin application.

All data is hard-coded (no I/O).  These constants are used by:
  - Unit tests (deterministic inputs)
  - DatabaseSeeder / DemoDataSeeder
  - API handlers that need fallback reference data
"""

# ---------------------------------------------------------------------------
# DEMO_USERS – 10 pre-defined user profiles
# ---------------------------------------------------------------------------

DEMO_USERS = [
    {"pubkey": "aabbcc" + "0" * 58, "persona": "new_user",    "monthly_usd": 50,   "target_years": 10, "country": "SV"},
    {"pubkey": "ddeeff" + "1" * 58, "persona": "power_saver", "monthly_usd": 500,  "target_years": 20, "country": "US"},
    {"pubkey": "112233" + "2" * 58, "persona": "whale",       "monthly_usd": 5000, "target_years": 5,  "country": "MX"},
    {"pubkey": "445566" + "3" * 58, "persona": "dormant",     "monthly_usd": 100,  "target_years": 15, "country": "SV"},
    {"pubkey": "778899" + "4" * 58, "persona": "diversified", "monthly_usd": 1000, "target_years": 25, "country": "GT"},
    {"pubkey": "aaccee" + "5" * 58, "persona": "dca_weekly",  "monthly_usd": 200,  "target_years": 10, "country": "HN"},
    {"pubkey": "bbddff" + "6" * 58, "persona": "lump_sum",    "monthly_usd": 0,    "target_years": 5,  "country": "NI"},
    {"pubkey": "113355" + "7" * 58, "persona": "student",     "monthly_usd": 25,   "target_years": 30, "country": "CR"},
    {"pubkey": "224466" + "8" * 58, "persona": "retiree",     "monthly_usd": 750,  "target_years": 3,  "country": "PA"},
    {"pubkey": "335577" + "9" * 58, "persona": "developer",   "monthly_usd": 300,  "target_years": 20, "country": "CO"},
]

# ---------------------------------------------------------------------------
# SAMPLE_PRICES – 30 days of daily BTC prices (2024-03-01 to 2024-03-30)
# ---------------------------------------------------------------------------

SAMPLE_PRICES = [
    {"date": "2024-03-01", "timestamp": 1709251200, "open": 61200.0,  "high": 63400.0,  "low": 60500.0,  "close": 62800.0,  "volume": 1823.5},
    {"date": "2024-03-02", "timestamp": 1709337600, "open": 62800.0,  "high": 64100.0,  "low": 61900.0,  "close": 63500.0,  "volume": 2100.2},
    {"date": "2024-03-03", "timestamp": 1709424000, "open": 63500.0,  "high": 64800.0,  "low": 62400.0,  "close": 64200.0,  "volume": 1950.7},
    {"date": "2024-03-04", "timestamp": 1709510400, "open": 64200.0,  "high": 66500.0,  "low": 63800.0,  "close": 65900.0,  "volume": 2341.0},
    {"date": "2024-03-05", "timestamp": 1709596800, "open": 65900.0,  "high": 68100.0,  "low": 65200.0,  "close": 67500.0,  "volume": 2780.3},
    {"date": "2024-03-06", "timestamp": 1709683200, "open": 67500.0,  "high": 69200.0,  "low": 66800.0,  "close": 68400.0,  "volume": 3100.8},
    {"date": "2024-03-07", "timestamp": 1709769600, "open": 68400.0,  "high": 70500.0,  "low": 67900.0,  "close": 69800.0,  "volume": 3450.1},
    {"date": "2024-03-08", "timestamp": 1709856000, "open": 69800.0,  "high": 72000.0,  "low": 68500.0,  "close": 71200.0,  "volume": 4200.5},
    {"date": "2024-03-09", "timestamp": 1709942400, "open": 71200.0,  "high": 72800.0,  "low": 70100.0,  "close": 72300.0,  "volume": 3800.2},
    {"date": "2024-03-10", "timestamp": 1710028800, "open": 72300.0,  "high": 73500.0,  "low": 71200.0,  "close": 73100.0,  "volume": 3200.9},
    {"date": "2024-03-11", "timestamp": 1710115200, "open": 73100.0,  "high": 74200.0,  "low": 71800.0,  "close": 71900.0,  "volume": 3550.4},
    {"date": "2024-03-12", "timestamp": 1710201600, "open": 71900.0,  "high": 73000.0,  "low": 70500.0,  "close": 72500.0,  "volume": 2900.1},
    {"date": "2024-03-13", "timestamp": 1710288000, "open": 72500.0,  "high": 73800.0,  "low": 71900.0,  "close": 73400.0,  "volume": 3100.6},
    {"date": "2024-03-14", "timestamp": 1710374400, "open": 73400.0,  "high": 74500.0,  "low": 72800.0,  "close": 74100.0,  "volume": 2750.3},
    {"date": "2024-03-15", "timestamp": 1710460800, "open": 74100.0,  "high": 74900.0,  "low": 73200.0,  "close": 73800.0,  "volume": 2500.0},
    {"date": "2024-03-16", "timestamp": 1710547200, "open": 73800.0,  "high": 75200.0,  "low": 73100.0,  "close": 74800.0,  "volume": 2600.8},
    {"date": "2024-03-17", "timestamp": 1710633600, "open": 74800.0,  "high": 76000.0,  "low": 74000.0,  "close": 75500.0,  "volume": 2900.5},
    {"date": "2024-03-18", "timestamp": 1710720000, "open": 75500.0,  "high": 76800.0,  "low": 74900.0,  "close": 75900.0,  "volume": 3100.2},
    {"date": "2024-03-19", "timestamp": 1710806400, "open": 75900.0,  "high": 68200.0,  "low": 64100.0,  "close": 65800.0,  "volume": 5800.1},
    {"date": "2024-03-20", "timestamp": 1710892800, "open": 65800.0,  "high": 68000.0,  "low": 64500.0,  "close": 67200.0,  "volume": 4200.7},
    {"date": "2024-03-21", "timestamp": 1710979200, "open": 67200.0,  "high": 68500.0,  "low": 66100.0,  "close": 67900.0,  "volume": 3500.3},
    {"date": "2024-03-22", "timestamp": 1711065600, "open": 67900.0,  "high": 69000.0,  "low": 67200.0,  "close": 68700.0,  "volume": 3000.1},
    {"date": "2024-03-23", "timestamp": 1711152000, "open": 68700.0,  "high": 70200.0,  "low": 68000.0,  "close": 69500.0,  "volume": 2800.4},
    {"date": "2024-03-24", "timestamp": 1711238400, "open": 69500.0,  "high": 71000.0,  "low": 69000.0,  "close": 70300.0,  "volume": 2900.6},
    {"date": "2024-03-25", "timestamp": 1711324800, "open": 70300.0,  "high": 71500.0,  "low": 69800.0,  "close": 70900.0,  "volume": 2700.2},
    {"date": "2024-03-26", "timestamp": 1711411200, "open": 70900.0,  "high": 71800.0,  "low": 70100.0,  "close": 71500.0,  "volume": 2600.5},
    {"date": "2024-03-27", "timestamp": 1711497600, "open": 71500.0,  "high": 72500.0,  "low": 70900.0,  "close": 72100.0,  "volume": 2550.3},
    {"date": "2024-03-28", "timestamp": 1711584000, "open": 72100.0,  "high": 73000.0,  "low": 71600.0,  "close": 72700.0,  "volume": 2400.1},
    {"date": "2024-03-29", "timestamp": 1711670400, "open": 72700.0,  "high": 73800.0,  "low": 72200.0,  "close": 73400.0,  "volume": 2350.8},
    {"date": "2024-03-30", "timestamp": 1711756800, "open": 73400.0,  "high": 74200.0,  "low": 72900.0,  "close": 73900.0,  "volume": 2200.4},
]

# ---------------------------------------------------------------------------
# SAMPLE_DEPOSITS – sample deposit records
# ---------------------------------------------------------------------------

SAMPLE_DEPOSITS = [
    {"pubkey": DEMO_USERS[0]["pubkey"], "amount_sats": 100_000,   "created_at": 1709251200, "confirmed": True},
    {"pubkey": DEMO_USERS[0]["pubkey"], "amount_sats": 150_000,   "created_at": 1711065600, "confirmed": True},
    {"pubkey": DEMO_USERS[1]["pubkey"], "amount_sats": 1_000_000, "created_at": 1709337600, "confirmed": True},
    {"pubkey": DEMO_USERS[1]["pubkey"], "amount_sats": 2_000_000, "created_at": 1710028800, "confirmed": True},
    {"pubkey": DEMO_USERS[1]["pubkey"], "amount_sats": 500_000,   "created_at": 1710892800, "confirmed": True},
    {"pubkey": DEMO_USERS[2]["pubkey"], "amount_sats": 10_000_000,"created_at": 1709510400, "confirmed": True},
    {"pubkey": DEMO_USERS[3]["pubkey"], "amount_sats": 50_000,    "created_at": 1709683200, "confirmed": True},
    {"pubkey": DEMO_USERS[4]["pubkey"], "amount_sats": 3_000_000, "created_at": 1710201600, "confirmed": True},
    {"pubkey": DEMO_USERS[4]["pubkey"], "amount_sats": 2_500_000, "created_at": 1711238400, "confirmed": True},
]

# ---------------------------------------------------------------------------
# SAMPLE_ACHIEVEMENTS – achievement configurations
# ---------------------------------------------------------------------------

SAMPLE_ACHIEVEMENTS = [
    {"type": "first_deposit",   "name": "First Deposit",      "description": "Made your first Bitcoin deposit",       "icon": "🪙", "points": 10},
    {"type": "streak_7",        "name": "Week Streak",         "description": "Saved for 7 consecutive days",          "icon": "🔥", "points": 20},
    {"type": "streak_30",       "name": "Month Streak",        "description": "Saved for 30 consecutive days",         "icon": "💪", "points": 50},
    {"type": "streak_90",       "name": "Quarter Streak",      "description": "Saved for 90 consecutive days",         "icon": "🏆", "points": 100},
    {"type": "goal_reached",    "name": "Goal Reached",        "description": "Hit your monthly savings target",       "icon": "🎯", "points": 30},
    {"type": "sats_1k",         "name": "1K Sats",             "description": "Accumulated 1,000 sats",                "icon": "⚡", "points": 5},
    {"type": "sats_10k",        "name": "10K Sats",            "description": "Accumulated 10,000 sats",               "icon": "⚡", "points": 10},
    {"type": "sats_100k",       "name": "100K Sats",           "description": "Accumulated 100,000 sats",              "icon": "💎", "points": 25},
    {"type": "sats_1m",         "name": "1M Sats",             "description": "Accumulated 1,000,000 sats",            "icon": "💎", "points": 75},
    {"type": "btc_01",          "name": "0.1 BTC",             "description": "Accumulated 0.1 BTC",                   "icon": "🌋", "points": 200},
    {"type": "btc_1",           "name": "1 BTC",               "description": "Accumulated 1 full Bitcoin",            "icon": "🌋", "points": 1000},
    {"type": "early_adopter",   "name": "Early Adopter",       "description": "Joined in the first 1,000 users",       "icon": "🚀", "points": 50},
    {"type": "hodler",          "name": "HODLER",              "description": "Held through a 50%+ drawdown",           "icon": "🧊", "points": 150},
    {"type": "diamond_hands",   "name": "Diamond Hands",       "description": "Never sold during market panic",        "icon": "💍", "points": 300},
    {"type": "lightning_payment","name": "Lightning Speed",    "description": "Made a Lightning Network payment",      "icon": "⚡", "points": 15},
    {"type": "referral",        "name": "Referred a Friend",   "description": "Successfully referred a new user",      "icon": "👥", "points": 40},
    {"type": "anniversary_1y",  "name": "One Year",            "description": "Used Magma for one year",               "icon": "🎂", "points": 100},
    {"type": "anniversary_2y",  "name": "Two Years",           "description": "Used Magma for two years",              "icon": "🎂", "points": 250},
]

# ---------------------------------------------------------------------------
# BENCHMARK_DATA – comparison indices (annual returns, approx.)
# ---------------------------------------------------------------------------

BENCHMARK_DATA = {
    "sp500": {
        "name": "S&P 500",
        "symbol": "^GSPC",
        "annual_returns": {
            "2015": 0.014, "2016": 0.119, "2017": 0.217, "2018": -0.044,
            "2019": 0.313, "2020": 0.184, "2021": 0.288, "2022": -0.182,
            "2023": 0.264, "2024": 0.232,
        },
        "avg_annual_return": 0.186,
        "currency": "USD",
    },
    "gold": {
        "name": "Gold (XAU/USD)",
        "symbol": "GC=F",
        "annual_returns": {
            "2015": -0.102, "2016": 0.088, "2017": 0.133, "2018": -0.020,
            "2019": 0.184, "2020": 0.252, "2021": -0.035, "2022": -0.001,
            "2023": 0.132, "2024": 0.271,
        },
        "avg_annual_return": 0.092,
        "currency": "USD",
    },
    "us_bonds_10y": {
        "name": "US 10-Year Treasury",
        "symbol": "^TNX",
        "annual_returns": {
            "2015": 0.013, "2016": -0.032, "2017": 0.025, "2018": -0.002,
            "2019": 0.090, "2020": 0.115, "2021": -0.024, "2022": -0.178,
            "2023": 0.038, "2024": 0.020,
        },
        "avg_annual_return": 0.027,
        "currency": "USD",
    },
    "bitcoin": {
        "name": "Bitcoin (BTC/USD)",
        "symbol": "BTC-USD",
        "annual_returns": {
            "2015": 0.350, "2016": 1.250, "2017": 13.500, "2018": -0.730,
            "2019": 0.920, "2020": 3.010, "2021": 0.590, "2022": -0.640,
            "2023": 1.540, "2024": 1.240,
        },
        "avg_annual_return": 2.003,
        "currency": "USD",
    },
}

# ---------------------------------------------------------------------------
# COUNTRY_DATA – El Salvador focus + LATAM
# ---------------------------------------------------------------------------

COUNTRY_DATA = [
    {"code": "SV", "name": "El Salvador",  "currency": "USD", "btc_legal_tender": True,  "region": "Central America"},
    {"code": "US", "name": "United States","currency": "USD", "btc_legal_tender": False, "region": "North America"},
    {"code": "MX", "name": "Mexico",       "currency": "MXN", "btc_legal_tender": False, "region": "North America"},
    {"code": "GT", "name": "Guatemala",    "currency": "GTQ", "btc_legal_tender": False, "region": "Central America"},
    {"code": "HN", "name": "Honduras",     "currency": "HNL", "btc_legal_tender": False, "region": "Central America"},
    {"code": "NI", "name": "Nicaragua",    "currency": "NIO", "btc_legal_tender": False, "region": "Central America"},
    {"code": "CR", "name": "Costa Rica",   "currency": "CRC", "btc_legal_tender": False, "region": "Central America"},
    {"code": "PA", "name": "Panama",       "currency": "PAB", "btc_legal_tender": False, "region": "Central America"},
    {"code": "CO", "name": "Colombia",     "currency": "COP", "btc_legal_tender": False, "region": "South America"},
    {"code": "VE", "name": "Venezuela",    "currency": "VES", "btc_legal_tender": False, "region": "South America"},
    {"code": "EC", "name": "Ecuador",      "currency": "USD", "btc_legal_tender": False, "region": "South America"},
    {"code": "PE", "name": "Peru",         "currency": "PEN", "btc_legal_tender": False, "region": "South America"},
    {"code": "BR", "name": "Brazil",       "currency": "BRL", "btc_legal_tender": False, "region": "South America"},
    {"code": "AR", "name": "Argentina",    "currency": "ARS", "btc_legal_tender": False, "region": "South America"},
    {"code": "CL", "name": "Chile",        "currency": "CLP", "btc_legal_tender": False, "region": "South America"},
    {"code": "BO", "name": "Bolivia",      "currency": "BOB", "btc_legal_tender": False, "region": "South America"},
    {"code": "PY", "name": "Paraguay",     "currency": "PYG", "btc_legal_tender": False, "region": "South America"},
    {"code": "UY", "name": "Uruguay",      "currency": "UYU", "btc_legal_tender": False, "region": "South America"},
    {"code": "DO", "name": "Dominican Republic", "currency": "DOP", "btc_legal_tender": False, "region": "Caribbean"},
    {"code": "PR", "name": "Puerto Rico",  "currency": "USD", "btc_legal_tender": False, "region": "Caribbean"},
]

# ---------------------------------------------------------------------------
# FEE_HISTORY – 30 days of mempool fee estimates (sat/vB)
# ---------------------------------------------------------------------------

FEE_HISTORY = [
    {"date": "2024-03-01", "fastest": 85,  "half_hour": 60,  "hour": 45,  "economy": 30, "minimum": 1},
    {"date": "2024-03-02", "fastest": 72,  "half_hour": 55,  "hour": 40,  "economy": 25, "minimum": 1},
    {"date": "2024-03-03", "fastest": 90,  "half_hour": 70,  "hour": 55,  "economy": 35, "minimum": 1},
    {"date": "2024-03-04", "fastest": 110, "half_hour": 90,  "hour": 70,  "economy": 45, "minimum": 2},
    {"date": "2024-03-05", "fastest": 145, "half_hour": 120, "hour": 95,  "economy": 60, "minimum": 3},
    {"date": "2024-03-06", "fastest": 180, "half_hour": 150, "hour": 120, "economy": 80, "minimum": 5},
    {"date": "2024-03-07", "fastest": 200, "half_hour": 170, "hour": 140, "economy": 90, "minimum": 6},
    {"date": "2024-03-08", "fastest": 250, "half_hour": 210, "hour": 180, "economy": 110,"minimum": 8},
    {"date": "2024-03-09", "fastest": 220, "half_hour": 190, "hour": 160, "economy": 100,"minimum": 7},
    {"date": "2024-03-10", "fastest": 175, "half_hour": 145, "hour": 120, "economy": 75, "minimum": 4},
    {"date": "2024-03-11", "fastest": 130, "half_hour": 110, "hour": 90,  "economy": 55, "minimum": 3},
    {"date": "2024-03-12", "fastest": 100, "half_hour": 85,  "hour": 68,  "economy": 40, "minimum": 2},
    {"date": "2024-03-13", "fastest": 88,  "half_hour": 72,  "hour": 58,  "economy": 35, "minimum": 1},
    {"date": "2024-03-14", "fastest": 75,  "half_hour": 62,  "hour": 50,  "economy": 28, "minimum": 1},
    {"date": "2024-03-15", "fastest": 65,  "half_hour": 52,  "hour": 42,  "economy": 22, "minimum": 1},
    {"date": "2024-03-16", "fastest": 80,  "half_hour": 65,  "hour": 52,  "economy": 32, "minimum": 1},
    {"date": "2024-03-17", "fastest": 95,  "half_hour": 78,  "hour": 62,  "economy": 38, "minimum": 2},
    {"date": "2024-03-18", "fastest": 120, "half_hour": 100, "hour": 80,  "economy": 50, "minimum": 3},
    {"date": "2024-03-19", "fastest": 300, "half_hour": 260, "hour": 220, "economy": 160,"minimum": 20},
    {"date": "2024-03-20", "fastest": 280, "half_hour": 240, "hour": 200, "economy": 140,"minimum": 18},
    {"date": "2024-03-21", "fastest": 195, "half_hour": 165, "hour": 135, "economy": 85, "minimum": 10},
    {"date": "2024-03-22", "fastest": 140, "half_hour": 120, "hour": 100, "economy": 60, "minimum": 5},
    {"date": "2024-03-23", "fastest": 105, "half_hour": 88,  "hour": 72,  "economy": 44, "minimum": 3},
    {"date": "2024-03-24", "fastest": 85,  "half_hour": 70,  "hour": 58,  "economy": 34, "minimum": 2},
    {"date": "2024-03-25", "fastest": 70,  "half_hour": 58,  "hour": 46,  "economy": 28, "minimum": 1},
    {"date": "2024-03-26", "fastest": 62,  "half_hour": 52,  "hour": 42,  "economy": 24, "minimum": 1},
    {"date": "2024-03-27", "fastest": 58,  "half_hour": 48,  "hour": 38,  "economy": 20, "minimum": 1},
    {"date": "2024-03-28", "fastest": 55,  "half_hour": 45,  "hour": 36,  "economy": 18, "minimum": 1},
    {"date": "2024-03-29", "fastest": 68,  "half_hour": 55,  "hour": 44,  "economy": 26, "minimum": 1},
    {"date": "2024-03-30", "fastest": 78,  "half_hour": 64,  "hour": 52,  "economy": 30, "minimum": 1},
]

# ---------------------------------------------------------------------------
# MEMPOOL_SAMPLES – representative mempool snapshots
# ---------------------------------------------------------------------------

MEMPOOL_SAMPLES = [
    {"timestamp": 1709251200, "size_bytes": 25_000_000, "tx_count": 42_000, "fee_histogram": [[1,500],[5,2000],[10,5000],[20,8000],[50,15000],[100,20000]]},
    {"timestamp": 1710028800, "size_bytes": 45_000_000, "tx_count": 78_000, "fee_histogram": [[1,200],[5,800],[10,2000],[20,5000],[50,12000],[100,18000],[200,25000]]},
    {"timestamp": 1710892800, "size_bytes": 120_000_000,"tx_count": 150_000,"fee_histogram": [[1,100],[5,300],[10,800],[20,2500],[50,8000],[100,15000],[200,22000],[500,40000]]},
    {"timestamp": 1711065600, "size_bytes": 30_000_000, "tx_count": 55_000, "fee_histogram": [[1,1000],[5,3000],[10,7000],[20,10000],[50,16000],[100,20000]]},
    {"timestamp": 1711497600, "size_bytes": 18_000_000, "tx_count": 32_000, "fee_histogram": [[1,2000],[5,5000],[10,8000],[20,12000],[50,18000]]},
]

# ---------------------------------------------------------------------------
# LIGHTNING_SAMPLES – Lightning Network snapshots
# ---------------------------------------------------------------------------

LIGHTNING_SAMPLES = [
    {
        "timestamp": 1709251200,
        "node_count": 14_532,
        "channel_count": 52_841,
        "total_capacity_btc": 4_823.45,
        "avg_channel_capacity_sats": 9_120_000,
        "median_fee_rate_ppm": 250,
        "network_diameter": 6,
        "avg_path_length": 3.2,
    },
    {
        "timestamp": 1710028800,
        "node_count": 14_601,
        "channel_count": 53_200,
        "total_capacity_btc": 4_900.12,
        "avg_channel_capacity_sats": 9_210_000,
        "median_fee_rate_ppm": 245,
        "network_diameter": 6,
        "avg_path_length": 3.2,
    },
    {
        "timestamp": 1711065600,
        "node_count": 14_720,
        "channel_count": 54_100,
        "total_capacity_btc": 5_010.88,
        "avg_channel_capacity_sats": 9_260_000,
        "median_fee_rate_ppm": 240,
        "network_diameter": 6,
        "avg_path_length": 3.1,
    },
]

# ---------------------------------------------------------------------------
# EXCHANGE_RATES – USD to 20 currencies (approximate, mid-2024)
# ---------------------------------------------------------------------------

EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 151.0,
    "CAD": 1.36,
    "AUD": 1.53,
    "CHF": 0.90,
    "CNY": 7.24,
    "MXN": 17.20,
    "BRL": 4.97,
    "ARS": 876.0,
    "COP": 3910.0,
    "CLP": 952.0,
    "PEN": 3.72,
    "GTQ": 7.79,
    "HNL": 24.70,
    "NIO": 36.60,
    "CRC": 515.0,
    "DOP": 58.50,
    "VES": 36.40,
}

# ---------------------------------------------------------------------------
# HISTORICAL_HALVINGS – all Bitcoin halving events
# ---------------------------------------------------------------------------

HISTORICAL_HALVINGS = [
    {
        "height": 0,
        "date": "2009-01-03",
        "timestamp": 1231006505,
        "block_reward_btc": 50.0,
        "event": "genesis",
        "btc_price_usd_approx": 0.0,
    },
    {
        "height": 210_000,
        "date": "2012-11-28",
        "timestamp": 1354116278,
        "block_reward_btc": 25.0,
        "event": "halving_1",
        "btc_price_usd_approx": 12.35,
        "price_1y_later_usd": 1000.0,
    },
    {
        "height": 420_000,
        "date": "2016-07-09",
        "timestamp": 1468082773,
        "block_reward_btc": 12.5,
        "event": "halving_2",
        "btc_price_usd_approx": 650.0,
        "price_1y_later_usd": 2500.0,
    },
    {
        "height": 630_000,
        "date": "2020-05-11",
        "timestamp": 1589225023,
        "block_reward_btc": 6.25,
        "event": "halving_3",
        "btc_price_usd_approx": 8821.0,
        "price_1y_later_usd": 56_800.0,
    },
    {
        "height": 840_000,
        "date": "2024-04-20",
        "timestamp": 1713571767,
        "block_reward_btc": 3.125,
        "event": "halving_4",
        "btc_price_usd_approx": 63_700.0,
        "price_1y_later_usd": None,
    },
    {
        "height": 1_050_000,
        "date": "2028-03-01",  # estimated
        "timestamp": None,
        "block_reward_btc": 1.5625,
        "event": "halving_5_estimated",
        "btc_price_usd_approx": None,
        "price_1y_later_usd": None,
    },
]

# ---------------------------------------------------------------------------
# NOTABLE_ADDRESSES – famous Bitcoin addresses
# ---------------------------------------------------------------------------

NOTABLE_ADDRESSES = [
    {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na", "label": "Genesis block coinbase",    "notes": "Satoshi Nakamoto – never moved"},
    {"address": "12cbQLTFMXRnSzktFkuoG3eHoMeFtpTu3", "label": "Mt. Gox cold wallet (old)",  "notes": "Defunct exchange"},
    {"address": "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF", "label": "Patoshi (Satoshi-era miner)","notes": "~1M BTC – never moved"},
    {"address": "3FHNBLobJnbCPujupEDEQL7ZPgQmB7TVDV", "label": "Binance cold wallet",         "notes": "Major exchange"},
    {"address": "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97", "label": "Coinbase custody", "notes": "Major exchange"},
    {"address": "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ", "label": "Kraken hot wallet",           "notes": "Major exchange"},
    {"address": "385cR5DM96n1HvBDMnLoxft1Pss7eFdFQQ", "label": "BitFinex cold storage",       "notes": "Exchange hacked in 2016"},
]

# ---------------------------------------------------------------------------
# TEST_VECTORS – cryptographic test vectors
# ---------------------------------------------------------------------------

TEST_VECTORS = {
    "bip39_mnemonic": {
        "entropy_hex": "00000000000000000000000000000000",
        "mnemonic": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
        "passphrase": "",
        "seed_hex": "5eb00bbddcf069084889a8ab9155568165f5c453ccb85e70811aaed6f6da5fc19a5ac40b389cd370d086206dec8aa6c43daea6690f20ad3d8d48b2d2ce9e38e4",
    },
    "bip32_root_xpub": {
        "seed_hex": "000102030405060708090a0b0c0d0e0f",
        "xpub": "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC1CVuoFxFgbSRaBCfKxQT5PBER7gGrgQ2VpEPcFY8EAaHEeFhDpvBsHoR2vC6Eq58b3HtaFQrMeiy",
    },
    "sha256_vectors": [
        {"input": "", "output": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        {"input": "abc", "output": "ba7816bf8f01cfea414140de5dae2ec73b00361bbef0469f0a3417d9f2e8f37f"},
        {"input": "The quick brown fox jumps over the lazy dog",
         "output": "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592"},
    ],
    "nostr_keypair_example": {
        "private_key_hex": "67dea2ed018072d675f5415ecfaed7d2597555e202d85b3d65ea4e58d2d92ffa",
        "public_key_hex":  "7e7e9c42a91bfef19fa929e5fda1b72e0ebc1a4c1141673e2794234d86addf4e",
        "note_id_example": "a0a0a0a0b1b1b1b1c2c2c2c2d3d3d3d3e4e4e4e4f5f5f5f5061616170717181",
    },
    "lnurl_auth_example": {
        "lnurl_callback": "https://api.eclalune.com/v1/auth/lnurl-callback",
        "k1_hex": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "sig_format": "DER-encoded ECDSA over secp256k1",
    },
}

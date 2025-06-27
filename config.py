# config.py

# Penskalaan skor untuk tingkat pendidikan
EDUCATION_LEVELS = {
    "Tidak ada": 0, "SD": 1, "SMP": 2, "SMA": 3, "SMK": 3,
    "D1": 4, "D2": 4, "D3": 5, "S1": 6, "Sarjana": 6, "S2": 7, "Master": 7
}

# Daftar kunci untuk dropdown di UI
EDUCATION_KEYS = list(EDUCATION_LEVELS.keys())
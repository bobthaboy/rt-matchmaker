from math import inf

# ==========================================================
# Lookup Tables (copied from the spreadsheet)
# ==========================================================

ACC_TABLE = [
    (inf, 1.00),
    (500, 0.99),
    (40, 0.95),
    (15, 0.80),
    (10, 0.70),
    (5, 0.40),
    (2, 0.30),
    (1, 0.00),
    (0, 0.00),
]

COMBO_TABLE = [
    (100, 1.00),
    (99.9, 0.95),
    (40, 0.85),
    (20, 0.65),
    (10, 0.45),
    (5, 0.20),
    (0, 0.00),
]

MISS_TABLE = [
    (0, 1.00),
    (0.5, 0.90),
    (1, 0.80),
    (2.5, 0.60),
    (5, 0.40),
    (10, 0.20),
    (25, 0.00),
    (999999, 0.00),
]

# ==========================================================
# Weights
# ==========================================================

ACC_WEIGHT = 5.0
COMBO_WEIGHT = 1.5
MISS_WEIGHT = 3.5

TOTAL_WEIGHT = ACC_WEIGHT + COMBO_WEIGHT + MISS_WEIGHT


# ==========================================================
# Generic interpolation
# ==========================================================

def interpolate(x, table):
    """
    Piecewise linear interpolation.
    Table is a list of (x, y) points.
    """

    # Remove infinite point for interpolation purposes
    if table[0][0] == inf:
        if x >= table[1][0]:
            return table[0][1]
        table = table[1:]

    descending = table[0][0] > table[-1][0]

    if descending:
        if x >= table[0][0]:
            return table[0][1]
        if x <= table[-1][0]:
            return table[-1][1]

        for i in range(len(table) - 1):
            x1, y1 = table[i]
            x2, y2 = table[i + 1]

            if x1 >= x >= x2:
                t = (x - x2) / (x1 - x2)
                return y2 + t * (y1 - y2)

    else:
        if x <= table[0][0]:
            return table[0][1]
        if x >= table[-1][0]:
            return table[-1][1]

        for i in range(len(table) - 1):
            x1, y1 = table[i]
            x2, y2 = table[i + 1]

            if x1 <= x <= x2:
                t = (x - x1) / (x2 - x1)
                return y1 + t * (y2 - y1)

    return table[-1][1]


# ==========================================================
# Accuracy
# ==========================================================

def calculate_accuracy(judgement_string, misses):
    perfect, good, ok = map(int, judgement_string.split("/"))

    effective_good = good + ok * 2 + misses * 0.05

    if effective_good == 0:
        return 1.0

    ratio = perfect / effective_good

    return interpolate(ratio, ACC_TABLE)


# ==========================================================
# Combo
# ==========================================================

def calculate_combo(combo, max_combo):
    percent = combo / max_combo * 100
    return interpolate(percent, COMBO_TABLE)


# ==========================================================
# Miss
# ==========================================================

def calculate_miss(misses, max_combo):
    percent = misses / max_combo * 100
    return interpolate(percent, MISS_TABLE)


# ==========================================================
# Final Score
# ==========================================================

def calculate_score(judgements, misses, combo, max_combo):
    acc = calculate_accuracy(judgements, misses)
    combo_score = calculate_combo(combo, max_combo)
    miss_score = calculate_miss(misses, max_combo)

    final = (
                    acc * ACC_WEIGHT +
                    combo_score * COMBO_WEIGHT +
                    miss_score * MISS_WEIGHT
            ) / TOTAL_WEIGHT

    return int(round(final, 6) * 1000000)

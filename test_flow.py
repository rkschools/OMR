sections = [
    {"name": "TELUGU", "q_count": 3},
    {"name": "HINDI", "q_count": 3},
    {"name": "ENGLISH", "q_count": 5},
    {"name": "MATHEMATICS", "q_count": 10},
    {"name": "SCIENCE", "q_count": 18},
    {"name": "SOCIAL STUDIES", "q_count": 5},
    {"name": "GK / COMPUTER", "q_count": 4},
    {"name": "CURRENT AFFAIRS", "q_count": 2}
]

header_overhead = 8.0 + 5.0 + 8.0 # 21.0
row_spacing = 7.0
K = 3

def simulate(target_h):
    cols = [[] for _ in range(K)]
    current_col = 0
    current_y = 0
    
    for sec in sections:
        q_rem = sec["q_count"]
        first_part = True
        
        while q_rem > 0:
            if current_y + header_overhead >= target_h and current_col < K - 1:
                current_col += 1
                current_y = 0
                first_part = False
            
            # How many questions can fit in this column?
            available_h = target_h - current_y - header_overhead
            if available_h < row_spacing:
                if current_col < K - 1:
                    current_col += 1
                    current_y = 0
                    first_part = False
                    continue
                else:
                    return False # Overflowed last column
            
            # max questions that fit
            max_q = int(available_h // row_spacing)
            take_q = min(q_rem, max_q)
            
            cols[current_col].append({
                "name": sec["name"] + (" (CONT.)" if not first_part else ""),
                "q_count": take_q
            })
            
            current_y += header_overhead + take_q * row_spacing
            q_rem -= take_q
            first_part = False
            
    return cols

# Binary search for the optimal target_h
low = 50.0
high = 300.0
best_cols = None
for _ in range(50):
    mid = (low + high) / 2
    res = simulate(mid)
    if res:
        best_cols = res
        high = mid
    else:
        low = mid

print(f"Optimal column height: {high}")
for i, col in enumerate(best_cols):
    print(f"Col {i+1}:")
    for sec in col:
        print(f"  {sec['name']}: {sec['q_count']}")

def calculate_h(q_count, row_spacing=7.0, header_h=8.0, header_gap=5.0, bottom_m=8.0):
    return header_h + header_gap + (q_count * row_spacing) + bottom_m

def partition(sections, K):
    # simple DP for partition
    n = len(sections)
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i+1] = prefix[i] + sections[i]
        
    dp = [[float('inf')] * (K + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    
    for i in range(1, n + 1):
        for j in range(1, K + 1):
            for m in range(i):
                cost = max(dp[m][j-1], prefix[i] - prefix[m])
                if cost < dp[i][j]:
                    dp[i][j] = cost
                    
    return dp[n][K]

q_counts = [3, 3, 5, 10, 18, 5, 4, 2]

print("Standard (7.0, 8.0, 5.0, 8.0)")
sections = [calculate_h(q) for q in q_counts]
for k in [2, 3, 4]:
    print(f"K={k}, max_h={partition(sections, k)}")

print("\nCompressed 1 (6.5, 8.0, 4.0, 5.0)")
sections = [calculate_h(q, 6.5, 8.0, 4.0, 5.0) for q in q_counts]
for k in [2, 3, 4]:
    print(f"K={k}, max_h={partition(sections, k)}")


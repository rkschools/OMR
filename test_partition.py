def partition_sections(sections, k):
    # dynamic programming to partition sections into k contiguous groups minimizing max sum
    n = len(sections)
    dp = [[float('inf')] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    prefix = [0] * (n + 1)
    for i in range(1, n + 1):
        prefix[i] = prefix[i-1] + sections[i-1]
        
    for i in range(1, n + 1):
        for j in range(1, k + 1):
            for m in range(i):
                dp[i][j] = min(dp[i][j], max(dp[m][j-1], prefix[i] - prefix[m]))
                
    return dp[n][k]

sections = [30.5, 30.5, 43.5, 76, 128, 43.5, 37, 24] # heights
print("K=2 max height:", partition_sections(sections, 2))
print("K=3 max height:", partition_sections(sections, 3))

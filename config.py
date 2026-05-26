# 全局参数配置
import os

OPENAI_API_KEY          = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY        = os.getenv("DEEPSEEK_API_KEY", "")
POPULATION              = 100           # 学生数量
MAX_STEPS               = 15           # 模拟天数
MAX_PARTNERS            = 2             # 每个学生最多同时性伙伴数
VENUE_PROB_BASE         = 0.3           # 基础去娱乐场所概率（可被LLM决策覆盖）
CAMPUS_MEET_PROB        = 0.5          # 校园内随机结识新伙伴基础概率
VENUE_MEET_PROB         = 0.8        # 场所结识新伙伴基础概率
VENUE_INFECT_PROB       = 0.01        # 场所基础感染概率（独立于伙伴关系）
# 性传播差异化概率
HETERO_INFECT_RATE      = 0.1      # 异性无保护性交 0.08% * 100
HOMO_MALE_INFECT_RATE   = 0.4         # 男性同性无保护 1.38% * 10
HOMO_FEMALE_INFECT_RATE = 0.00001      # 女性同性无保护 0.0001%
import os
import random
import asyncio
from openai import AsyncOpenAI
from typing import List, Dict, Optional
import hashlib
import json # 导入json库
from ncss_sampler import generate_student_profiles_from_ncss

async_client = None
_llm_cache = {}


def _get_async_client():
    global async_client
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    if async_client is None:
        async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    return async_client


def probability_threshold(p: float) -> bool:
    """以概率 p 返回 True"""
    return random.random() < p


async def get_completion_from_messages(
    messages: List[Dict],
    model: str = "deepseek-chat",
    #这里改成了本地模型名称
    # model: str = "/mnt/d/Zelin Tan/Deepseek-V3/DeepSeek-R1-Distill-Qwen-7B"
    #temperature: float = 0.0
) -> str:
    """调用 ChatCompletion 并返回回复内容，带简单重试机制"""
    global _llm_cache
    # ⬅️ 缓存查找逻辑
    # 1. 将消息列表转换为稳定的字符串（排序后，确保顺序无关）
    messages_str = json.dumps(messages, sort_keys=True)
    # 2. 计算这个字符串的哈希值作为缓存的键
    cache_key = hashlib.sha256(messages_str.encode('utf-8')).hexdigest()
    # 3. 检查缓存中是否已有该结果
    if cache_key in _llm_cache:
        # print(f"[LLM] Cache hit for prompt. Returning cached response.")
        return _llm_cache[cache_key]

    for _ in range(3):
        try:
            client = _get_async_client()
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                # temperature=temperature
            )
            # print(f"[LLM] Agent got response")
            response_content = resp.choices[0].message.content
            # 将LLM的返回结果存入缓存
            _llm_cache[cache_key] = response_content
            return response_content

        except Exception as e:
            # 增加一个小的异步等待，避免在失败时立即重试导致拥塞
            print(f"API call failed, retrying... Error: {e}")
            await asyncio.sleep(1)
            continue
    raise RuntimeError("deepseek API 调用失败")


def generate_student_profiles(
    n: int,
    source: str = "random",
    data_path: Optional[str] = None,
) -> List[Dict]:
    """生成 n 个学生基础 Profile"""
    if source == "ncss":
        return generate_student_profiles_from_ncss(n, data_path=data_path)

    profiles = []
    for i in range(n):
        profiles.append({
            "name": f"Student_{i}",
            "age": random.randint(18,24),
            "gender": random.choice(["男","女"]),
            "social_activity": random.choice(["较低","中等","很高"]),
            "attractiveness": random.choice(["较低","中等","很高"]),
            "sexual_orientation": random.choice(["异性恋","同性恋","双性恋"]),
            # "condom_use_tendency": round(random.uniform(0.2,0.9),2),
            "risk_propensity": random.choice(["鲁莽的", "普通的", "谨慎的"]),
        })
    return profiles 
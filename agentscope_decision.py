import asyncio
import hashlib
import json
import os
import re


def _load_formatter():
    """Prefer AgentScope's DeepSeek formatter, fallback to OpenAI-compatible."""
    try:
        from agentscope.formatter import DeepSeekChatFormatter

        return DeepSeekChatFormatter()
    except ImportError:
        from agentscope.formatter import OpenAIChatFormatter

        return OpenAIChatFormatter()


def _build_openai_model(model_name: str, api_key: str, base_url: str, stream: bool):
    from agentscope.model import OpenAIChatModel

    model_kwargs = {
        "model_name": model_name,
        "api_key": api_key,
        "stream": stream,
    }

    try:
        return OpenAIChatModel(
            **model_kwargs,
            client_kwargs={"base_url": base_url},
        )
    except TypeError:
        return OpenAIChatModel(
            **model_kwargs,
            client_args={"base_url": base_url},
        )


def _extract_text(response) -> str:
    if response is None:
        return ""
    if hasattr(response, "get_text_content"):
        return response.get_text_content()
    if isinstance(response, dict):
        return str(response.get("content", response))
    return str(response)


def _messages_to_prompt(messages) -> str:
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _format_profile_context(profile: dict) -> str:
    fields = [
        ("姓名", "name"),
        ("年龄", "age"),
        ("性别", "gender"),
        ("社交活跃度", "social_activity"),
        ("关系机会/吸引力代理指标", "attractiveness"),
        ("性取向", "sexual_orientation"),
        ("风险偏好", "risk_propensity"),
        ("学校性教育形式", "sex_education_forms"),
        ("性与生殖健康知识来源", "knowledge_sources"),
        ("目前感情状况", "relationship_status"),
        ("是否想交男/女朋友", "wants_partner"),
        ("过往恋爱伴侣数量", "past_partner_count"),
        ("每日社交娱乐时间", "daily_social_hours"),
        ("色情作品接触频率", "porn_exposure_frequency"),
        ("是否有插入式性行为经验", "has_insertive_sex"),
        ("是否有约炮/一夜情/买春经验", "casual_sex_experience"),
        ("此类性行为对象人数", "casual_sex_partner_count"),
        ("此类性行为对象类型", "casual_sex_partner_types"),
        ("过去一年性行为频率", "sex_frequency_last_year"),
        ("最近一次避孕/安全措施", "recent_contraception_methods"),
        ("平时避孕及避孕方式决策者", "contraception_decision_maker"),
        ("未避孕原因", "no_contraception_reasons"),
        ("过去一年性病确诊史", "sti_history"),
        ("过去一年艾滋病确诊", "hiv_diagnosis_last_year"),
        ("艾滋病确诊后治疗情况", "hiv_treatment_after_diagnosis"),
    ]
    return "\n".join(f"- {label}：{profile.get(key, '未知')}" for label, key in fields)


def parse_decision_json(raw_text: str, default_action=None):
    """Parse {"reflection": "...", "action": ...} from an LLM response."""
    text = (raw_text or "").strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match:
        text = match.group(1)
    else:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            text = match.group(0)

    try:
        data = json.loads(text)
        return {
            "reflection": str(data.get("reflection", "")).strip(),
            "action": data.get("action", default_action),
            "parse_ok": True,
        }
    except (TypeError, json.JSONDecodeError):
        return {
            "reflection": "",
            "action": default_action,
            "parse_ok": False,
        }


_max_concurrency = int(os.getenv("AGENTSCOPE_MAX_CONCURRENCY", "5"))
_llm_semaphore = asyncio.Semaphore(_max_concurrency)


class AgentScopeDecisionAgent:
    """Small adapter that lets the existing simulation call AgentScope agents."""

    def __init__(self, profile: dict):
        try:
            from agentscope.agent import ReActAgent
            from agentscope.memory import InMemoryMemory
            from agentscope.message import Msg
        except ImportError as exc:
            raise RuntimeError(
                "AgentScope is not installed. Run `pip install -r requirements.txt` first."
            ) from exc

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. In PowerShell run: "
                '$env:DEEPSEEK_API_KEY="your_key"'
            )

        model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        stream = os.getenv("AGENTSCOPE_STREAM", "0") == "1"

        self._Msg = Msg
        self._cache = {}
        self.agent = ReActAgent(
            name=profile["name"],
            sys_prompt=self._build_system_prompt(profile),
            model=_build_openai_model(model_name, api_key, base_url, stream),
            formatter=_load_formatter(),
            memory=InMemoryMemory(),
        )

    @staticmethod
    def _build_system_prompt(profile: dict) -> str:
        extended_context = _format_profile_context(profile)
        return f"""
你是一名参与校园社会模拟的大学生智能体。
你的静态个人特征如下：
{extended_context}

你需要根据个人特征、近期记忆和当天场景做出行动决策。
为了方便模拟程序解析，凡是问题要求 JSON 时，你必须只输出 JSON，不要输出额外解释。
""".strip()

    async def ask(self, messages) -> str:
        prompt = _messages_to_prompt(messages)
        cache_key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        async with _llm_semaphore:
            response = await self.agent(self._Msg("simulation", prompt, "user"))

        text = _extract_text(response).strip()
        self._cache[cache_key] = text
        return text

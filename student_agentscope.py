import random

import config
from agentscope_decision import AgentScopeDecisionAgent, parse_decision_json, _format_profile_context
from utils import probability_threshold


class AgentScopeStudent:
    """Student agent with AgentScope/DeepSeek decision-making."""

    def __init__(self, model, uid: int, profile: dict, logger):
        self.model = model
        self.unique_id = uid
        self.logger = logger
        self.profile = profile
        self.decision_agent = AgentScopeDecisionAgent(profile)

        self.name = profile["name"]
        self.age = profile["age"]
        self.gender = profile["gender"]
        self.social_activity = profile["social_activity"]
        self.attractiveness = profile["attractiveness"]
        self.sexual_orientation = profile["sexual_orientation"]
        self.risk_propensity = profile["risk_propensity"]
        self.awareness = float(profile.get("awareness", 0.25))

        self.sex_education_forms = profile.get("sex_education_forms", "未知")
        self.knowledge_sources = profile.get("knowledge_sources", "未知")
        self.relationship_status = profile.get("relationship_status", "未知")
        self.wants_partner = profile.get("wants_partner", "未知")
        self.past_partner_count = profile.get("past_partner_count", "未知")
        self.daily_social_hours = profile.get("daily_social_hours", "未知")
        self.porn_exposure_frequency = profile.get("porn_exposure_frequency", "未知")
        self.has_insertive_sex = profile.get("has_insertive_sex", "未知")
        self.casual_sex_experience = profile.get("casual_sex_experience", "未知")
        self.casual_sex_partner_count = profile.get("casual_sex_partner_count", "未知")
        self.casual_sex_partner_types = profile.get("casual_sex_partner_types", "未知")
        self.sex_frequency_last_year = profile.get("sex_frequency_last_year", "未知")
        self.recent_contraception_methods = profile.get("recent_contraception_methods", "未知")
        self.contraception_decision_maker = profile.get("contraception_decision_maker", "未知")
        self.no_contraception_reasons = profile.get("no_contraception_reasons", "未知")
        self.sti_history = profile.get("sti_history", "未知")
        self.hiv_diagnosis_last_year = profile.get("hiv_diagnosis_last_year", "未知")
        self.hiv_treatment_after_diagnosis = profile.get("hiv_treatment_after_diagnosis", "未知")

        self.mems = []
        self.health_condition = "Susceptible"
        self.day_infected = None
        self.partner_list = []
        self.location = "dorm"
        self.seek_partners_today = False
        self.sexual_acts = {}
        self.test_today = False
        self.infection_source = None

    def add_memory(self, text: str):
        self.mems.append(text)

    def receive_event(self, text: str):
        """Add event memory and update awareness when the event contains health cues."""
        self.add_memory(text)
        base_delta, reason = self._awareness_base_delta_from_event(text)
        if base_delta:
            participation, multiplier = self._sample_awareness_participation()
            delta = round(base_delta * multiplier, 3)
            old_awareness = self.awareness
            self.awareness = round(max(0.0, min(1.0, self.awareness + delta)), 3)
            self.profile["awareness"] = self.awareness
            self.add_memory(
                f"第{self._current_day()}天事件影响：{reason}；参与程度：{participation}，"
                f"防艾意识从{old_awareness:.3f}变为{self.awareness:.3f}。"
            )

    def _sample_awareness_participation(self):
        """Sample how strongly the agent pays attention to a campus intervention."""
        weights = {
            "完全没听": 0.20,
            "听了一些": 0.50,
            "很认真听": 0.30,
        }

        if self.awareness >= 0.65:
            weights["完全没听"] -= 0.08
            weights["很认真听"] += 0.08
        elif self.awareness <= 0.35:
            weights["完全没听"] += 0.08
            weights["很认真听"] -= 0.08

        if self.social_activity == "很高":
            weights["听了一些"] += 0.05
            weights["完全没听"] -= 0.05

        if self.risk_propensity == "鲁莽的":
            weights["完全没听"] += 0.06
            weights["很认真听"] -= 0.06
        elif self.risk_propensity == "谨慎的":
            weights["完全没听"] -= 0.05
            weights["很认真听"] += 0.05

        labels = list(weights)
        clean_weights = [max(0.01, weights[label]) for label in labels]
        participation = random.choices(labels, weights=clean_weights, k=1)[0]
        multipliers = {
            "完全没听": 0.0,
            "听了一些": 0.5,
            "很认真听": 1.0,
        }
        return participation, multipliers[participation]

    @staticmethod
    def _awareness_base_delta_from_event(text: str):
        if any(keyword in text for keyword in ["科普教育", "预防性病", "艾滋病预防", "安全套"]):
            return 0.18, "接受防艾/性健康教育"
        if any(keyword in text for keyword in ["自助检测", "匿名", "保密", "检测机"]):
            return 0.12, "获得低成本且保密的检测渠道信息"
        if any(keyword in text for keyword in ["公安", "法律", "刑事责任", "严厉打击"]):
            return 0.08, "接收到法律风险提示"
        if any(keyword in text for keyword in ["减少或避免", "娱乐场所", "人身安全"]):
            return 0.06, "接收到场所风险提醒"
        return 0.0, ""

    def _current_day(self):
        return getattr(self.model, "current_day", self.model.schedule.steps + 1)

    def _profile_context(self) -> str:
        return _format_profile_context(self.profile)

    @staticmethod
    def _partner_context(partner) -> str:
        return _format_profile_context(partner.profile)

    @staticmethod
    def _prompt_text(messages):
        return "\n\n".join(
            f"[{msg.get('role', 'user')}]\n{msg.get('content', '')}" for msg in messages
        )

    @staticmethod
    def _normalize_binary_action(action, raw_response: str) -> bool:
        if isinstance(action, bool):
            return action
        if isinstance(action, (int, float)):
            return int(action) == 1
        text = str(action).strip().lower()
        if text in {"1", "true", "yes", "y", "是", "会", "使用", "检测", "发生"}:
            return True
        if text in {"0", "false", "no", "n", "否", "不会", "不使用", "不检测", "不发生"}:
            return False
        return raw_response.strip().startswith("1")

    @staticmethod
    def _normalize_location_action(action, raw_response: str) -> str:
        text = str(action).strip().lower()
        if text in {"venue", "go_venue", "去娱乐场所", "娱乐", "外出"}:
            return "venue"
        if text in {"dorm", "stay_dorm", "待在宿舍", "宿舍"}:
            return "dorm"
        positive_keywords = ["娱乐", "外出", "社交活动", "venue"]
        return "venue" if any(keyword in raw_response for keyword in positive_keywords) else "dorm"

    async def _ask_json_decision(
        self,
        decision_type: str,
        messages,
        default_action,
        recent_memory: str = "",
        metadata: str = "",
    ):
        raw_response = await self.decision_agent.ask(messages)
        parsed = parse_decision_json(raw_response, default_action=default_action)
        self.logger.log_decision(
            self._current_day(),
            self.unique_id,
            decision_type,
            parsed["action"],
            parsed["reflection"],
            parsed["parse_ok"],
            raw_response,
            self._prompt_text(messages),
            recent_memory=recent_memory,
            metadata=metadata,
        )
        if parsed["reflection"]:
            self.add_memory(f"第{self._current_day()}天{decision_type}反思：{parsed['reflection']}")
        return parsed, raw_response

    async def decide_location(self):
        history = "\n".join(self.mems[-5:])
        self_context = self._profile_context()
        system_prompt = (
            f"你是名大学生。你的完整背景如下：\n{self_context}\n\n"
            "一个社交活跃度“很高”的学生非常喜欢参加派对和社交活动，即使在普通的日子里也很有可能外出。\n"
            "一个社交活跃度“中等”的学生对社交活动持开放态度，但会根据当天的具体情况和心情决定。\n"
            "一个社交活跃度“较低”的学生更喜欢安静的环境，通常倾向于待在宿舍，除非有特别的理由。"
        )
        user_prompt = (
            f"你最近的记忆是：\n{history}\n\n"
            f"基于你{self.social_activity}的性格，你今天晚上决定去娱乐场所参加社交活动，还是待在宿舍？\n"
            "请先用一句话反思近期记忆和性格如何影响你的选择，然后给出 action。\n"
            "你必须只输出 JSON，格式如下：\n"
            '{"reflection": "一句话说明理由", "action": "venue 或 dorm"}'
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            parsed, raw_response = await self._ask_json_decision(
                "location",
                messages,
                default_action="dorm",
                recent_memory=history,
            )
            self.location = self._normalize_location_action(parsed["action"], raw_response)
        except Exception as e:
            print(f"AgentScope调用失败 (decide_location, 学生ID: {self.unique_id}): {e}。将采用默认行为（待在宿舍）。")
            self.location = "dorm"

    def decide_seek_partners(self):
        if len(self.partner_list) >= config.MAX_PARTNERS:
            self.seek_partners_today = False
            return

        if self.attractiveness == "很高":
            self.seek_partners_today = probability_threshold(0.9)
        elif self.attractiveness == "中等":
            self.seek_partners_today = probability_threshold(0.6)
        else:
            self.seek_partners_today = probability_threshold(0.3)

    def meet_and_form_relationships(self):
        seekers = [a for a in self.model.students if a.seek_partners_today]
        for other in seekers:
            if other.unique_id <= self.unique_id:
                continue
            prob = config.VENUE_MEET_PROB if self.location == "venue" else config.CAMPUS_MEET_PROB
            if (
                probability_threshold(prob)
                and len(self.partner_list) < config.MAX_PARTNERS
                and len(other.partner_list) < config.MAX_PARTNERS
            ):
                self.partner_list.append(other.unique_id)
                other.partner_list.append(self.unique_id)

    def decide_end_partnerships(self):
        new_list = []
        for pid in self.partner_list:
            if probability_threshold(0.1):
                partner = self.model.students[pid]
                if self.unique_id in partner.partner_list:
                    partner.partner_list.remove(self.unique_id)
                continue
            new_list.append(pid)
        self.partner_list = new_list

    async def decide_hiv_test(self):
        history = "\n".join(self.mems[-2:])
        self_context = self._profile_context()
        system_prompt = f"你是一名在校大学生。你的完整背景如下：\n{self_context}\n"
        user_prompt = (
            f"你近期的记忆是：\n{history}\n\n"
            "基于以上所有信息，你今天会去进行HIV检测吗？\n"
            "请先用一句话反思近期记忆、校园信息和个人风险感知如何影响你的选择，然后给出 action。\n"
            "你必须只输出 JSON，格式如下：\n"
            '{"reflection": "一句话说明理由", "action": 1 或 0}'
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            parsed, raw_response = await self._ask_json_decision(
                "hiv_test",
                messages,
                default_action=0,
                recent_memory=history,
            )
            self.test_today = self._normalize_binary_action(parsed["action"], raw_response)
        except Exception as e:
            print(f"AgentScope HIV检测决策错误 (学生ID: {self.unique_id}): {e}. 采用默认选项：不检测.")
            self.test_today = False

    async def decide_sexual_activity(self):
        self.sexual_acts = {}
        if not self.partner_list:
            return

        for pid in self.partner_list:
            partner = self.model.students[pid]
            history = "\n".join(self.mems[-2:])
            self_context = self._profile_context()
            partner_context = self._partner_context(partner)

            system_prompt_sex = f"你是一名在校大学生。你的完整背景如下：\n{self_context}\n"
            user_prompt_sex = (
                f"你的性伙伴(ID: {pid})完整背景如下：\n{partner_context}\n\n"
                f"你近期的记忆是：\n{history}\n\n"
                "根据以上信息决定，你会和这位性伴侣发生性行为吗？\n"
                "请先用一句话反思个人特征、伴侣信息和近期记忆如何影响你的选择，然后给出 action。\n"
                "你必须只输出 JSON，格式如下：\n"
                '{"reflection": "一句话说明理由", "action": 1 或 0}'
            )
            messages_sex = [
                {"role": "system", "content": system_prompt_sex},
                {"role": "user", "content": user_prompt_sex},
            ]

            sex_today = False
            try:
                parsed_sex, raw_sex = await self._ask_json_decision(
                    "sexual_activity",
                    messages_sex,
                    default_action=0,
                    recent_memory=history,
                    metadata=f"partner_id={pid}",
                )
                sex_today = self._normalize_binary_action(parsed_sex["action"], raw_sex)
            except Exception as e:
                print(f"AgentScope性行为决策错误 (学生ID: {self.unique_id}): {e}. 采取默认选项：否.")

            condom_today = False
            if sex_today:
                system_prompt_condom = f"你是一名在校大学生。你的完整背景如下：\n{self_context}\n"
                user_prompt_condom = (
                    f"你的性伙伴(ID: {pid})完整背景如下：\n{partner_context}\n\n"
                    f"你近期的记忆是：\n{history}\n\n"
                    "根据以上信息决定，你会在性行为中使用安全套吗？\n"
                    "请先用一句话反思风险偏好、近期记忆和健康知识如何影响你的选择，然后给出 action。\n"
                    "你必须只输出 JSON，格式如下：\n"
                    '{"reflection": "一句话说明理由", "action": 1 或 0}'
                )
                messages_condom = [
                    {"role": "system", "content": system_prompt_condom},
                    {"role": "user", "content": user_prompt_condom},
                ]

                try:
                    parsed_condom, raw_condom = await self._ask_json_decision(
                        "condom_use",
                        messages_condom,
                        default_action=0,
                        recent_memory=history,
                        metadata=f"partner_id={pid}",
                    )
                    condom_today = self._normalize_binary_action(parsed_condom["action"], raw_condom)
                except Exception as e:
                    print(f"AgentScope安全套决策错误 (学生ID: {self.unique_id}): {e}. 采用默认选项：不使用.")

            self.sexual_acts[pid] = {"sex": sex_today, "condom": condom_today}

    async def prepare_step(self):
        self.test_today = False
        self.decide_end_partnerships()
        await self.decide_location()
        self.decide_seek_partners()
        if self.seek_partners_today:
            self.meet_and_form_relationships()
        await self.decide_hiv_test()
        await self.decide_sexual_activity()

    def finalize_step(self):
        if self.location == "venue" and self.health_condition == "Susceptible":
            if probability_threshold(config.VENUE_INFECT_PROB):
                self.health_condition = "To_Be_Infected"
                self.infection_source = "venue"

        for pid, self_act in self.sexual_acts.items():
            if self.unique_id > pid:
                continue
            other = self.model.students[pid]
            other_act = other.sexual_acts.get(self.unique_id)
            sex_happens = (self_act and self_act.get("sex", False)) and (
                other_act and other_act.get("sex", False)
            )
            if not sex_happens:
                continue

            self_wants_condom = self_act and self_act.get("condom", False)
            other_wants_condom = other_act and other_act.get("condom", False)
            if self_wants_condom or other_wants_condom:
                continue

            infected_one, susceptible_one = None, None
            infectious_states = {"Infected_Undiagnosed", "Infected_Diagnosed"}
            if self.health_condition in infectious_states and other.health_condition == "Susceptible":
                infected_one, susceptible_one = self, other
            elif other.health_condition in infectious_states and self.health_condition == "Susceptible":
                infected_one, susceptible_one = other, self
            else:
                continue

            if infected_one.gender == "男" and susceptible_one.gender == "男":
                trans_prob = config.HOMO_MALE_INFECT_RATE
            elif infected_one.gender == "女" and susceptible_one.gender == "女":
                trans_prob = config.HOMO_FEMALE_INFECT_RATE
            else:
                trans_prob = config.HETERO_INFECT_RATE

            if probability_threshold(trans_prob):
                susceptible_one.health_condition = "To_Be_Infected"
                susceptible_one.infection_source = "unprotected_sex"

    def update_health(self):
        current_day = getattr(self.model, "current_day", self.model.schedule.steps)
        if self.health_condition == "To_Be_Infected":
            self.health_condition = "Infected_Undiagnosed"
            self.day_infected = 0
            self.logger.log_infected_profile(current_day, self)
        elif self.health_condition == "Infected_Undiagnosed":
            self.day_infected += 1
            if self.test_today:
                self.health_condition = "Infected_Diagnosed"
                self.add_memory("你经过检测后知道了自己已感染艾滋病病毒。")
        elif self.health_condition == "Infected_Diagnosed":
            self.day_infected += 1


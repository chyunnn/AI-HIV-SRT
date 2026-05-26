from agentscope_decision import AgentScopeDecisionAgent, parse_decision_json
from student import Student


class AgentScopeStudent(Student):
    """Student variant whose LLM decisions are managed by AgentScope."""

    def __init__(self, model, uid: int, profile: dict, logger):
        super().__init__(model, uid, profile, logger)
        self.decision_agent = AgentScopeDecisionAgent(profile)

    def _current_day(self):
        return getattr(self.model, "current_day", self.model.schedule.steps + 1)

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

    async def _ask_json_decision(self, decision_type: str, messages, default_action, recent_memory: str = "", metadata: str = ""):
        raw_response = await self.decision_agent.ask(messages)
        parsed = parse_decision_json(raw_response, default_action=default_action)
        prompt = self._prompt_text(messages)
        self.logger.log_decision(
            self._current_day(),
            self.unique_id,
            decision_type,
            parsed["action"],
            parsed["reflection"],
            parsed["parse_ok"],
            raw_response,
            prompt,
            recent_memory=recent_memory,
            metadata=metadata,
        )
        if parsed["reflection"]:
            self.add_memory(f"第{self._current_day()}天{decision_type}反思：{parsed['reflection']}")
        return parsed, raw_response

    async def decide_location(self):
        history = "\n".join(self.mems[-5:])
        system_prompt = (
            f"你是名大学生，社交活跃度{self.social_activity}。\n"
            f"一个社交活跃度“很高”的学生非常喜欢参加派对和社交活动，即使在普通的日子里也很有可能外出。\n"
            f"一个社交活跃度“中等”的学生对社交活动持开放态度，但会根据当天的具体情况和心情决定。\n"
            f"一个社交活跃度“较低”的学生更喜欢安静的环境，通常倾向于待在宿舍，除非有特别的理由。"
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

    async def decide_hiv_test(self):
        history = "\n".join(self.mems[-2:])
        system_prompt = (
            f"你今年{self.age}岁，性别{self.gender},是一名在校大学生。\n"
        )
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

            system_prompt_sex = (
                f"你今年{self.age}岁，性别{self.gender},是一名在校大学生。\n"
                f"你的性取向为{self.sexual_orientation}。\n"
            )
            user_prompt_sex = (
                f"你的性伙伴(ID: {pid})年龄是{partner.age}岁,性别{partner.gender}，颜值吸引力{partner.attractiveness}。\n"
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
                system_prompt_condom = (
                    f"你今年{self.age}岁，性别{self.gender},是一名在校大学生。\n"
                    f"你的风险偏好为{self.risk_propensity}。\n"
                )
                user_prompt_condom = (
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

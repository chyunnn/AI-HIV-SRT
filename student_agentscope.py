from agentscope_decision import AgentScopeDecisionAgent
from student import Student


class AgentScopeStudent(Student):
    """Student variant whose LLM decisions are managed by AgentScope."""

    def __init__(self, model, uid: int, profile: dict, logger):
        super().__init__(model, uid, profile, logger)
        self.decision_agent = AgentScopeDecisionAgent(profile)

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
            "你的回答必须且只能是“去娱乐场所”或“待在宿舍”。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            resp_str = await self.decision_agent.ask(messages)
            positive_keywords = ["娱乐", "外出", "社交活动"]
            if any(keyword in resp_str for keyword in positive_keywords):
                self.location = "venue"
            else:
                self.location = "dorm"
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
            "如果进行检测，请回答“1”；如果拒绝检测，请回答“0”。你的回答只能包含一个数字。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            resp_str = await self.decision_agent.ask(messages)
            self.test_today = resp_str.strip().startswith("1")
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
                "如果发生性行为，请回答“1”，如果不发生性行为，请回答“0”。你的回答只能包含一个数字。"
            )
            messages_sex = [
                {"role": "system", "content": system_prompt_sex},
                {"role": "user", "content": user_prompt_sex},
            ]

            sex_today = False
            try:
                resp_sex = await self.decision_agent.ask(messages_sex)
                sex_today = resp_sex.strip().startswith("1")
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
                    "如果使用，请回答“1”，如果不使用，请回答“0”。你的回答只能包含一个数字。"
                )
                messages_condom = [
                    {"role": "system", "content": system_prompt_condom},
                    {"role": "user", "content": user_prompt_condom},
                ]

                try:
                    resp_condom = await self.decision_agent.ask(messages_condom)
                    condom_today = resp_condom.strip().startswith("1")
                except Exception as e:
                    print(f"AgentScope安全套决策错误 (学生ID: {self.unique_id}): {e}. 采用默认选项：不使用.")

            self.sexual_acts[pid] = {"sex": sex_today, "condom": condom_today}

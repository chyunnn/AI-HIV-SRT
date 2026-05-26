import config
import random
from utils import probability_threshold, get_completion_from_messages
import json
import re

class Student:
    def __init__(self, model, uid: int, profile: dict, logger):
        self.model = model
        self.unique_id = uid
        self.logger = logger # ⬅️ 保存 logger 实例
        # 基本信息
        self.name = profile['name']
        self.age = profile['age']
        self.gender = profile['gender']
        # 特征
        self.social_activity = profile['social_activity']
        self.attractiveness = profile['attractiveness']
        self.sexual_orientation = profile['sexual_orientation']
        # self.condom_use_tendency = profile['condom_use_tendency']
        self.risk_propensity = profile['risk_propensity']
        # 状态
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

    # 以下是prompt-based方法，由于与llm交互的成本太高，可以考虑用rule-based
    # def decide_location(self):
    #     history = '\n'.join(self.mems[-5:])
    #     prompt = (
    #         f"You are {self.name}, age {self.age}.\n"
    #         f"Memories:\n{history}\n"
    #         "Should you go to a venue today? Answer Yes or No."
    #     )

    #     resp = get_completion_from_messages([{"role":"user","content":prompt}])
    #     self.location = "venue" if "yes" in resp.lower() else "dorm"
    async def decide_location(self):
        # """基于规则判断是否去娱乐场所"""
        # if self.social_activity == "high":
        #     self.location = "venue" if probability_threshold(0.8) else "dorm"
        # elif self.social_activity == "medium":
        #     self.location = "venue" if probability_threshold(0.4) else "dorm"
        # else:
        #     self.location = "venue" if probability_threshold(0.1) else "dorm"
        """基于LLM判断是否去娱乐场所，通过在prompt中强调社交活跃度来影响决策。
        否则，event无法影响前往娱乐场所的决策，从而使得感染率被锁定。
        """
        history = '\n'.join(self.mems[-5:])
        system_prompt = (
            f"你是名大学生，社交活跃度{self.social_activity}。\n"
            f"一个社交活跃度“很高”的学生非常喜欢参加派对和社交活动，即使在普通的日子里也很有可能外出。\n"
            f"一个社交活跃度“中等”的学生对社交活动持开放态度，但会根据当天的具体情况和心情决定。\n"
            f"一个社交活跃度“较低”的学生更喜欢安静的环境，通常倾向于待在宿舍，除非有特别的理由。"
        )
        user_prompt = (
            # f"今天是校园生活的第{self.model.schedule.steps}天。\n"
            f"你最近的记忆是：\n{history}\n\n"
            f"基于你{self.social_activity}的性格，你今天晚上决定去娱乐场所参加社交活动，还是待在宿舍？\n"
            "你的回答必须且只能是“去娱乐场所”或“待在宿舍”。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        try:
            resp_str = await get_completion_from_messages(messages)
            positive_keywords = ["娱乐", "外出", "社交活动"]
            response_lower = resp_str.lower()
            if any(keyword in response_lower for keyword in positive_keywords):
                self.location = "venue"
            else:
                # 如果回复不清晰或有误，默认选择更安全、更常见的选项
                self.location = "dorm"
        except Exception as e:
            print(f"LLM调用失败 (decide_location, 学生ID: {self.unique_id}): {e}。将采用默认行为（待在宿舍）。")
            self.location = "dorm"

    # def decide_seek_partners(self):
    #     history = '\n'.join(self.mems[-5:])
    #     prompt = (
    #         f"You are {self.name}.\n"
    #         f"Memories:\n{history}\n"
    #         "Do you want to seek new intimate partners today? Answer Yes or No."
    #     )

    #     resp = get_completion_from_messages([{"role":"user","content":prompt}])
    #     self.seek_partners_today = "yes" in resp.lower()
    def decide_seek_partners(self):
        # 前置条件：如果伴侣数量已达到上限，则直接决定不寻找新伴侣
        if len(self.partner_list) >= config.MAX_PARTNERS:
            self.seek_partners_today = False
            return  # 直接结束函数，不再执行后面的概率判断

        """基于规则判断是否寻找新性伙伴"""
        if self.attractiveness == "很高":
            self.seek_partners_today = probability_threshold(0.9)
        elif self.attractiveness == "中等":
            self.seek_partners_today = probability_threshold(0.6)
        else:
            self.seek_partners_today = probability_threshold(0.3)



    # def meet_and_form_relationships(self):
    #     seekers = [a for a in self.model.students if a.seek_partners_today]
    #     for other in seekers:
    #         if other.unique_id <= self.unique_id:
    #             continue
    #         prob = config.VENUE_MEET_PROB if self.location == "venue" else config.CAMPUS_MEET_PROB
    #         if probability_threshold(prob) and len(self.partner_list) < config.MAX_PARTNERS:
    #             self.partner_list.append(other.unique_id)
    #             other.partner_list.append(self.unique_id)
    def meet_and_form_relationships(self):
        """基于概率与其他 seek-partner 学生建立关系"""
        seekers = [a for a in self.model.students if a.seek_partners_today]
        for other in seekers:
            if other.unique_id <= self.unique_id:
                continue
            prob = config.VENUE_MEET_PROB if self.location == "venue" else config.CAMPUS_MEET_PROB
            if probability_threshold(prob) and len(self.partner_list) < config.MAX_PARTNERS and len(other.partner_list) < config.MAX_PARTNERS:
                self.partner_list.append(other.unique_id)
                other.partner_list.append(self.unique_id)
                #为双方建立关系添加记忆
                # day = self.model.schedule.steps
                # memory_text = f"你在第{day}天和另一位同学(ID: {other.unique_id})建立起了性亲密关系。"
                # self.add_memory(memory_text)

                # other_memory_text = f"你在第{day}天和另一位同学(ID: {self.unique_id})建立起了性亲密关系。"
                # other.add_memory(other_memory_text)


    # def decide_end_partnerships(self):
    #     new_list = []
    #     for pid in self.partner_list:
    #         if probability_threshold(0.2):
    #             continue
    #         partner = self.model.students[pid]
    #         history = '\n'.join(self.mems[-5:])
    #         prompt = (
    #             f"You are {self.name}.\n"
    #             f"Memories:\n{history}\n"
    #             f"Should you end your relationship with {partner.name}? Answer Yes or No."
    #         )

    #         resp = get_completion_from_messages([{"role":"user","content":prompt}])
    #         if "no" in resp.lower():
    #             new_list.append(pid)
    def decide_end_partnerships(self):
        """基于规则判断是否结束当前关系，并为双方添加记忆"""
        new_list = []
        for pid in self.partner_list:
            if probability_threshold(0.1):  # 10% 概率结束关系
                # day = self.model.schedule.steps
                # self.add_memory(f"你和你的伴侣(ID: {pid})分手了。")

                #同时解除对方和自己的亲密伴侣关系
                partner = self.model.students[pid]
                if self.unique_id in partner.partner_list:
                    partner.partner_list.remove(self.unique_id)
                    # partner.add_memory(f"你和你的伴侶(ID: {self.unique_id})分手了。")
            
                continue
            new_list.append(pid)
        self.partner_list = new_list

    # ==============================================================================
    # ⬇️ 新增：独立的HIV检测决策方法
    # ==============================================================================
    async def decide_hiv_test(self):
        """每天独立决策是否进行HIV检测"""
        history = '\n'.join(self.mems[-2:])
        system_prompt = (
            f"你今年{self.age}岁，性别{self.gender},是一名在校大学生。\n"
            # f"你的社交活跃度{self.social_activity}，颜值吸引力{self.attractiveness}，风险偏好为{self.risk_propensity}，性取向为{self.sexual_orientation}。\n"
            # f"你会根据个人特点与校园内获得的新信息调整自身决定。"
        )


        user_prompt = (
            f"你近期的记忆是：\n{history}\n\n"
            "基于以上所有信息，你今天会去进行HIV检测吗？\n"
            "如果进行检测，请回答“1”；如果拒绝检测，请回答“0”。你的回答只能包含一个数字。"
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

        try:
            resp_str = await get_completion_from_messages(messages)
            self.test_today = "1" in resp_str
        except Exception as e:
            print(f"agentHIV检测决策的LLM回复错误. 采用默认选项：不检测.")
            self.test_today = False

    # ==============================================================================
    # ⬇️ 新增：拆分后的性行为与安全套决策方法
    # ==============================================================================
    async def decide_sexual_activity(self):
        """为每个伴侣分别决策是否发生性行为，以及是否使用安全套"""
        self.sexual_acts = {}
        if not self.partner_list:
            return

        for pid in self.partner_list:
            partner = self.model.students[pid]
            history = '\n'.join(self.mems[-2:])
            
            # --- 第1步：决策是否发生性行为 ---
            system_prompt_sex = (
                f"你今年{self.age}岁，性别{self.gender},是一名在校大学生。\n"
                f"你的性取向为{self.sexual_orientation}。\n"
                # f"请你带入你的个人信息和特点，进行后续决策。"
            )
            user_prompt_sex = (
                f"你的性伙伴(ID: {pid})年龄是{partner.age}岁,性别{partner.gender}，颜值吸引力{partner.attractiveness}。\n"
                f"你近期的记忆是：\n{history}\n\n"
                # "{history}"
                "根据以上信息决定，你会和这位性伴侣发生性行为吗？\n"
                "如果发生性行为，请回答“1”，如果不发生性行为，请回答“0”。你的回答只能包含一个数字。"
            )
            messages_sex = [{"role": "system", "content": system_prompt_sex}, {"role": "user", "content": user_prompt_sex}]

            sex_today = False
            try:
                resp_sex = await get_completion_from_messages(messages_sex)
                sex_today = "1" in resp_sex
            except Exception as e:
                print(f"agent进行性行为决策发生llm回复错误. 采取默认选项：否.")
                sex_today = False

            # --- 第2步：如果发生性行为，决策是否使用安全套 ---
            condom_today = False # 默认为不使用
            if sex_today:
                system_prompt_condom = (
                    f"你今年{self.age}岁，性别{self.gender},是一名在校大学生。\n"
                    f"你的风险偏好为{self.risk_propensity}。\n"
                    # f"你会根据校园内得到的新信息调整这一决定。"
                )
                user_prompt_condom = (
                    # f"你已经决定今天和你的伴侣(ID: {pid})发生性行为。\n"
                    f"你近期的记忆是：\n{history}\n\n"
                    # "{history}"
                    "根据以上信息决定，你会在性行为中使用安全套吗？\n"
                    "如果使用，请回答“1”，如果不使用，请回答“0”。你的回答只能包含一个数字。"
                )
                messages_condom = [{"role": "system", "content": system_prompt_condom}, {"role": "user", "content": user_prompt_condom}]
                
                try:
                    resp_condom = await get_completion_from_messages(messages_condom)
                    condom_today = "1" in resp_condom
                except Exception as e:
                    print(f"agent进行安全套决策发生llm回复错误.采用默认选项：不使用.")
                    condom_today = False

            # --- 第3步：记录最终决策 ---
            self.sexual_acts[pid] = {'sex': sex_today, 'condom': condom_today}



    # 弃用原来的make_decisions函数




    # 重大修修改！！！！！！1011，将step方法拆分为prepare和finalize两个部分
    # 从而将agent的决策和agent之间的互动完全分割开
    async def prepare_step(self):
        """第一阶段：准备和决策。只更新自己的状态，不依赖他人当天的决策。"""
        # 重置当日状态
        self.test_today = False

        # 执行不依赖他人的行为
        self.decide_end_partnerships()
        await self.decide_location()
        self.decide_seek_partners()
        if self.seek_partners_today:
            self.meet_and_form_relationships()

        # 进行LLM决策
        await self.decide_hiv_test()
        await self.decide_sexual_activity()

        
    # 这个函数不应当是异步的，会造成bug
    def finalize_step(self):
        # 重置当日检测标志
        # self.test_today = False

        # self.decide_end_partnerships()
        # await self.decide_location()
        # self.decide_seek_partners()
        # if self.seek_partners_today:
        #     self.meet_and_form_relationships()

        # # await self.decide_behaviors()
        # # await self.decide_hiv_test()
        # await self.decide_hiv_test()        # 决策是否检测
        # await self.decide_sexual_activity() # 决策性行为和安全套

        if self.location == "venue" and self.health_condition == "Susceptible":
            if probability_threshold(config.VENUE_INFECT_PROB):
                self.health_condition = "To_Be_Infected"
                self.infection_source = "venue"
        # for pid, act in self.sexual_acts.items():
        #     if not act['sex']:
        #         continue
        #     other = self.model.students[pid]
        #     other_act = other.sexual_acts.get(self.unique_id, {'sex':False,'condom':True})
        #     if not other_act['sex'] or act['condom'] or other_act['condom']:
        #         continue
        #     if self.sexual_orientation != other.sexual_orientation:
        #         trans_prob = config.HETERO_INFECT_RATE
        #     elif self.sexual_orientation=='homosexual':
        #         if self.gender=='male' and other.gender=='male':
        #             trans_prob = config.HOMO_MALE_INFECT_RATE
        #         elif self.gender=='female' and other.gender=='female':
        #             trans_prob = config.HOMO_FEMALE_INFECT_RATE
        #         else:
        #             trans_prob = config.HETERO_INFECT_RATE
        #     else:
        #         trans_prob = config.HETERO_INFECT_RATE
        #     if probability_threshold(trans_prob):
        #         other.health_condition = "To_Be_Infected"
        #         other.infection_source = "unprotected_sex"
        # 遍历学生今天发起的所有性行为意向
        for pid, self_act in self.sexual_acts.items():
            # 为了避免重复计算（A->B 和 B->A），我们只让ID较小的学生来处理互动
            if self.unique_id > pid:
                continue
            #性行为有一方同意即可发生
            other = self.model.students[pid]
            other_act = other.sexual_acts.get(self.unique_id)
            sex_happens = (self_act and self_act.get('sex', False)) or \
                          (other_act and other_act.get('sex', False))
            if not sex_happens:
                continue

            # # 检查是否是“双向奔赴”：对方也必须同意
            # if not other_act or not other_act.get('sex', False):
            #     continue

            # 不使用安全套需要双方同意
            self_wants_condom = self_act and self_act.get('condom', False)
            other_wants_condom = other_act and other_act.get('condom', False)
            if self_wants_condom or other_wants_condom:
                continue
            # self_wants_unprotected = self_act and not self_act.get('condom', True)
            # other_wants_unprotected = other_act and not other_act.get('condom', True)
            # is_unprotected = self_wants_unprotected or other_wants_unprotected
            # if not is_unprotected:  
            #     continue

            # --- 如果代码执行到这里，说明发生了一次双方同意的无保护性行为 ---

            # 确定感染者和易感者
            infected_one, susceptible_one = None, None
            if "Infected" in self.health_condition and other.health_condition == "Susceptible":
                infected_one, susceptible_one = self, other
            elif "Infected" in other.health_condition and self.health_condition == "Susceptible":
                infected_one, susceptible_one = other, self
            else:
                continue # 如果双方都健康或都已感染，则跳过

            # 计算传播概率
            # 检查是否为男男性行为
            if infected_one.gender == '男' and susceptible_one.gender == '男':
                trans_prob = config.HOMO_MALE_INFECT_RATE
            # 检查是否为女女性行为
            elif infected_one.gender == '女' and susceptible_one.gender == '女':
                trans_prob = config.HOMO_FEMALE_INFECT_RATE
            # 其他所有情况（即男女行为）
            else:
                trans_prob = config.HETERO_INFECT_RATE
            # trans_prob = config.HETERO_INFECT_RATE # 默认为异性恋概率
            # if infected_one.sexual_orientation != susceptible_one.sexual_orientation:
            #     trans_prob = config.HETERO_INFECT_RATE
            # elif infected_one.sexual_orientation == 'homosexual':
            #     if infected_one.gender == 'male' and susceptible_one.gender == 'male':
            #         trans_prob = config.HOMO_MALE_INFECT_RATE
            #     elif infected_one.gender == 'female' and susceptible_one.gender == 'female':
            #         trans_prob = config.HOMO_FEMALE_INFECT_RATE

            # 进行感染判定
            if probability_threshold(trans_prob):
                susceptible_one.health_condition = "To_Be_Infected"
                susceptible_one.infection_source = "unprotected_sex"
    def update_health(self):
        """
        更新健康状态：将 To_Be_Infected 转为 Infected_Undiagnosed，并累加感染天数
        """
        if self.health_condition == "To_Be_Infected":
            self.health_condition = "Infected_Undiagnosed"
            self.day_infected = 0
            self.logger.log_infected_profile(self.model.schedule.steps, self)
        elif self.health_condition == "Infected_Undiagnosed":
            self.day_infected += 1
            if self.test_today:
                self.health_condition = "Infected_Diagnosed"
                day = self.model.schedule.steps
                self.add_memory(f"你经过检测后知道了自己已感染艾滋病病毒。")
        elif self.health_condition == "Infected_Diagnosed":
            self.day_infected += 1

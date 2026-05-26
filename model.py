import config
from student import Student
from event import EventManager
from utils import generate_student_profiles
import asyncio # 导入 asyncio


class SimpleSchedule:
    def __init__(self):
        self.steps = 0


class SimulationModel:
    def __init__(self, args,logger, student_cls=Student):
        self.schedule = SimpleSchedule()
        self.event_manager  = EventManager()
        self.students       = [] # ⬅️ 这是一个列表
        # ⬅️ 保存 logger 实例
        self.logger = logger
        profile_source = getattr(args, "profile_source", "random")
        profile_data = getattr(args, "profile_data", None)
        profiles = generate_student_profiles(
            args.population,
            source=profile_source,
            data_path=profile_data,
        )
        for i, prof in enumerate(profiles):
            s = student_cls(self, i, prof,self.logger)
            self.students.append(s)
            #self.schedule.add(s)
    
    
    #重要更新！！！！1011，在这里分别调用prepare_step和finalize_step
    async def step(self):
        day = self.schedule.steps
        self.event_manager.dispatch(day, self)

        # #self.schedule.step()
        # tasks = [s.step() for s in self.students]
        # # 2. 使用 asyncio.gather 并发运行所有 task
        # #    这将同时启动所有学生的决策过程（LLM调用）
        # await asyncio.gather(*tasks)
        # for s in self.students:
        #     s.update_health()
        # # 手动增加Mesa的步数，因为我们没有调用 schedule.step()
        #——————第一阶段，所有agent完成决策
        prepare_tasks = [s.prepare_step() for s in self.students]
        await asyncio.gather(*prepare_tasks)

        # --- 在这里，所有学生的LLM调用都已完成，sexual_acts都已更新为当天的数据 ---

        # --- 第二阶段：依次执行所有学生的互动 ---
        # 互动阶段是纯计算，不涉及IO等待，不需要并发
        for s in self.students:
            s.finalize_step()

        # --- 第三阶段：统一更新所有人的健康状态 ---
        for s in self.students:
            s.update_health()

        self.schedule.steps += 1

    async def run(self, steps):
        # 1. 在开头创建一个空字典来存储结果
        results_at_checkpoints = {}
        for day in range(1, steps + 1):
            await self.step()

            #记录当天所有学生的详细状态
            self.logger.log_daily_agent_states(day, self.students)

            # ⬅️ 记录群体数据 (重构后的统一逻辑)
            # 1. 先统计与个体直接相关的指标
            tested_count_today = sum(1 for s in self.students if s.test_today)
            infected_count = sum(1 for s in self.students if s.health_condition != "Susceptible")
            
            # 2. 在一个统一的循环中，计算所有与“伴侣对”相关的指标
            total_sexual_acts_today = 0
            condom_acts_today = 0
            counted_pairs = set() # 用于防止重复计算 A->B 和 B->A

            for s in self.students:
                # 只需遍历伴侣列表，因为 sexual_acts 是基于它的
                for partner_id in s.partner_list:
                    pair = tuple(sorted((s.unique_id, partner_id)))
                    if pair in counted_pairs:
                        continue
                    
                    other = self.students[partner_id]
                    self_act = s.sexual_acts.get(partner_id)
                    other_act = other.sexual_acts.get(s.unique_id)

                    # 判断性行为是否实际发生 (至少一方同意)
                    sex_happens = (self_act and self_act.get('sex', False)) or \
                                  (other_act and other_act.get('sex', False))
                    
                    if sex_happens:
                        # 如果性行为发生，总数加一
                        total_sexual_acts_today += 1
                        
                        # 接着判断这次行为是否使用了安全套 (至少一方同意使用)
                        self_used_condom = self_act and self_act.get('condom', False)
                        other_used_condom = other_act and other_act.get('condom', False)
                        
                        if self_used_condom or other_used_condom:
                            condom_acts_today += 1
                    
                    counted_pairs.add(pair)

            total_condom_intentions = sum(
                1 for s in self.students if s.sexual_acts and 
                any(act.get('condom', False) for act in s.sexual_acts.values())
            )

            # 3. 按感染源进行分类统计 (这个逻辑保持不变)
            infected_by_venue = sum(1 for s in self.students if s.infection_source == "venue")
            infected_by_sex = sum(1 for s in self.students if s.infection_source == "unprotected_sex")
            
            # 4. 调用日志，并使用新的变量名 condom_acts_today
            self.logger.log_population_stats(day, len(self.students), infected_count, infected_by_venue, infected_by_sex, tested_count_today, condom_acts_today, total_sexual_acts_today, total_condom_intentions)

            # 5. 更新print语句
            print(f"Day {day}: Infected = {infected_count} (Venue: {infected_by_venue}, Sex: {infected_by_sex}), Tested = {tested_count_today}, Condom Acts = {condom_acts_today}, Total Acts = {total_sexual_acts_today}, Condom Intentions = {total_condom_intentions}")


             # 6. 检查当前日期是否是我们关心的“检查点” (10, 20, 30, ...)
            if day % 10 == 0:
                # 将当天的感染人数存入字典
                results_at_checkpoints[f'day_{day}'] = infected_count
                results_at_checkpoints[f'day_{day}_tested'] = tested_count_today
                results_at_checkpoints[f'day_{day}_condom_acts'] = condom_acts_today
                results_at_checkpoints[f'day_{day}_infected_venue'] = infected_by_venue
                results_at_checkpoints[f'day_{day}_infected_sex'] = infected_by_sex

        return results_at_checkpoints
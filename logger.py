import csv
import os
from datetime import datetime

class SimulationLogger:
    def __init__(self, output_dir="outputs", run_id=1):
        """
        初始化日志器。
        为本次模拟运行创建一个唯一的、带时间戳的文件夹。
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 为每次运行创建一个单独的文件夹，例如: outputs/20250823_172000_run_1
        self.run_output_dir = os.path.join(output_dir, f"{timestamp}_run_{run_id}")
        os.makedirs(self.run_output_dir, exist_ok=True)

        # 定义三个日志文件的路径
        self.population_log_path = os.path.join(self.run_output_dir, "population_log.csv")
        self.daily_agent_state_path = os.path.join(self.run_output_dir, "daily_agent_state.csv")
        self.infected_profiles_path = os.path.join(self.run_output_dir, "infected_profiles.csv")
        self.decision_log_path = os.path.join(self.run_output_dir, "decision_log.csv")

        # --- 初始化每个日志文件并写入表头 ---

        # 1. 初始化群体数据日志
        with open(self.population_log_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Day', 'Total_Population', 'Infected_Count', 'Infected_Venue', 'Infected_Sex', 'Tested_Count', 'Condom_Acts_Count', 'Total_Sexual_Acts', 'Condom_intentions_Count', 'Average_Awareness'])

        # 2. 初始化每日学生状态日志
        with open(self.daily_agent_state_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Day', 'Student_ID', 'Health_Condition', 'Partners_Count',
                'Had_Sex_Today', 'Used_Condom_Today', 'Tested_Today', 'Location', 'Awareness'
            ])

        # 3. 初始化感染者档案日志
        with open(self.infected_profiles_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Day_Infected', 'Student_ID', 'Age', 'Gender', 'Social_Activity',
                'Attractiveness', 'Sexual_Orientation', 'Risk_Propensity', 'Infection_Source'
            ])

        # 4. 初始化 LLM 决策过程日志
        with open(self.decision_log_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Day', 'Student_ID', 'Decision_Type', 'Parsed_Action', 'Reflection',
                'Parse_OK', 'Raw_Response', 'Prompt', 'Recent_Memory', 'Metadata'
            ])

    def log_population_stats(self, day: int, total_students: int, infected_count: int, infected_venue_count: int, infected_sex_count: int, tested_count: int, condom_acts_count: int, total_sexual_acts: int, condom_intentions_count: int, average_awareness: float = 0.0):
        """记录每日的宏观群体数据"""
        with open(self.population_log_path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([day, total_students, infected_count, infected_venue_count, infected_sex_count, tested_count, condom_acts_count, total_sexual_acts, condom_intentions_count, average_awareness])

    def log_daily_agent_states(self, day: int, students: list):
        """
        记录当天所有学生的详细状态。
        这个函数应该在每天所有学生完成决策后被调用一次。
        """
        rows_to_write = []
        for s in students:
            # 判断学生今天是否有性行为
            # had_sex = "yes" if s.sexual_acts else "no"
            had_sex = "no"
            if s.sexual_acts:
                if any(act.get('sex', False) for act in s.sexual_acts.values()):
                    had_sex = "yes"


            # 判断学生今天是否使用了安全套 (只要有一次使用就算)
            used_condom = "no"
            if had_sex == "yes": # 只有在实际发生性行为时，才判断是否使用安全套
                if any(act.get('condom', False) for act in s.sexual_acts.values()):
                    used_condom = "yes"
            # if s.sexual_acts:
                # # 只要任意一次性行为使用了安全套，就记录为 "yes"
                # if any(act.get('condom', False) for act in s.sexual_acts.values()):
                #     used_condom = "yes"

            tested_today = "yes" if s.test_today else "no"

            rows_to_write.append([
                day, s.unique_id, s.health_condition, len(s.partner_list),
                had_sex, used_condom, tested_today, s.location, getattr(s, "awareness", "")
            ])

        with open(self.daily_agent_state_path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(rows_to_write)

    def log_infected_profile(self, day: int, student):
        """
        当一个学生首次被感染时，记录下他的完整个人档案。
        """
        with open(self.infected_profiles_path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                day, student.unique_id, student.age, student.gender, student.social_activity,
                student.attractiveness, student.sexual_orientation, student.risk_propensity,
                student.infection_source
            ])

    def log_decision(self, day: int, student_id: int, decision_type: str, parsed_action, reflection: str, parse_ok: bool, raw_response: str, prompt: str, recent_memory: str = "", metadata: str = ""):
        """记录每一次 LLM 决策的 prompt、反思与最终 action。"""
        with open(self.decision_log_path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                day, student_id, decision_type, parsed_action, reflection,
                "yes" if parse_ok else "no", raw_response, prompt, recent_memory, metadata
            ])



class EventManager:
    def __init__(self):
        # day(int) -> List[str] 事件文本列表
        self.schedule = {}

    def schedule_event(self, day: int, text: str):
        """在指定 day 注入 event 文本"""
        self.schedule.setdefault(day, []).append(text)

    def dispatch(self, day: int, model):
        """把事件记忆注入所有学生"""
        for text in self.schedule.get(day, []):
            for agent in model.students:
                if hasattr(agent, "receive_event"):
                    agent.receive_event(text)
                else:
                    agent.add_memory(text)
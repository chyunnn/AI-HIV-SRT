import argparse
import asyncio
import random
import sys

import config
from logger import SimulationLogger
from model import SimulationModel
from student_agentscope import AgentScopeStudent


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SCENARIOS = {
    "lecture": """
校园内进行了艾滋病科普教育，内容如下：
艾滋病没有预防疫苗，无法治愈。
艾滋病病毒主要通过体液传播，无保护性行为是主要传播方式。
艾滋病预防：
1. 洁身自爱、遵守性道德是预防经性途径传染艾病毒的根本措施。
2. 选择质量合格的安全套，确保每次全程正确使用安全套。
感染艾滋病病毒只能通过检测来确定。
国家对个人接受自愿咨询检测的信息实行严格的保密措施。
""",
    "campaign": """
学校开展防艾宣传活动，设置咨询摊位、发放安全套，并用海报和短视频介绍艾滋病预防、检测与反歧视知识。
活动鼓励同学在亲密关系中主动沟通安全措施，并在有风险暴露后及时寻求检测和咨询。
""",
    "police": """
重要通知：
学校将加强对校园内涉及 HIV 传播相关行为的社会治安管理。
任何明知自己感染 HIV 而故意进行无保护性行为，导致他人感染的，将承担严重法律后果。
请全体同学提高法律意识和责任意识，保护自己，同时尊重他人的生命健康权。
""",
    "self_test": """
通知：学校在各宿舍楼与教学楼放置了 HIV 自助检测机，能够匿名、保密、可靠地进行病毒检测。
检测成本很低，可以通过手机获得检测结果，保障个人隐私。
""",
    "venue_warning": """
鉴于近期校园周边娱乐场所发生数起治安事件，校学生处及保卫处提醒：
请全体同学近期减少或避免前往人员复杂、环境不明的校外娱乐场所，尤其是在夜间。
若确需外出，请务必结伴而行，并告知室友或朋友你的去向。
""",
    "placebo": """
诺贝尔经济学奖颁给了一位美国经济学家。
""",
}


def schedule_scenario(model, scenario: str, day: int):
    if scenario == "none":
        return
    model.event_manager.schedule_event(day, SCENARIOS[scenario])


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--population", type=int, default=config.POPULATION)
    parser.add_argument("--days", type=int, default=config.MAX_STEPS)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--runs", type=int, default=1, help="Number of simulation runs")
    parser.add_argument(
        "--profile-source",
        choices=["random", "ncss"],
        default="random",
        help="Use random rules or NCSS-SRH empirical distribution for initial profiles",
    )
    parser.add_argument(
        "--profile-data",
        default=None,
        help="Path to NCSS-SRH .dta file. Defaults to ../91-王泽宇-2025.dta when profile-source=ncss",
    )
    parser.add_argument(
        "--scenario",
        choices=["none", *SCENARIOS.keys()],
        default="none",
        help="Scenario event injected into all agents' memories",
    )
    parser.add_argument("--event-day", type=int, default=5, help="Day index used by EventManager")
    parser.add_argument("--output-dir", default="outputs_agentscope")
    args = parser.parse_args()

    all_runs_data = []
    for i in range(args.runs):
        print(f"=============== 开始 AgentScope 模拟： {i + 1}/{args.runs} ================")
        random.seed(args.seed + i)

        logger = SimulationLogger(output_dir=args.output_dir, run_id=i + 1)
        model = SimulationModel(args, logger, student_cls=AgentScopeStudent)
        schedule_scenario(model, args.scenario, args.event_day)

        print(
            f"开始模拟: 总人数={args.population}, 天数={args.days}, "
            f"profile_source={args.profile_source}, scenario={args.scenario}, "
            f"event_day={args.event_day}"
        )
        run_result = await model.run(args.days)
        run_result["run_id"] = i + 1
        all_runs_data.append(run_result)
        print(f"=============== 结束模拟 {i + 1}, 结果: {run_result} ================\n")

    print(f"\nAgentScope 模拟结束. All {args.runs} runs are finished.")
    print(f"详细日志已保存至 {args.output_dir}")
    print(f"汇总结果: {all_runs_data}")


if __name__ == "__main__":
    asyncio.run(main())

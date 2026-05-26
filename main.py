import argparse
import config
from model import SimulationModel
import asyncio # 导入 asyncio
from logger import SimulationLogger
import random
import csv



async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--population", type=int, default=config.POPULATION)
    parser.add_argument("--days", type=int, default=config.MAX_STEPS)
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
     # 新增一个参数用于控制模拟次数
    parser.add_argument('--runs', type=int, default=5, help='Number of simulation runs')
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
    args = parser.parse_args()

    # 准备一个列表，用于存储每一次模拟的结果
    all_runs_data = []

    # 开始进行5次模拟的大循环
    for i in range(args.runs):
        print(f"=============== 开始模拟： {i + 1}/{args.runs} ================")
        # 关键一步：为每次模拟设置不同的随机种子，确保结果不同
        # 我们在基础种子上加上循环的序号i
        random.seed(args.seed + i)
        # ⬅️ 在这里创建日志器实例
        # 每次循环都创建全新的logger和model实例
        logger = SimulationLogger(output_dir="outputs", run_id = i + 1)
        # ⬅️ 将日志器实例传递给 SimulationModel
        model = SimulationModel(args,logger)


       #————————————————————————————————————————————————————————————————————
        event_day_lecture = 5
        event_text_lecture = '''
        校园内进行了艾滋病科普教育，内容如下：
        艾滋病没有预防疫苗，无法治愈。
        艾滋病病毒主要通过体液传播，无保护性行为是主要传播方式。
        艾滋病预防：
        1. 洁身自爱、遵守性道德是预防经性途径传染艾病毒的根本措施。
        2. 选择质量合格的安全套，确保每次全程正确使用安全套。
        感染艾滋病病毒只能通过检测来确定：
        根据国务院颁布的《艾滋病防治条例》，国家对个人接受自愿咨询检测的信息实行严格的保密措施。
        国家实施免费的艾滋病自愿咨询检测。自愿接受艾滋病咨询和检测的人员，可在各级疾病预防控制中心和卫生行政部门指定的医疗机构（自愿咨询检测门诊）得到免费咨询和艾滋病病毒抗体初筛检测。
        '''
        #这是防艾宣讲事件开关
        # model.event_manager.schedule_event(event_day_lecture, event_text_lecture)
        

        #这是公安介入事件————————————————————————————————————————————————————————
        event_text_police = '''
        重要通知：

        根据上级公安机关最新指示精神，为维护校园安全与公共卫生秩序，将加强对校园内涉及艾滋病（HIV）传播相关行为的社会治安管理。
        具体通告如下：
        1.  依据《中华人民共和国刑法》及相关司法解释，任何明知自己感染艾滋病病毒而故意进行无保护性行为，导致他人感染的，将被视为严重危害公共安全的行为。
        2.  执法机关将对此类行为予以严厉打击，一经查实，将依法追究当事人的刑事责任。
        3.  请全体同学提高法律意识和责任意识，保护自己，同时尊重他人的生命健康权。任何可能危害他人健康的行为都将承担严重的法律后果。
        '''

        event_day_police = 5
        #这是公安介入政策开关
        # model.event_manager.schedule_event(event_day_police, event_text_police)

        #——————————————————————————————————————————————————————————————————————————————
        event_text_zizhu = """
        通知：学校在各宿舍楼与教学楼放置了艾滋病病毒自助检测机，能够匿名、保密、可靠地进行病毒检测。
        检测成本极低，只需要几块钱。
        同学们可以通过手机获得检测结果，保障个人隐私。
        """
        event_day_zizhu = 5
        #这是自助检测机的开关
        # model.event_manager.schedule_event(event_day_zizhu, event_text_zizhu)

        #——————————————————————————————————————————————————————————————————————————————————
        event_text_venue = '''
        鉴于近期校园周边娱乐场所（如酒吧、KTV等）发生数起治安事件，为切实保障同学们的个人安全，校学生处及保卫处联合发布以下提醒：
        请全体同学近期**减少或避免**前往人员复杂、环境不明的校外娱乐场所，尤其是在夜间。
        若确需外出，请务必结伴而行，并告知室友或朋友你的去向。
        请大家务必提高警惕，将人身安全放在首位。
        '''
        event_day_venue = 5
        #model.event_manager.schedule_event(event_day_venue, event_text_venue)

        #———————————————————————————————————————————————————————————————————————————————————
        event_day_placebo = 5
        event_text_placebo = '''
        诺贝尔经济学奖颁给了一位美国经济学家。
        '''
        #这是安慰剂的开关
        # model.event_manager.schedule_event(event_day_placebo, event_text_placebo)


        print(f"开始模拟: 总人数={args.population}, 天数={args.days}, profile_source={args.profile_source}")
    
 
        # 运行模型，并接收返回的检查点数据
        run_result = await model.run(args.days)
        # 将运行序号（run_id）也添加到结果中
        run_result['run_id'] = i + 1
        # 将本次运行的结果添加到总列表中
        all_runs_data.append(run_result)
        print(f"=============== 结束模拟 {i + 1}, 结果: {run_result} ================\n")


    # # 每完成一轮 step 后汇报一次(这是以前的代码，没有引入logger)
    # for day in range(1, args.steps + 1):
    #     await model.step()
    #     infected_count = sum(1 for s in model.students if s.health_condition != "Susceptible")
    #     print(f"Day {day}: Total infected = {infected_count}/{args.population}")
    
    
    # --- 所有模拟运行结束后，将数据写入CSV文件 ---
    # 注意，每次模拟需要修改这里的文件保存名称
    output_filename = "simulation_summary_education_event（1）.csv"

    # # 定义表头，从 day_10 到 day_100
    # fieldnames = ['run_id']
    # for day in range(10, args.days + 1, 10):
    #     fieldnames.append(f'day_{day}_infected')
    #     fieldnames.append(f'day_{day}_tested')
    #     fieldnames.append(f'day_{day}_condom_users')
    #     fieldnames.append(f'day_{day}_infected_venue')
    #     fieldnames.append(f'day_{day}_infected_sex')
    
    # with open(output_filename, 'w', newline='', encoding='utf-8') as f:
    #     writer = csv.DictWriter(f, fieldnames=fieldnames)
    #     writer.writeheader() # 写入表头
    #     writer.writerows(all_runs_data) # 写入所有数据
    print(f"\n模拟结束. All {args.runs} runs are finished.")
    print(f"模拟结果保存至 {output_filename}")


    # 程序入口
if __name__ == "__main__":
    # 使用 asyncio.run() 来启动异步主函数
    asyncio.run(main())
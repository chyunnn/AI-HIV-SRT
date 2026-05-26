# Running the AgentScope Version

This project includes an AgentScope-based version of the HIV social simulation. In this version, student profiles can be initialized from the NCSS-SRH survey distribution, while each student agent uses AgentScope to call DeepSeek for behavior decisions such as location choice, HIV testing, sexual activity, and condom use.

## 1. Install Dependencies

Run the following commands in PowerShell:

```powershell
python -m pip install -r requirements.txt
```

## 2. Set Environment Variables

Do not hard-code API keys in Python files. Set the DeepSeek API key in the current PowerShell session:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

The AgentScope version reads the key from `DEEPSEEK_API_KEY`.

## 3. Quick Checks

Check whether AgentScope and the simulation entrypoint can be imported:

```powershell
python -c "import agentscope; import main_agentscope; print('AgentScope import ok')"
```

Check whether NCSS-SRH based profile generation works:

```powershell
python -c "from utils import generate_student_profiles; print(generate_student_profiles(3, source='ncss'))"
```

If this prints three `Student` profiles, the survey-based initialization is working.

## 4. Run a Small Test

Start with a very small run to confirm that DeepSeek can be called through AgentScope:

```powershell
python main_agentscope.py --population 1 --days 1 --runs 1 --profile-source ncss --scenario none
```

If successful, the terminal should show agent decisions and a daily summary such as `Day 1: Infected = ...`.
The full reasoning process is saved in `decision_log.csv`.

## 5. Run Baseline and Intervention Experiments

Run a baseline group without intervention:

```powershell
python main_agentscope.py --population 10 --days 5 --runs 1 --seed 42 --profile-source ncss --scenario none --output-dir outputs_baseline_seed42
```

Run a lecture intervention group:

```powershell
python main_agentscope.py --population 10 --days 5 --runs 1 --seed 42 --profile-source ncss --scenario lecture --event-day 1 --output-dir outputs_lecture_seed42
```

Using the same seed makes the two runs easier to compare.

## 6. Output Files

Each run creates a timestamped folder inside the selected output directory. The main files are:

- `population_log.csv`: daily aggregate outcomes, including infections, HIV testing, sexual acts, and condom use.
- `daily_agent_state.csv`: daily state of each student agent.
- `infected_profiles.csv`: profile records for newly infected agents.
- `decision_log.csv`: each AgentScope/DeepSeek decision, including prompt, raw response, parsed action, and one-sentence reflection.

For example, this command:

```powershell
python main_agentscope.py --population 10 --days 5 --runs 1 --profile-source ncss --scenario lecture --output-dir outputs_lecture_seed42
```

will create a folder similar to:

```text
outputs_lecture_seed42/
└── 20260526_203202_run_1/
    ├── population_log.csv
    ├── daily_agent_state.csv
    ├── infected_profiles.csv
    └── decision_log.csv
```

## 7. How to Read the Results

Use `population_log.csv` for high-level intervention outcomes. Each row represents one simulated day.

Important columns:

- `Infected_Count`: total number of infected agents by that day.
- `Infected_Venue`: infections caused by venue exposure.
- `Infected_Sex`: infections caused by unprotected sex.
- `Tested_Count`: number of agents who chose HIV testing on that day.
- `Condom_Acts_Count`: number of sexual acts where condom use occurred.
- `Total_Sexual_Acts`: total number of sexual acts on that day.
- `Condom_intentions_Count`: number of agents who expressed condom-use intention.

Use `daily_agent_state.csv` to inspect individual behavior trajectories. Each row is one agent on one day.

Important columns:

- `Health_Condition`: `Susceptible`, `Infected_Undiagnosed`, or `Infected_Diagnosed`.
- `Partners_Count`: number of current intimate partners.
- `Had_Sex_Today`: whether the agent had sex on that day.
- `Used_Condom_Today`: whether condom use occurred.
- `Tested_Today`: whether the agent chose HIV testing.
- `Location`: `dorm` or `venue`.

Use `decision_log.csv` to inspect the AgentScope/DeepSeek decision process.

Important columns:

- `Decision_Type`: the decision being made, such as `location`, `hiv_test`, `sexual_activity`, or `condom_use`.
- `Prompt`: the prompt sent to the model.
- `Raw_Response`: the original DeepSeek response.
- `Reflection`: the model's one-sentence reasoning before action.
- `Parsed_Action`: the action extracted by the simulation.
- `Parse_OK`: whether the JSON response was parsed successfully.
- `Recent_Memory`: the agent's recent memory used in the prompt.
- `Metadata`: additional context such as partner ID.

Use `infected_profiles.csv` only when infections occur. It records the profile and infection source for newly infected agents.

## 8. Comparing Baseline and Intervention

For intervention analysis, compare the following columns in `population_log.csv`:

- `Infected_Count`
- `Tested_Count`
- `Condom_Acts_Count`
- `Total_Sexual_Acts`
- `Condom_intentions_Count`

Interpretation guide:

- If `Tested_Count` increases after an intervention, the intervention may be increasing HIV testing willingness.
- If `Condom_Acts_Count` or `Condom_intentions_Count` increases, the intervention may be improving protective behavior.
- If `Total_Sexual_Acts` decreases, the intervention may be reducing risky encounters.
- If `Infected_Count` decreases across repeated runs, the intervention may reduce simulated infection risk.

For a more reliable comparison, run multiple repetitions:

```powershell
python main_agentscope.py --population 20 --days 7 --runs 3 --seed 42 --profile-source ncss --scenario none --output-dir outputs_baseline_test
python main_agentscope.py --population 20 --days 7 --runs 3 --seed 42 --profile-source ncss --scenario lecture --event-day 1 --output-dir outputs_lecture_test
```

Small runs are useful for debugging, but they are not enough to make strong claims about intervention effects.

## 9. Notes

The NCSS-SRH profile sampler currently uses `91-王泽宇-2025.dta` by default. It samples real survey respondent rows and maps them into simulation profiles, which helps preserve empirical joint distributions among gender, age, sexual orientation, social activity, and risk-related behavior proxies.

Start with small population sizes because each agent may call DeepSeek several times per simulated day.

This folder is now intended to be run through `main_agentscope.py`. The older non-AgentScope entrypoint has been removed to avoid mixing two execution paths.

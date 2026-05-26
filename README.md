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

For intervention analysis, compare the following columns in `population_log.csv`:

- `Infected_Count`
- `Tested_Count`
- `Condom_Acts_Count`
- `Total_Sexual_Acts`
- `Condom_intentions_Count`

## 7. Notes

The NCSS-SRH profile sampler currently uses `91-王泽宇-2025.dta` by default. It samples real survey respondent rows and maps them into simulation profiles, which helps preserve empirical joint distributions among gender, age, sexual orientation, social activity, and risk-related behavior proxies.

Start with small population sizes because each agent may call DeepSeek several times per simulated day.

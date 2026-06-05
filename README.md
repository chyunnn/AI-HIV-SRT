# AgentScope HIV Social Simulation

This repository contains an AgentScope-based HIV social simulation. Student agents are initialized from the 2025 NCSS-SRH survey distribution, then use AgentScope + DeepSeek to make daily behavior decisions such as location choice, HIV testing, sexual activity, and condom use.

The current version is AgentScope-only. The old non-AgentScope entrypoint has been removed, and the student logic has been merged into a single agent file: `student_agentscope.py`.

## Project Structure

```text
main_agentscope.py       # Main CLI entrypoint
student_agentscope.py    # Student agent, AgentScope decisions, interaction, infection, health updates
agentscope_decision.py   # AgentScope/DeepSeek wrapper and JSON decision parsing
ncss_sampler.py          # NCSS-SRH 2025 survey-based profile sampling
model.py                 # Simulation loop and daily aggregate statistics
event.py                 # Scenario/event memory injection
logger.py                # CSV output writer
config.py                # Simulation parameters and environment-variable API keys
requirements.txt         # Python dependencies
```

Generated folders such as `outputs*/`, `__pycache__/`, and `.env` should not be committed.

## Data Requirement

The sampler expects the 2025 NCSS-SRH Stata file by default:

```text
../91-王泽宇-2025.dta
```

This means that if the repository folder is:

```text
C:\Users\cheny\OneDrive\Desktop\srt\1110
```

the data file should be placed at:

```text
C:\Users\cheny\OneDrive\Desktop\srt\91-王泽宇-2025.dta
```

You can also provide another path explicitly:

```powershell
python main_agentscope.py --profile-source ncss --profile-data "C:\path\to\91-王泽宇-2025.dta"
```

The raw `.dta` file is not required to be uploaded to GitHub unless the team explicitly decides to share data.

## Install Dependencies

Run in PowerShell:

```powershell
cd C:\Users\cheny\OneDrive\Desktop\srt\1110
python -m pip install -r requirements.txt
```

## Set Environment Variables

Do not hard-code API keys in Python files. Set the DeepSeek key in the current PowerShell session:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

The code reads the key from `DEEPSEEK_API_KEY`.

## Quick Checks

Check whether AgentScope and the entrypoint can be imported:

```powershell
python -c "import agentscope; import main_agentscope; print('AgentScope import ok')"
```

Check whether NCSS-SRH profile generation works:

```powershell
python -c "from utils import generate_student_profiles; print(generate_student_profiles(3, source='ncss'))"
```

If this prints three `Student` profiles, survey-based initialization is working.

## Profile Sampling Logic

The current sampler does not independently sample each variable. Instead, it samples complete respondent rows from `91-王泽宇-2025.dta` and maps each row into one simulated student profile.

This preserves empirical joint distributions among variables such as gender, age, sexual orientation, social activity, sexual behavior history, contraceptive behavior, and STI/HIV-related history.

Mapped variables include:

- `sex`: biological sex
- `age`: age
- `b1`: sexual orientation
- `b3`: current relationship status
- `b3_1`: whether the respondent wants a boyfriend/girlfriend
- `b3_5`: number of past romantic partners
- `b3_7_1`, `b3_7_2`: daily social/recreational time
- `a1_3_*`: school sex education format
- `a3_0_*`: sources of sexual and reproductive health knowledge
- `c2`: pornography exposure frequency
- `c5`: insertive sexual experience
- `c6`, `c6_1`, `c6_2_*`: casual sex / one-night stand / transactional sex experience
- `c11`: sexual activity frequency in the past year
- `c14_0_*`: most recent contraception/protection method
- `c14_1_*`: reasons for not using contraception
- `c15`: who usually decides contraception method
- `c20_0_*`: STI/HIV diagnosis history
- `c20_10`: HIV treatment after diagnosis

Some simulation variables are derived proxies:

- `social_activity`: derived mainly from `b3_7_1 + b3_7_2`
- `attractiveness`: currently used as a relationship-opportunity proxy, not literal physical attractiveness
- `risk_propensity`: derived from sexual experience, casual sex, contraception/protection behavior, sexual frequency, and pornography exposure
- `awareness`: a 0-1 HIV/SRH awareness score derived from sex education, knowledge sources, condom/protection behavior, and STI/HIV history

Initial `awareness` starts from `0.25` and is adjusted as follows:

- each selected school sex education format adds up to `0.08`, capped at three forms
- each selected knowledge source adds up to `0.06`, capped at five sources
- condom/protection use adds `0.12`
- STI/HIV diagnosis history adds `0.08`
- no contraception/protection use subtracts `0.12`
- not actively seeking knowledge subtracts `0.15`
- the final value is clipped to the `0-1` range

Intervention events can further increase `awareness`. Each exposed agent is assigned one of three attention levels:

- `完全没听`: multiplier `0.0`
- `听了一些`: multiplier `0.5`
- `很认真听`: multiplier `1.0`

The base event effects are:

- lecture/campaign health education: up to `+0.18`
- self-test machine information: up to `+0.12`
- police/legal warning: up to `+0.08`
- venue risk warning: up to `+0.06`

For example, a lecture gives `+0.00`, `+0.09`, or `+0.18` depending on whether the agent completely ignored it, listened partly, or listened carefully.

## Running a Small Test

Start with a very small run because each agent may call DeepSeek several times per simulated day:

```powershell
python main_agentscope.py --population 2 --days 1 --runs 1 --profile-source ncss --scenario none --output-dir outputs_test
```

If successful, the terminal will show a daily summary such as:

```text
Day 1: Infected = ...
```

The full reasoning and action process is saved in `decision_log.csv`.

## Running Baseline and Intervention Experiments

Baseline group:

```powershell
python main_agentscope.py --population 10 --days 5 --runs 1 --seed 42 --profile-source ncss --scenario none --output-dir outputs_baseline_seed42
```

Lecture intervention group:

```powershell
python main_agentscope.py --population 10 --days 5 --runs 1 --seed 42 --profile-source ncss --scenario lecture --event-day 1 --output-dir outputs_lecture_seed42
```

Campaign intervention group:

```powershell
python main_agentscope.py --population 10 --days 5 --runs 1 --seed 42 --profile-source ncss --scenario campaign --event-day 1 --output-dir outputs_campaign_seed42
```

Using the same seed makes the two runs easier to compare, but serious analysis should use multiple repetitions.

## Output Files

Each run creates a timestamped folder inside the selected output directory:

```text
outputs_lecture_seed42/
└── 20260605_200530_run_1/
    ├── population_log.csv
    ├── daily_agent_state.csv
    ├── infected_profiles.csv
    └── decision_log.csv
```

Main files:

- `population_log.csv`: daily aggregate outcomes
- `daily_agent_state.csv`: daily state of each agent
- `infected_profiles.csv`: newly infected agent profiles
- `decision_log.csv`: AgentScope/DeepSeek prompt, raw response, parsed action, and reflection

## Reading Results

Use `population_log.csv` for high-level outcomes:

- `Infected_Count`: total infected agents by day
- `Infected_Venue`: infections from venue exposure
- `Infected_Sex`: infections from unprotected sex
- `Tested_Count`: agents choosing HIV testing that day
- `Condom_Acts_Count`: sexual acts where condom use occurred
- `Total_Sexual_Acts`: sexual acts that actually occurred
- `Condom_intentions_Count`: agents expressing condom-use intention
- `Average_Awareness`: mean 0-1 awareness score across all agents

Use `daily_agent_state.csv` for individual trajectories:

- `Health_Condition`
- `Partners_Count`
- `Had_Sex_Today`
- `Used_Condom_Today`
- `Tested_Today`
- `Location`
- `Awareness`: the agent's current 0-1 awareness score

Use `decision_log.csv` to inspect the model reasoning process:

- `Decision_Type`: `location`, `hiv_test`, `sexual_activity`, or `condom_use`
- `Prompt`: prompt sent to DeepSeek
- `Raw_Response`: original model response
- `Reflection`: one-sentence reasoning before action
- `Parsed_Action`: action extracted by the simulation
- `Parse_OK`: whether JSON parsing succeeded
- `Recent_Memory`: agent memory used in the prompt
- `Metadata`: extra context such as partner ID

## Current Behavioral Assumptions

Sexual activity now requires mutual agreement:

```text
sex_happens = agent_A_agrees AND agent_B_agrees
```

Condom/protection use follows a protective rule:

```text
condom_used = agent_A_wants_condom OR agent_B_wants_condom
```

This means sexual activity only occurs if both agents agree, and protection is used if either agent requests it.

## Comparing Baseline and Intervention

Compare these columns in `population_log.csv`:

- `Infected_Count`
- `Tested_Count`
- `Condom_Acts_Count`
- `Total_Sexual_Acts`
- `Condom_intentions_Count`

Interpretation guide:

- Higher `Tested_Count` may indicate increased HIV testing willingness.
- Higher `Condom_Acts_Count` or `Condom_intentions_Count` may indicate improved protective behavior.
- Lower `Total_Sexual_Acts` may indicate fewer risky encounters.
- Lower `Infected_Count` across repeated runs may indicate reduced simulated infection risk.

Recommended repeated-run commands:

```powershell
python main_agentscope.py --population 20 --days 7 --runs 3 --seed 42 --profile-source ncss --scenario none --output-dir outputs_baseline_test
python main_agentscope.py --population 20 --days 7 --runs 3 --seed 42 --profile-source ncss --scenario lecture --event-day 1 --output-dir outputs_lecture_test
```

Small runs are useful for debugging, but they are not enough for strong claims about intervention effects.

## GitHub Upload Notes

Only upload source code and documentation. Do not upload generated simulation outputs.

Keep:

```text
.gitignore
README.md
requirements.txt
main_agentscope.py
student_agentscope.py
agentscope_decision.py
ncss_sampler.py
model.py
event.py
logger.py
utils.py
config.py
```

Do not upload:

```text
outputs*/
__pycache__/
*.pyc
.env
```

The `.gitignore` file should include:

```gitignore
__pycache__/
*.pyc
outputs*/
.env
```

Before pushing, check:

```powershell
git status --short
```

If old generated files were already tracked, remove them from Git tracking but keep them locally:

```powershell
git rm --cached -r outputs outputs_agentscope outputs_baseline_seed42 outputs_lecture_seed42
git rm --cached -r __pycache__
```

Then commit and push:

```powershell
git add .gitignore README.md requirements.txt main_agentscope.py student_agentscope.py agentscope_decision.py ncss_sampler.py model.py event.py logger.py utils.py config.py
git add -u
git commit -m "Update AgentScope simulation documentation"
git push origin main
```

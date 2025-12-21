# CARLA Simulator

CARLA 0.9.16
ScenarioRunner 0.9.16

https://carla.org/

## Set up CARLA and ScenarioRunner

Follow the installation of

CARLA 0.9.16
https://carla.readthedocs.io/en/0.9.16/

and

CARLA ScenarioRunner 0.9.16
https://scenario-runner.readthedocs.io/en/latest/

## Files

Save the file **Scenario.xml** in the path:
C:\path-to\scenario_runner-0.9.16\srunner\examples

Save the file **sensai_study_scenario.py** in the path:
C:\path-to\scenaio_runner-0.9.16\srunner\scenarios

## Run

### Terminal 1

```
cd
C:\path-to\CARLA_0.9.16
```

#### Windows:

```
.\CarlaUE4.exe --sync --output
```

#### Linux:

```
.\CarlaUE4.sh --sync --output
```

### Terminal 2

```
cd
C:\path-to\scenario_runner-0.9.16

python3 scenario_runner.py --scenario ScenarioName_SensAiStudy --reloadWorld --sync --frameRate 40 --output
```

If an error occurs, the following must be set manually:

> $env:PYTHONPATH="C:\path-to\CARLA_0.9.16\PythonAPI\carla"

### Terminal 3

```
cd
C:\path-to\scenario_runner-0.9.16

python3 .\manual_control.py

optional --res 3840x1080

```

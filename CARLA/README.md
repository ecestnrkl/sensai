# CARLA Simulator

CARLA 0.9.16
ScenarioRunner 0.9.16

https://carla.org/

## Desription

A controlled driving simulation was created using CARLA Simulator (v0.9.16) in combination with ScenarioRunner (v0.9.16) in Town03, allowing participants to navigate an urban environment. The participants controlled the ego vehicle using a Logitech steering wheel and pedal set, enabling acceleration, braking, steering, and forward/reverse driving.
To induce stress, non-player vehicles in autopilot mode and stationary roadblocks were used to create traffic congestion and time pressure. Blocking vehicles resumed movement as participants approach the area, causing the traffic jam to gradually clear.

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

> Execute only once Terminal 2 (scenario) is done!

```
cd
C:\path-to\scenario_runner-0.9.16

python3 .\manual_control.py

optional --res 3840x1080

```

> May need to be commented out, as shown (as problems may arise when using the steering wheel). (approx. 2 times in code):

```
elif event.key == K_c:
    world.next_weather()
```

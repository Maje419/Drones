# VeLOS
This the the source code for VeLOS, a project that allows drones to autonomously check if a given point would provide line of sight to existing masts, if a new mast placed at that point.

## How to run
You will need two (required) or three (optional) terminal windows to start the drone.


### Setting up the environment
You will need to change the `PX4_HOME_LAT` and `PX4_HOME_LON` environment variables to your desired location, before running `VeLOS` with that location. Otherwise the drone will not be taking off from the location that it calculated distances from, and LoS will not be able to be confirmed.

### Terminal 1 - `PX4`
Make sure to source the `setup.env` file before running the make command. 

Assuming you are in the directory with `PX4` installed, you need to run the command `make px4_sitl gazebo_typhoon_h480__mcmillan_airfield`

Note that `__mcmillan_airfield` is optional, but it provides a more realistic environment with hills/mountains.

### Terminal 2 - `QGroundControl` (Optional)
Run the `QGroundControl.AppImage` file

### Terminal 3 - `VeLOS`
Run `python run_mission.py --lon <LONGITUDE> --lat <LATITUDE>` to start the mission. You should be able to see the drone taking off in the Gazebo window shortly.

If you don't specify any parameters to `run_mission.py`, it will use the default coordinates (that matches the default coordinates from setup.env), as specified in the help command:
```bash
$ python3 run_mission.py --help
usage: run_mission.py [-h] [--lon LONGITUDE] [--lat LATITUDE]

Automatic Drone Mast LoS confirmation tool. Default location is somewhere in Langeskov (i.e., Lars Tyndskids mark)

optional arguments:
  -h, --help       show this help message and exit
  --lon LONGITUDE  The longitude coordinate, default=10.573138
  --lat LATITUDE   The latitude coordinate, default=55.369671
  ```
  
  In the terminal running `run_mission.py` info messages are regularly printed. If more verbose logging is needed, debug logs are also stored in the `/logs` directory.

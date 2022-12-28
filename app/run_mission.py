import asyncio
from typing import List, Tuple
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan

from mast_calculations import get_closest_masts

MAST_HEIGHT = 30 #meters relative to starting position of drone

async def run(entry_point: Tuple[float, float]):
    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"-- Connected to drone!")
            break

    print_mission_progress_task = asyncio.ensure_future(print_mission_progress(drone))

    closest_masts = get_closest_masts(entry_point)  #Should be received from the base-station in real setup

    await drone.param.set_param_float("MIS_DIST_1WP", 5000)
    await drone.param.set_param_float("MIS_DIST_WPS", 5000)

    mission_items = []
    for (mast, distance) in closest_masts:
        mission_items.append(
            MissionItem(
                float(mast["wgs84koordinat"]["bredde"]),
                float(mast["wgs84koordinat"]["laengde"]),
                MAST_HEIGHT,
                5,
                False,
                float("nan"),
                float("nan"),
                MissionItem.CameraAction.NONE,
                float("nan"),
                float("nan"),
                float("nan"),
                float("nan"),
                float("nan"),
            )
        )
        
    has_found_mast = False
    i = 0
    await drone.mission.set_return_to_launch_after_mission(False)
    while not has_found_mast and i < 3:
        mission_plan = MissionPlan([mission_items[i]])
        print(f"-- Uploading mission {i}")
        await drone.mission.upload_mission(mission_plan)

        print("Waiting for drone to have a global position estimate...")
        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position estimate OK")
                break

        print("-- Arming")
        await drone.action.arm()

        print("-- Starting mission")
        await drone.mission.start_mission()

        print(f"-- Now checking mast {closest_masts[i][0]['unik_station_navn']} at {closest_masts[i][0]['wgs84koordinat']['laengde']}, {closest_masts[i][0]['wgs84koordinat']['bredde']}")
        j = 0
        has_obstacle = False
        while not has_found_mast and not has_obstacle:
            j += 1
            await asyncio.sleep(1)
            if j > 45:
                has_obstacle = True
            if has_obstacle:
                print("-- Obstacle found")
                await drone.mission.pause_mission()
                await drone.mission.clear_mission()
            else:
                has_obstacle = False    ##Update on camera input

        print("-- Returning to base")
        await drone.mission.clear_mission()
        await drone.mission.upload_mission(MissionPlan([MissionItem(
                float(entry_point[1]),
                float(entry_point[0]),
                MAST_HEIGHT,
                5,
                False,
                float("nan"),
                float("nan"),
                MissionItem.CameraAction.NONE,
                float("nan"),
                float("nan"),
                float("nan"),
                float("nan"),
                float("nan"),
            )]))
        await drone.mission.start_mission()
        is_finished = False
        while not is_finished:
            is_finished = await drone.mission.is_mission_finished()
            await asyncio.sleep(1)
        i += 1
        print(f"-- Mission finished. Line of sight confirmed to mast: {has_found_mast}")

async def print_mission_progress(drone):
    async for mission_progress in drone.mission.mission_progress():
        print(
            f"Mission progress: "
            f"{mission_progress.current}/"
            f"{mission_progress.total}"
        )


async def observe_is_in_air(drone, running_tasks):
    """Monitors whether the drone is flying or not and
    returns after landing"""

    was_in_air = False

    async for is_in_air in drone.telemetry.in_air():
        if is_in_air:
            was_in_air = is_in_air

        if was_in_air and not is_in_air:
            for task in running_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await asyncio.get_event_loop().shutdown_asyncgens()

            return

def start():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run((10.573138, 55.369671)))


if __name__ == "__main__":
    start()

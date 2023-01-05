import asyncio
from typing import List, Tuple
import threading
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mast_calculations import get_closest_masts
from Video import Video
from keras.applications.vgg16 import VGG16, preprocess_input, decode_predictions
from keras.utils.image_utils import img_to_array, load_img
import time

# Image stuff
from PIL import Image

MAST_HEIGHT = 30  # Relative height of old mast to starting position of drone (meters)
ACCEPTANCE_RADIUS = 5  # How close should the drone be to the mast before the mission is a success (meters)

video = Video()

time_start = time.time()

model = VGG16()

# Initialize thread-safe variables
obstacle_avoidance_triggered = threading.Event()
has_found_mast = threading.Event()
is_returning = threading.Event()


async def run(entry_point: Tuple[float, float]):
    drone = System()

    closest_masts = get_closest_masts(
        entry_point
    )  # Should be received from the base-station in real setup
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"-- Connected to drone!")
            break

    print("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position estimate OK")
            break

    # Configure the drone parameters
    await drone.param.set_param_float("MIS_DIST_1WP", 5000)
    await drone.param.set_param_float("MIS_DIST_WPS", 5000)
    await drone.mission.set_return_to_launch_after_mission(False)

    print("-- Arming")
    await drone.action.arm()

    # Start parallel tasks
    monitor_distance_task = asyncio.ensure_future(monitor_distance(drone))
    print_mission_progress_task = asyncio.ensure_future(print_mission_progress(drone))
    do_mast_recognition_task = asyncio.ensure_future(do_mast_recognition())

    running_tasks = [
        monitor_distance_task,
        print_mission_progress_task,
        do_mast_recognition_task,
    ]

    mission_items = []
    for (mast, distance) in closest_masts:
        mission_items.append(
            MissionItem(
                latitude_deg=float(mast["wgs84koordinat"]["bredde"]),
                longitude_deg=float(mast["wgs84koordinat"]["laengde"]),
                relative_altitude_m=MAST_HEIGHT,
                speed_m_s=5,
                is_fly_through=False,
                gimbal_pitch_deg=float("nan"),
                gimbal_yaw_deg=float("nan"),
                camera_action=MissionItem.CameraAction.NONE,
                loiter_time_s=float("nan"),
                camera_photo_interval_s=float("nan"),
                acceptance_radius_m=ACCEPTANCE_RADIUS,
                yaw_deg=float("nan"),
                camera_photo_distance_m=float("nan"),
            )
        )

    i = 0
    while not has_found_mast.is_set() and i < 3:
        mission_plan = MissionPlan([mission_items[i]])

        print(f"-- Uploading mission {i}")
        await drone.mission.upload_mission(mission_plan)

        await asyncio.sleep(1)

        print("-- Starting mission")
        await drone.mission.start_mission()

        print(
            f"-- Now checking mast {closest_masts[i][0]['unik_station_navn']} at {closest_masts[i][0]['wgs84koordinat']['laengde']}, {closest_masts[i][0]['wgs84koordinat']['bredde']}"
        )

        while not has_found_mast.is_set() and not obstacle_avoidance_triggered.is_set():
            await asyncio.sleep(1)

        if obstacle_avoidance_triggered.is_set():
            print("-- Clearing current mission")
            await drone.mission.pause_mission()
            await drone.mission.clear_mission()

        print("-- Returning to base")
        is_returning.set()
        obstacle_avoidance_triggered.clear()
        await drone.mission.clear_mission()
        await drone.mission.upload_mission(
            MissionPlan(
                [
                    MissionItem(
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
                    )
                ]
            )
        )
        await asyncio.sleep(1)
        await drone.mission.start_mission()
        is_finished = False
        while not is_finished:
            is_finished = await drone.mission.is_mission_finished()
            await asyncio.sleep(1)
        i += 1
        print(
            f"-- Mission finished. Line of sight confirmed to mast: {has_found_mast.is_set()}"
        )
        is_returning.clear()


async def monitor_distance(drone: System):
    async for distance in drone.telemetry.distance_sensor():
        # print(distance)
        if (
            distance.current_distance_m < 250
            and not await drone.mission.is_mission_finished()
        ):
            obstacle_avoidance_triggered.set()
            print(f"Obstacle identified, line of sight cannot be confirmed.")


async def do_mast_recognition():
    i = 0  # TODO: Remove i, as we only need one (1) image at a time
    print("Mast recognition called")
    print("Has Found Mast: " + str(has_found_mast.is_set()))
    while not has_found_mast.is_set():
        print("Enter has_found loop")
        if not is_returning.is_set():
            # Capture image every 5 seconds to analyze
            print("-- Taking image")
            img = None
            while img is None:
                # Wait for the next frame
                if not video.frame_available():
                    continue

                img = video.frame()
            print("-- Took image")
            im = Image.fromarray(img[:, :, ::-1])
            im = im.resize((224, 224))
            im.save(f"images/second_{i}.jpeg")
            if image_contains_mast(img_to_array(im)):
                has_found_mast.set()
                print("Mast found! Returning to base.")
            print("Did mast check")
            await asyncio.sleep(5)
            i += 1
    print("Exiting mast recognition task")


def image_contains_mast(im):
    print("-- image_contains_mast called")
    image = im.reshape((1, im.shape[0], im.shape[1], im.shape[2]))
    print("1")
    image = preprocess_input(image)
    print("2")
    pred = model.predict(image)
    print("3")
    label = decode_predictions(pred)
    print("4")
    label = label[0][0]
    print(
        " -- image_contains_mast returned "
        + str(label[1] == "balloon" and label[2] >= 0.90)
    )
    return label[1] == "balloon" and label[2] >= 0.90


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
    loop = asyncio.get_event_loop().run_until_complete(run((10.573138, 55.369671)))


if __name__ == "__main__":
    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    start()

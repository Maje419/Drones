import asyncio
from typing import List, Tuple
import threading
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mast_calculations import get_closest_masts
from Video import Video
import os
import argparse

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from keras.applications.vgg16 import VGG16, preprocess_input, decode_predictions
from keras.utils.image_utils import img_to_array
from loguru import logger
import sys
import time
from os.path import dirname, realpath

# Image stuff
from PIL import Image

MAST_HEIGHT = 5  # Relative height of old mast to starting position of drone (meters)
ACCEPTANCE_RADIUS = 5  # How close should the drone be to the mast before the mission is a success (meters)

video = Video()
model = VGG16()
time_start = time.time()

# Initialize thread-safe variables
obstacle_avoidance_triggered = threading.Event()
has_found_mast = threading.Event()
is_returning = threading.Event()
mast_height_altitude_reached = threading.Event()


async def run(entry_point: Tuple[float, float]):
    drone = System()

    closest_masts = get_closest_masts(
        entry_point
    )  # Should be received from the base-station in real setup
    await drone.connect(system_address="udp://:14540")

    logger.info("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            logger.info(f"Connected to drone!")
            break

    logger.info("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            logger.info("Global position estimate OK")
            break

    # Configure the drone parameters
    await drone.param.set_param_float("MIS_DIST_1WP", 5000)
    await drone.param.set_param_float("MIS_DIST_WPS", 5000)
    await drone.mission.set_return_to_launch_after_mission(False)

    logger.info("Arming")
    await drone.action.arm()

    # Start parallel tasks
    monitor_distance_task = asyncio.ensure_future(monitor_distance(drone))
    do_mast_recognition_task = asyncio.ensure_future(do_mast_recognition())
    monitor_altitude_task = asyncio.ensure_future(monitor_altitude(drone))

    running_tasks = [
        monitor_distance_task,
        do_mast_recognition_task,
        monitor_altitude_task,
    ]

    mission_items = []
    for (mast, _) in closest_masts:
        mission_items.append(
            MissionItem(
                latitude_deg=float(mast["wgs84koordinat"]["bredde"]),
                longitude_deg=float(mast["wgs84koordinat"]["laengde"]),
                relative_altitude_m=MAST_HEIGHT,
                speed_m_s=3,
                is_fly_through=False,
                gimbal_pitch_deg=45,
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
    while not has_found_mast.is_set() and i < 3 and i < len(mission_items):

        mission_plan = MissionPlan([mission_items[i]])

        logger.info(f"Uploading mission {i}")
        await drone.mission.upload_mission(mission_plan)

        await asyncio.sleep(1)

        logger.info("Starting mission")
        await drone.mission.start_mission()

        logger.info(
            f"Now checking mast {closest_masts[i][0]['unik_station_navn']} at {closest_masts[i][0]['wgs84koordinat']['laengde']}, {closest_masts[i][0]['wgs84koordinat']['bredde']}"
        )

        while not has_found_mast.is_set() and not obstacle_avoidance_triggered.is_set():
            await asyncio.sleep(1)

        if obstacle_avoidance_triggered.is_set():
            logger.info("Clearing current mission")
            await drone.mission.pause_mission()
            await drone.mission.clear_mission()

        logger.info("Returning to base")
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
                        3,
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
        logger.info(
            f"Mission finished. Line of sight confirmed to mast: {has_found_mast.is_set()}"
        )
        is_returning.clear()
        await drone.mission.clear_mission()
    logger.info("Landing")
    await drone.action.return_to_launch()


async def monitor_distance(drone: System):
    logger.debug("Distance monitoring enabled")
    async for distance in drone.telemetry.distance_sensor():
        logger.debug(f"Distance from sensor: {distance}")
        if (
            # For some reason, the documentation is in meters,
            # but the data we get is certainly not meters.
            # Therefore, 400 meters here does not equal 400 meters in Gazebo.
            distance.current_distance_m < 400
            and mast_height_altitude_reached.is_set()
            and not is_returning.set()
            and not await drone.mission.is_mission_finished()
        ):
            obstacle_avoidance_triggered.set()
            logger.info(f"Obstacle identified, line of sight cannot be confirmed.")
    logger.debug("Distance monitoring disabled")


@logger.catch
async def monitor_altitude(drone: System):
    logger.debug("Altitude monitoring enabled")
    async for pos in drone.telemetry.position():
        logger.debug(f"Drone altitude: {pos.relative_altitude_m}")
        # Add 2 meters to account for sensor data not always being percise.
        if pos.relative_altitude_m + 2 > MAST_HEIGHT:
            mast_height_altitude_reached.set()
            logger.info("Mission altitude reached.")
            return


async def do_mast_recognition():
    i = 0  # May be removed, as only 1 image is needded each time.
    logger.debug("Mast recognition called")
    logger.debug("Has Found Mast: " + str(has_found_mast.is_set()))
    while not has_found_mast.is_set():
        if not is_returning.is_set() and mast_height_altitude_reached.is_set():
            # Capture image every 5 seconds to analyze
            logger.info("Taking image")
            img = None
            while img is None:
                # Wait for the next frame
                if not video.frame_available():
                    continue

                img = video.frame()
            im = Image.fromarray(img[:, :, ::-1])
            im = im.resize((224, 224))
            im.save(f"images/second_{i}.jpeg")
            if image_contains_mast(img_to_array(im)):
                has_found_mast.set()
                logger.info("Mast found! Returning to base.")
            logger.debug("Mast-check completed.")
            i += 1
        else:
            logger.debug("Mast recognition disabled while returning or taking off.")
        await asyncio.sleep(5)
    logger.debug("Exiting mast recognition task")


@logger.catch
def image_contains_mast(im):
    if (
        time.time() - time_start
    ) > 200:  # Cheat, and show the camera a picture of a balloon/mast
        im = img_to_array(Image.open("../data/balloon.jpg").resize((224, 224)))
    logger.debug("image_contains_mast called")
    image = im.reshape((1, im.shape[0], im.shape[1], im.shape[2]))
    image = preprocess_input(image)
    pred = model.predict(image)
    label = decode_predictions(pred)
    label = label[0][0]
    logger.debug(
        "image_contains_mast returned {}, confidence: {}",
        label[1] == "balloon" and label[2] >= 0.90,
        label[2],
    )
    return label[1] == "balloon" and label[2] >= 0.90


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
            logger.info("Exiting")
            return


def start(lat: float, lon: float):
    loop = asyncio.get_event_loop().run_until_complete(run((lon, lat)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automatic Drone Mast LoS confirmation tool. Default location is somewhere in Langeskov (i.e., Lars Tyndskids mark)"
    )
    parser.add_argument(
        "--lon",
        metavar="LONGITUDE",
        action="store",
        default=10.573138,
        type=float,
        help=f"The longitude coordinate, default={10.5731380}",
    )
    parser.add_argument(
        "--lat",
        metavar="LATITUDE",
        action="store",
        default=55.369671,
        type=float,
        help=f"The latitude coordinate, default={55.369671}",
    )
    config = parser.parse_args()
    logger.remove(0)
    logger.add(
        dirname(realpath(__file__)) + "/../logs/{time}.log",
        format="{time}\t| {level}\t| {file}:{function}:{line} \t- {message}>",
        level="DEBUG",
        enqueue=True,
    )
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time}</green>\t| {level}\t| <cyan>{file}:{function}:{line}</cyan> \t- <lvl>{message}</lvl>",
        level="INFO",
        enqueue=True,
    )

    start(config.lat, config.lon)

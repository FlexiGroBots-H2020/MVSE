import asyncio
from mavsdk import System
from mavsdk.geofence import Point, Polygon


async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")
    print("waiting for drone")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"Drone discovered!")
            break
    
    async for terrain_info in drone.telemetry.home():
        latitude = terrain_info.latitude_deg
        longitude = terrain_info.longitude_deg
        break

    await asyncio.sleep(1)
    p1 = Point(latitude - 0.0005, longitude - 0.0005)
    p2 = Point(latitude + 0.0005, longitude - 0.0005)
    p3 = Point(latitude + 0.0005, longitude + 0.0005)
    p4 = Point(latitude - 0.0005, longitude + 0.0005)

    # Create a polygon object using your points
    polygon = Polygon([p1, p2, p3, p4], Polygon.FenceType.INCLUSION)

    # Upload the geofence to your vehicle
    print("Uploading geofence...")
    await drone.geofence.upload_geofence([polygon])
    #await drone.geofence.clear_geofence()
    print("Geofence uploaded!")
        

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
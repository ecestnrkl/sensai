import random
import py_trees
import carla


from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.scenarioatomics.atomic_behaviors import (
    WaitForever,
    WaypointFollower,
    ChangeAutoPilot,
)
from srunner.scenariomanager.scenarioatomics.atomic_criteria import CollisionTest

from agents.navigation.local_planner import RoadOption

FORBIDDEN_ROADS = {
    19: None,
    24: [-1],
    30: None,
    8: [-1],
    28: None,
    7: [4, 5],
    69: None,
    1030: None,
}  # road_id :[lane_ids]


class SensAiStudyScenario(BasicScenario):

    timeout = 600  # Maximum runtime of the scenario in seconds

    def __init__(
        self,
        world,
        ego_vehicles,
        config,
        randomize=False,
        debug_mode=False,
        criteria_enable=True,
    ):
        self.world = world
        self.client = CarlaDataProvider.get_client()
        self.tm = self.client.get_trafficmanager()
        self.map = CarlaDataProvider.get_map()

        self.npc_actors = []  # List for saving spawned NPCs

        # 1. Blueprints prepare
        self.blueprint_library = CarlaDataProvider.get_world().get_blueprint_library()
        self.vehicle_blueprints = [
            bp
            for bp in self.blueprint_library.filter("vehicle.*")
            if bp.has_attribute("number_of_wheels")
            and bp.get_attribute("number_of_wheels").as_int() == 4
        ]

        # 2. Performance and Traffic Manager settings
        self._setup_traffic_manager()

        # 3. Initialisation of the base class
        super(SensAiStudyScenario, self).__init__(
            "SensAiStudyScenario",
            ego_vehicles,
            config,
            world,
            debug_mode,
            criteria_enable=criteria_enable,
        )

    # Setup traffic manager
    def _setup_traffic_manager(self):
        print(f"World Settings {self.world.get_settings()}")

        self.tm.set_hybrid_physics_mode(True)
        self.tm.set_hybrid_physics_radius(400.0)

    def _initialize_actors(self, config):
        # self.show_debug_draw_spawn_points()
        # self.show_debug_road_ids(10.0)  # Red

        self.spawn_static_props()
        self.set_all_vehicles_along_path()
        # self.spawn_autopilot_vehicles_on_waypoints()

        # Spawn ego vehicles and XML-defined actors
        # super(SensAiStudyScenario, self)._initialize_actors(config)

    def set_all_vehicles_along_path(self):
        for i in range(4):
            self.vehicle_along_path(
                f"Vehicles {i} from accident crossing",
                83,
                [89, 88, 175, 201, 87, 253],
                i,
                random.randint(0, 30),
            )
            self.vehicle_along_path(
                f"Vehicles {i} really slow",
                70,
                [133, 126, 61, 254, 90, 77, 190, 98, 261],
                i,
                random.randint(50, 70),
            )

        for i in range(8):
            self.vehicle_along_path(
                f"Vehicles {i} from roundabout",
                112,
                [
                    210,
                    246,
                    243,
                    244,
                    148,
                    17,
                    191,
                    83,
                    225,
                    171,
                    204,
                    162,
                    113,
                    245,
                    136,
                    85,
                    261,
                    57,
                    263,
                    55,
                    86,
                    32,
                ],
                i,
                30,
            )

        for i in range(8):
            self.vehicle_along_path(
                f"Vehicles {i} from petrolstation",
                197,
                [4, 45, 227, 199, 142, 138, 97, 131, 242, 150, 111, 208, 149, 121],
                i,
                random.randint(-10, 30),
            )
            self.vehicle_along_path(
                f"Vehicles {i} from tunnel",
                141,
                [223, 226],
                i,
                random.randint(-10, 30),
            )
            self.vehicle_along_path(
                f"Vehicles {i} from roundabout-skyscraper",
                218,
                [232, 234, 147, 21],
                i,
                random.randint(-10, 30),
            )

        for i in range(10):
            # SpawnPoints
            self.vehicle_along_path(
                f"Vehicles {i} at city",
                38,
                [165, 155, 190, 261, 127, 49, 129, 123, 232],
                i,
                random.randint(0, 50),
            )

            self.vehicle_along_path(
                f"Vehicles {i} at top-right",
                200,
                [
                    128,
                    134,
                    72,
                    135,
                    153,
                    217,
                    235,
                    184,
                    105,
                    145,
                    209,
                    151,
                    237,
                    238,
                    133,
                    264,
                    60,
                    257,
                    226,
                    232,
                    245,
                    136,
                    85,
                    261,
                ],
                i,
                random.randint(0, 50),
            )
            self.vehicle_along_path(
                f"Vehicles {i} at petrolstation to home",
                69,
                [164],
                i,
                random.randint(0, 40),
            )

        for i in range(12):
            self.vehicle_along_path(
                f"Vehicles {i} from near start street",
                164,
                [253, 226, 172, 206, 164, 253, 226, 172, 206, 245, 136, 228],
                i,
                random.randint(10, 40),
            )

        print(f"{len(self.other_actors)} Vehicles on street/ spawned")

    def spawn_static_props(self):
        staticProps = [
            # Destination 1
            {"name": "static.prop.foodcart", "x": -112, "y": -106, "z": 0.2, "yaw": 90},
            {"name": "static.prop.table", "x": -114, "y": -104, "z": 0.2, "yaw": 40},
            {"name": "static.prop.gnome", "x": -114, "y": -104, "z": 1.2, "yaw": 320},
            # Destination 2
            {
                "name": "static.prop.plastictable",
                "x": -55,
                "y": 153,
                "z": 0.2,
                "yaw": 320,
            },
            {"name": "static.prop.barbeque", "x": -56, "y": 152, "z": 0.2, "yaw": 320},
            {
                "name": "static.prop.shoppingcart",
                "x": -53,
                "y": 152,
                "z": 1.2,
                "yaw": 320,
            },
            # Construction site
            {"name": "static.prop.streetbarrier", "x": 60, "y": 127, "yaw": 90},
            {"name": "static.prop.streetbarrier", "x": 60, "y": 129, "yaw": 90},
            {"name": "static.prop.streetbarrier", "x": 59, "y": 130.5, "yaw": 145},
            {"name": "static.prop.streetbarrier", "x": 56.5, "y": 130.5, "yaw": 235},
            {
                "name": "static.prop.dirtdebris01",
                "x": 58,
                "y": 129,
                "z": 0.1,
                "yaw": 90,
            },
            {
                "name": "walker.pedestrian.0030",
                "x": 60.5,
                "y": 129.5,
                "z": 0.1,
                "yaw": 90,
            },
            {
                "name": "static.prop.warningconstruction",
                "x": 75,
                "y": 127,
                "z": 0.01,
                "yaw": 270,
            },
            # Highway crash
            {
                "name": "vehicle.mini.cooper_s_2021",
                "x": 211,
                "y": -6,
                "z": 1.8,
                "yaw": 305,
                "roll": 180,
            },
            {
                "name": "vehicle.toyota.prius",
                "x": 213.5,
                "y": 1.2,
                "z": 0.2,
                "yaw": 20,
            },
            {
                "name": "vehicle.dodge.charger_police_2020",
                "x": 200,
                "y": -5,
                "z": 0.1,
                "yaw": 65,
            },
            {
                "name": "vehicle.dodge.charger_police_2020",
                "x": 223,
                "y": -1,
                "z": 0.1,
                "yaw": 65,
            },
            {
                "name": "vehicle.dodge.charger_police_2020",
                "x": 225,
                "y": -8,
                "z": 0.1,
                "yaw": 140,
            },
            # Roadblock Firetruck
            {
                "name": "static.prop.trafficwarning",
                "x": -15.5,
                "y": -143,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -15.5,
                "y": -140,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -15.5,
                "y": -138,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -15.5,
                "y": -136,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -15.5,
                "y": -134,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -15.5,
                "y": -132,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -50,
                "y": -140,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -50,
                "y": -138,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -50,
                "y": -136,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -50,
                "y": -134,
                "yaw": 90,
            },
            {
                "name": "static.prop.streetbarrier",
                "x": -50,
                "y": -143,
                "yaw": 90,
            },
            {
                "name": "static.prop.trafficwarning",
                "x": -49,
                "y": -132,
                "yaw": 270,
            },
            {
                "name": "vehicle.dodge.charger_police_2020",
                "x": -52,
                "y": -133,
                "z": 0.1,
                "yaw": 90,
            },
            {
                "name": "vehicle.dodge.charger_police_2020",
                "x": -13,
                "y": -140,
                "z": 0.1,
                "yaw": 90,
            },
            {"name": "walker.pedestrian.0030", "x": -16, "y": -133, "z": 0.1, "yaw": 0},
            {"name": "walker.pedestrian.0030", "x": -16, "y": -136, "z": 0.1, "yaw": 0},
            {
                "name": "walker.pedestrian.0030",
                "x": -50,
                "y": -142,
                "z": 0.1,
                "yaw": 180,
            },
            {
                "name": "walker.pedestrian.0032",
                "x": -50,
                "y": -140,
                "z": 0.1,
                "yaw": 210,
            },
            {
                "name": "vehicle.carlamotors.firetruck",
                "x": -30,
                "y": -135,
                "z": 0.1,
                "yaw": 220,
            },
            # Ambulance blocking road
            {"name": "walker.pedestrian.0030", "x": 55, "y": 188, "z": 0.8, "yaw": 25},
            {
                "name": "static.prop.warningaccident",
                "x": 65,
                "y": 190,
                "z": 0.5,
                "yaw": 270,
            },
        ]

        spawned = []  # so that we can delete all later

        for prop in staticProps:
            print(f"Spawning {prop['name']}...")

            transform = carla.Transform(
                carla.Location(x=prop["x"], y=prop["y"], z=prop.get("z", 0)),
                carla.Rotation(yaw=prop.get("yaw", 0), roll=prop.get("roll", 0)),
            )

            blueprint = self.blueprint_library.find(f"{prop['name']}")

            actor = self.world.try_spawn_actor(blueprint, transform)
            if actor is None:
                print(f"FAILED: Could not spawn {prop['name']} (collision?)")
                continue

            actor.set_simulate_physics(False)

            if actor.attributes.get("special_type") == "emergency":
                actor.set_light_state(carla.VehicleLightState.All)

            # Spawned.append(actor)
            self.other_actors.append(actor)

            print(f"[StaticProp] Spawned {prop['name']}")

    def vehicle_along_path(
        self,
        name: str,
        startSpawnPoint: int,  # Must be a spawnpoint
        routePoints: list[int],  # Spawnpoints
        multiplier: int | None,
        speed_diffrence=30,
    ):
        spawn_points = self.map.get_spawn_points()
        spawn_point_start = spawn_points[startSpawnPoint]
        wp = self.map.get_waypoint(spawn_points[startSpawnPoint].location)
        if multiplier is not None:
            # Previous(distance)
            point_start = wp.previous(6 * (multiplier + 1))[0].transform
        else:
            point_start = spawn_point_start

        route_indices = routePoints
        route = []
        for ind in route_indices:
            route.append(spawn_points[ind].location)

        random_r = random.choice([0, 125, 255])
        random_g = random.choice([0, 125, 255])
        random_b = random.choice([0, 125])

        # Debug

        # self.world.debug.draw_string(
        #     point_start.location,
        #     "SP 1",
        #     False,
        #     carla.Color(random_r, random_g, random_b),
        #     20000.0,
        # )
        # for ind in route_indices:
        #     start_pos = spawn_points[ind].location
        #     text = ind

        #     self.world.debug.draw_string(
        #         start_pos,
        #         str(text),
        #         False,
        #         carla.Color(random_r, random_g, random_b),
        #         20000.0,
        #     )

        # self.world.debug.draw_line(
        #     begin=point_start.location,
        #     end=route[0],
        #     thickness=0.5,
        #     color=carla.Color(random_r, random_g, random_b),
        #     life_time=20000.0,
        # )
        # for i in range(len(route) - 1):
        #     self.world.debug.draw_line(
        #         begin=route[i],
        #         end=route[i + 1],
        #         thickness=0.5,
        #         color=carla.Color(random_r, random_g, random_b),
        #         life_time=20000.0,
        #     )

        actor = CarlaDataProvider.request_new_actor(
            random.choice(self.vehicle_blueprints).id, point_start
        )

        if actor is not None:
            actor.set_autopilot(True, self.tm.get_port())
            self.tm.set_path(actor, route)
            self.tm.vehicle_percentage_speed_difference(actor, speed_diffrence)
            self.tm.update_vehicle_lights(actor, True)
            self.other_actors.append(actor)
            print(f"Success spawned{name}")

    def show_debug_road_ids(self, distance: float):
        waypoints = self.map.generate_waypoints(distance)

        road_ids = []
        wp_for_road = []

        # Collect all RoadIDs individually + save sample waypoints
        for wp in waypoints:
            # if wp.road_id not in road_ids:
            road_ids.append(wp.road_id)
            wp_for_road.append(wp)

        # Sort RoadIDs
        road_ids.sort()

        # Display (Debug) each waypoint
        for wp in wp_for_road:
            self.world.debug.draw_string(
                wp.transform.location,
                str(f"\nRoad_ID: {wp.road_id}\nLANE_ID: {wp.lane_id}"),
                False,
                carla.Color(255, 0, 0),
                20000.0,
                True,
            )

    def show_debug_draw_spawn_points(self):
        spawn_points = self.map.get_spawn_points()

        for i, spawn_point in enumerate(spawn_points):
            self.world.debug.draw_string(
                spawn_point.location,
                str(i),
                False,
                carla.Color(255, 255, 255),
                20000.0,
                True,
            )

    def spawn_autopilot_vehicles_on_waypoints(self):
        waypoints = self.map.generate_waypoints(50)

        print(f"Got {len(waypoints)} waypoints")

        max_vehicles = 300
        max_vehicles = min([max_vehicles, len(waypoints)])
        vehicles = []

        for vehicle in range(max_vehicles):
            random_wp = random.choice(waypoints)

            wp = self.map.get_waypoint(
                random_wp.transform.location,
                project_to_road=True,
                lane_type=carla.LaneType.Driving,
            )
            new_wp = carla.Transform(
                wp.transform.location, random_wp.transform.rotation
            )
            actor = CarlaDataProvider.request_new_actor(
                random.choice(self.vehicle_blueprints).id,
                new_wp,
            )
            if actor is not None:
                actor.set_light_state(carla.VehicleLightState.All)
                actor.set_autopilot(True, self.tm.get_port())
                vehicles.append(actor)

        print(f"[AutopilotVehicles] {len(vehicles)} spawned")

        # Debug
        # for i, wp in enumerate(waypoints):
        #     self.world.debug.draw_string(
        #         wp.transform.location,
        #         str(f"wp: {i}\n{wp.transform.location}"),
        #         False,
        #         carla.Color(255, 255, 255),
        #         20000.0,
        #         True,
        #     )

    def spawn_vehicle(self, name, model, start_transform):
        vehicle = CarlaDataProvider.request_new_actor(model, start_transform)

        if vehicle is None:
            print("Vehicle: {name} could not spawn. Collision?")

        if vehicle is not None:
            vehicle.set_light_state(carla.VehicleLightState.All)
            print(f"Vehicle: {name} successfully requested.")
            return vehicle

    # Not used
    def spawn_vehicles_with_autopilot(self, maxVehicles):
        waypoints = self.map.generate_waypoints(100)
        vehicles = []

        for i in range(maxVehicles):
            vehicle = self.spawn_vehicle(
                f"Vehicle {i} in autopilot",
                random.choice(self.vehicle_blueprints).id,
                random.choice(waypoints).transform,
            )

            if vehicle is not None:
                # vehicle.set_autopilot(True)
                vehicles.append(vehicle)

        return vehicles

    # Not used
    def spawn_vehical_along_waypoints(
        self, name, model, start_transform, blocked_road_ids
    ):
        vehicle = self.spawn_vehicle(name, model, start_transform)
        get_waypoints = self.get_allowed_waypoints(
            start_location=start_transform.location, blocked_road_ids=blocked_road_ids
        )

        if vehicle is None:
            print(f"Vehicle {name} spawn failed")
            return None

        if not get_waypoints:
            print(f"No valid waypoints for vehicle {name}")
            return None

        wp_follow = WaypointFollower(
            actor=vehicle, target_speed=20.0, plan=get_waypoints, avoid_collision=True
        )
        print(f"Vehicle: {name} starts WpFollower. {wp_follow}")

        return wp_follow

    # Not used
    def get_allowed_waypoints(
        self,
        start_location: carla.Location,
        distance=5.0,
        num_waypoints=100,
        blocked_road_ids: None = None | list[int],
    ):
        if blocked_road_ids is None:
            blocked_road_ids = []

        allowed_waypoints = []
        current_wp = self.map.get_waypoint(start_location)

        for _ in range(num_waypoints):
            # Next Waypoints in "distance" meters
            next_wps = current_wp.next(distance)
            # Filter: only waypoints on allowed road_ids
            allowed_next_wps = [
                wp for wp in next_wps if wp.road_id not in blocked_road_ids
            ]

            if not allowed_next_wps:
                # If no allowed waypoints, end list
                break

            # Take a allowed waypoint (e.g. random, first one)
            current_wp = allowed_next_wps[0]
            allowed_waypoints.append((current_wp, RoadOption.LANEFOLLOW))

        return allowed_waypoints

    def _create_behavior(self):

        # Replaced by Parallel
        # root = py_trees.composites.Sequence("Scenario Root", memory=False)

        # Root: parallel -> all triggers run simultaneously
        root = py_trees.composites.Parallel(
            "ScenarioRoot",
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ALL,
        )

        vehicle1 = self.spawn_vehicle(
            name="v1",
            model="vehicle.tesla.model3",
            start_transform=carla.Transform(
                carla.Location(x=201, y=-205, z=0.5), carla.Rotation(0, 270, 0)
            ),
        )
        vehicle2 = self.spawn_vehicle(
            name="v2",
            model="vehicle.bmw.grandtourer",
            start_transform=carla.Transform(
                carla.Location(x=-52, y=-206, z=0.5), carla.Rotation(0, 270, 0)
            ),
        )
        vehicle3 = self.spawn_vehicle(
            name="v3",
            model="vehicle.ford.ambulance",
            start_transform=carla.Transform(
                carla.Location(x=48.5, y=191.5, z=0.2), carla.Rotation(0, 210, 0)
            ),
        )

        # Seq 1 1 + WP Follower 1
        seq1 = py_trees.composites.Sequence("Vehicle1Sequence", memory=False)

        ego_in_radius_1 = EgoInRadius(
            "VehicleReachedRadius_1",
            ego_vehicle=self.ego_vehicles[0],
            center_location=carla.Location(x=245, y=-55, z=0),
            radius=80.0,
        )
        seq1.add_child(ego_in_radius_1)

        wp1_start = self.map.get_waypoint(carla.Location(x=201, y=-205, z=0))
        wp1 = wp1_start.next(2)[0]

        wp_route_1 = [
            (wp1_start, RoadOption.LANEFOLLOW),
            (wp1, RoadOption.LANEFOLLOW),
            (wp1.next(20)[0], RoadOption.LANEFOLLOW),
            (wp1.next(20)[0].next(50)[0], RoadOption.LANEFOLLOW),
            (
                wp1.next(20)[0].next(50)[0].next(30)[0],
                RoadOption.LANEFOLLOW,
            ),
        ]

        seq1.add_child(
            WaypointFollower(actor=vehicle1, target_speed=20.0, plan=wp_route_1)
        )
        seq1.add_child(ChangeAutoPilot(vehicle1, True))

        # Seq 2
        seq2 = py_trees.composites.Sequence("Vehicle2Sequence", memory=False)

        ego_in_radius_2 = EgoInRadius(
            "TriggerVehicle2",
            ego_vehicle=self.ego_vehicles[0],
            center_location=carla.Location(x=-52, y=-206, z=0),
            radius=60.0,
        )
        seq2.add_child(ego_in_radius_2)
        seq2.add_child(ChangeAutoPilot(vehicle2, True))

        # Seq 3
        seq3 = py_trees.composites.Sequence("Vehicle3Sequence", memory=False)
        ego_in_radius_3 = EgoInRadius(
            "TriggerVehicle3",
            ego_vehicle=self.ego_vehicles[0],
            center_location=carla.Location(x=130, y=195, z=0),
            radius=10.0,
        )

        seq3.add_child(ego_in_radius_3)
        seq3.add_child(ChangeAutoPilot(vehicle3, True))

        # Seq 4
        # seq4 = py_trees.composites.Sequence("Vehicle4Sequence", memory=False)

        # vehicle4 = self.spawn_vehicle(
        #     name="v4",
        #     model="vehicle.ford.ambulance",
        #     start_transform=carla.Transform(
        #         carla.Location(x=40, y=193, z=0.2), carla.Rotation(0, 180, 0)
        #     ),
        # )
        # seq4.add_child(ChangeAutoPilot(vehicle4, True))
        # seq4.add_child(
        #     DestroyVehicleOnRoadID(
        #         name="DestroyOnForbiddenRoad",
        #         vehicle=vehicle4,
        #     )
        # )

        # Add independent sequences to parallel root
        root.add_child(seq1)
        root.add_child(seq2)
        root.add_child(seq3)

        # root.add_child(seq4)

        # vehiclesInAutopilot = self.spawn_vehicles_with_autopilot(50)

        # vehicleAuto = self.spawn_vehicle(
        #     name="vsdfs",
        #     model="vehicle.ford.ambulance",
        #     start_transform=carla.Transform(
        #         carla.Location(x=70, y=193, z=0.2), carla.Rotation(0, 180, 0)
        #     ),
        # )
        # for i in range(10):
        #     waypoints = self.map.generate_waypoints(100)
        #     vehicle = self.spawn_vehicle(
        #         f"Vehicle {i} in autopilot",
        #         random.choice(self.vehicle_blueprints).id,
        #         random.choice(waypoints).transform,
        #     )
        #     vehiclesInAutopilot.append(vehicle)

        # for i, vehicleAuto in enumerate(vehiclesInAutopilot):
        # seq = py_trees.composites.Sequence(f"Vehicle__Sequence", memory=False)
        # seq.add_child(ChangeAutoPilot(self.vAuto, True))
        # destroy_vehicle_on_road_id = DestroyVehicleOnRoadID(
        #     name=f"DestroyVehicle__OnForbiddenRoad", vehicle=self.vAuto
        # )
        # seq.add_child(destroy_vehicle_on_road_id)
        # root.add_child(seq)

        # monitor_forbidden_roads_parallel = py_trees.composites.Parallel(
        #     name="MonitorForbiddenRoads",
        #     policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE,
        # )

        # for i, vehicle in enumerate(vehiclesInAutopilot):
        #     monitor_forbidden_roads_parallel.add_child(
        #         DestroyVehicleOnRoadID(
        #             name=f"DestroyVehicle_{i}_OnForbiddenRoad", vehicle=vehicle
        #         )
        #     )

        # root.add_child(monitor_forbidden_roads_parallel)

        root.add_child(WaitForever())

        return root

    def _create_test_criteria(self):
        criteria = []
        if self.ego_vehicles:
            criteria.append(CollisionTest(self.ego_vehicles[0]))
        return criteria


class EgoInRadius(py_trees.behaviour.Behaviour):
    # Checks whether the ego vehicle is within a radius of a point.
    # SUCCESS = Ego is within radius
    # RUNNING/ FAILURE = Ego is outside

    def __init__(self, name, ego_vehicle, center_location, radius):
        super(EgoInRadius, self).__init__(name)
        self.ego_vehicle = ego_vehicle
        self.center = center_location
        self.radius = radius

    def update(self):
        if self.ego_vehicle is None:
            return py_trees.common.Status.RUNNING

        ego_loc = self.ego_vehicle.get_location()
        distance = ego_loc.distance(self.center)

        if distance <= self.radius:
            print(
                f"[Trigger] Ego vehicle is within range! (Distance: {distance:.2f} m)"
            )
            return py_trees.common.Status.SUCCESS
        else:
            return py_trees.common.Status.RUNNING


class DestroyVehicleOnRoadID(py_trees.behaviour.Behaviour):
    # Checks whether a vehicle is travelling on a forbidden road ID.
    # If so -> destroys the vehicle.

    def __init__(self, name, vehicle):
        super().__init__(name)
        self.vehicle = vehicle
        self.forbidden_roads = FORBIDDEN_ROADS
        self.map = None
        self.destroyed = False

    def initialise(self):
        self.world = CarlaDataProvider.get_world()
        self.map = self.world.get_map()

    def update(self):

        # Vehicle no longer exists
        if self.vehicle is None:
            return py_trees.common.Status.RUNNING

        if not self.vehicle.is_alive:
            self.destroyed = True
            return py_trees.common.Status.RUNNING

        location = self.vehicle.get_location()
        waypoint = self.map.get_waypoint(
            location, project_to_road=True, lane_type=carla.LaneType.Driving
        )

        if waypoint is None:
            return py_trees.common.Status.RUNNING

        road_id = waypoint.road_id
        lane_id = waypoint.lane_id

        print(f"[CHECK] veh={self.vehicle.id} road={road_id} lane={lane_id}")

        if road_id in self.forbidden_roads:
            forbidden_lanes = self.forbidden_roads[road_id]

        if road_id not in self.forbidden_roads:
            return py_trees.common.Status.RUNNING

        destroy = forbidden_lanes is None

        if forbidden_lanes is None and lane_id in forbidden_lanes:
            destroy = True

            if destroy:
                print(
                    f"[DestroyVehicleOnRoadID] Vehicle {self.vehicle.id} on road_id {road_id}, lane_id {lane_id} -> destroy"
                )

            # self.vehicle.set_autopilot(False)
            self.vehicle.destroy()
            # CarlaDataProvider.remove_actor(self.vehicle)
            self.world.debug.draw_string(
                location,
                f"Vehicle destoryed at road_id: {road_id}",
                False,
                carla.Color(255, 255, 0),
                0.1,
            )
            self.vehicle = None
            self.destroyed = True

            return py_trees.common.Status.RUNNING

        return py_trees.common.Status.RUNNING

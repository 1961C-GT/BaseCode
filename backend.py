from sgqlc.endpoint.http import HTTPEndpoint

import config
from pygeodesy.sphericalNvector import LatLon
import time
from statistics import mean
from algorithms.helpers.node import Node
import math


class Backend:
    CLEAR_NODES = "CLEAR_NODES"

    def __init__(self):
        self.base_1_node: Node = None
        self.base_2_node: Node = None
        self.endpoint = HTTPEndpoint(config.BACKEND_URL)

    def clear_nodes(self):
        mutation = \
            """
            mutation {
              clearNodes
            }       
            """
        self.endpoint(mutation)

    def update_node(self, node):
        if not node.is_resolved():
            return

        mutation = \
            """
            mutation {
              updateNode(id: "%(id)s", node: {
                type: %(type)s
                name: "%(name)s"
                pose: {
                  position: {
                    lat: %(lat).6f
                    lon: %(lon).6f
                  }
                }
              }) {
                id
              }
            }
            """

        if node.id == "0":
            self.base_1_node = node
            lat, lon = config.BASE_1_GPS
        elif node.id == "1":
            self.base_2_node = node
            # lat, lon = config.BASE_2_GPS  # could do this, but can also be sanity check for GPS translator
            lat, lon = self.translate_node_to_gps_coords(node)
        else:
            lat, lon = self.translate_node_to_gps_coords(node)

        mutation = mutation % {
            'id': node.id,
            'name': str(node),
            'type': 'BASE' if node.is_base else 'MOBILE',
            'lat': lat,
            'lon': lon
        }
        self.endpoint(mutation)

    def translate_node_to_gps_coords(self, node):
        if not self.base_1_node or not self.base_2_node:
            return node.x, node.y

        # Set up coordinate transforms
        base_1, base_2 = LatLon(*config.BASE_1_GPS), LatLon(*config.BASE_2_GPS)
        virtual_base_distance = self.base_2_node.x  # TODO: actually calculate this
        real_base_distance = base_1.distanceTo(base_2)
        distance_scale = real_base_distance / virtual_base_distance
        heading_offset = mean([base_1.initialBearingTo(base_2), base_2.initialBearingTo(base_1) - 180]) - 90

        # Transform node virtual coordinates
        new_x, new_y = self.rotate_point((node.x * distance_scale, node.y * distance_scale), heading_offset)
        n_d, n_a = math.sqrt(math.pow(new_x, 2) + math.pow(new_y, 2)), 90 - math.degrees(math.atan2(-new_y, new_x))

        # Add to base_1 GPS coords
        node_gps = base_1.destination(n_d, n_a)
        return node_gps.latlon2(ndigits=6)

    @staticmethod
    def rotate_point(point, angle):
        rad = math.radians(angle)
        x = math.cos(rad) * point[0] - math.sin(rad) * point[1]
        y = math.sin(rad) * point[0] + math.cos(rad) * point[1]
        return x, y

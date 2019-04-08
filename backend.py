from sgqlc.endpoint.http import HTTPEndpoint

import config


class Backend:
    CLEAR_NODES = "CLEAR_NODES"

    def __init__(self):
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
        pass

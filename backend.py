from sgqlc.endpoint.http import HTTPEndpoint

import config


class Backend:
    def __init__(self):
        self.endpoint = HTTPEndpoint(config.BACKEND_URL)

    def clear_nodes(self):
        mutation = \
            """
            mutation {
              clearNodes
            }       
            """
        print("Hello!1")
        self.endpoint(mutation)
        print("Hello!2")

    def update_node(self, node):
        pass

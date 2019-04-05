from sgqlc.endpoint.http import HTTPEndpoint

import config


class Backend:
    def __init__(self):
        self.endpoint = HTTPEndpoint(config.BACKEND_URL)
        pass

    def clear_nodes(self):
        mutation = \
            """
            mutation {
              clearNodes
            }       
            """
        self.endpoint(mutation)
        pass

    def update_node(self, node):
        pass

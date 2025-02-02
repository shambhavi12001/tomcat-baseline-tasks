import argparse
from multiprocessing import Process

from common import client_ai_teaming, pairing_clients
from config import DEFAULT_SERVER_ADDR, DEFAULT_SERVER_PORT
from network import Server, send
from tasks.affective_task import ServerAffectiveTask
from tasks.finger_tapping_task import ServerFingerTappingTask
from tasks.ping_pong_task import ServerPingPongTask
from tasks.rest_state import ServerRestState

REQUIRED_NUM_CONNECTIONS_REST_STATE = [1, 2, 3]
REQUIRED_NUM_CONNECTIONS_FINGER_TAPPING_TASK = [1, 2, 3]
REQUIRED_NUM_CONNECTIONS_AFFECTIVE_TASK = [1, 2, 3]
REQUIRED_NUM_CONNECTIONS_COMPETITIVE_PING_PONG_TASK = [2, 4]
REQUIRED_NUM_CONNECTIONS_COOPERATIVE_PING_PONG_TASK = [3, 4]


def _send_start(to_client_connections: list):
    data = {}
    data["type"] = "request"
    data["request"] = "start"
    send(to_client_connections, data)


def _run_ping_pong(to_client_connections: list, from_client_connections: dict, session_name: str, easy_mode: bool = True):
    server_ping_pong_task = ServerPingPongTask(to_client_connections, 
                                               from_client_connections,
                                               easy_mode=easy_mode,
                                               session_name=session_name)
    server_ping_pong_task.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run server of finger tapping task.')
    parser.add_argument("-a", "--address", default=DEFAULT_SERVER_ADDR, help="IP address of server")
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_SERVER_PORT, help="Port of server")
    args = parser.parse_args()

    server = Server(args.address, args.port)

    # Initial rest state

    server.establish_connections(REQUIRED_NUM_CONNECTIONS_REST_STATE)

    _send_start(list(server.to_client_connections.values()))

    server_rest_state = ServerRestState(list(server.to_client_connections.values()), 
                                        server.from_client_connections)
    server_rest_state.run()

    # Finger tapping task

    server.establish_connections(REQUIRED_NUM_CONNECTIONS_FINGER_TAPPING_TASK)

    _send_start(list(server.to_client_connections.values()))

    server_finger_tapping_task = ServerFingerTappingTask(list(server.to_client_connections.values()), 
                                                         server.from_client_connections)
    server_finger_tapping_task.run()

    # Individual affective task

    server.establish_connections(REQUIRED_NUM_CONNECTIONS_AFFECTIVE_TASK)

    _send_start(list(server.to_client_connections.values()))

    server_affective_task = ServerAffectiveTask(list(server.to_client_connections.values()), 
                                                     server.from_client_connections)
    
    server_affective_task.run("./tasks/affective_task/images/task_images", collaboration=False)

    # Team affective task

    server.establish_connections(REQUIRED_NUM_CONNECTIONS_AFFECTIVE_TASK)

    _send_start(list(server.to_client_connections.values()))

    server_affective_task.run("./tasks/affective_task/images/task_images", collaboration=True)

    server_affective_task.close_file()

    # Ping pong competitive

    server.establish_connections(REQUIRED_NUM_CONNECTIONS_COMPETITIVE_PING_PONG_TASK)

    _send_start(list(server.to_client_connections.values()))

    client_pairs = pairing_clients(server.to_client_connections, server.from_client_connections)

    ping_pong_processes = []
    for session_id, (to_client_connection_pair, from_client_connection_pair) in enumerate(client_pairs):
        to_client_connections = []
        for to_client_connection_team in to_client_connection_pair:
            to_client_connections = to_client_connections + list(to_client_connection_team.values())

        session_name = "competitive_" + str(session_id)
        process = Process(target=_run_ping_pong, args=(to_client_connections, from_client_connection_pair, session_name))
        ping_pong_processes.append(process)

    for process in ping_pong_processes:
        process.start()
    
    for process in ping_pong_processes:
        process.join()

    # Ping pong cooperative

    server.establish_connections(REQUIRED_NUM_CONNECTIONS_COOPERATIVE_PING_PONG_TASK)

    _send_start(list(server.to_client_connections.values()))

    client_pairs = client_ai_teaming(server.to_client_connections, server.from_client_connections)

    ping_pong_processes = []
    for session_id, (to_client_connection_teams, from_client_connection_teams) in enumerate(client_pairs):
        to_client_connections = []
        for to_client_connection_team in to_client_connection_teams:
            to_client_connections = to_client_connections + list(to_client_connection_team.values())

        session_name = "cooperative_" + str(session_id)
        process = Process(target=_run_ping_pong, args=(to_client_connections, from_client_connection_teams, session_name, False))
        ping_pong_processes.append(process)

    for process in ping_pong_processes:
        process.start()

    for process in ping_pong_processes:
        process.join()

    server.establish_connections()
    server.close_connections_listener()

import sqlite3
import settings
from chat_web_socket import RocketChatReader
from rocketchat_API.rocketchat import RocketChat


class DBApi:
    def __init__(self):
        self.__connection = sqlite3.connect(settings.DB_PATH)
        self.__cursor = self.__connection.cursor()

    def help(self) -> list:
        return [
            "$bot_api create_new_user username gitlab_username",
            "$bot_api add_user_to_project username project_id impact",
            "$bot_api delete_user username",
            "$bot_api delete_user_from_project username project_id",
            "$bot_api ger_users_from_project project_id"
        ]

    def create_new_user(self, username: str, gitlab_username: str) -> str:

        if not self.__find_user(username):
            self.__cursor.execute("""INSERT INTO developer (username, gitlab) VALUES (?, ?)""",
                                  (username, gitlab_username))
            self.__connection.commit()
            return f"User {username} created"
        else:
            return f"User {username} already exists"

    def add_user_to_project(self, username: str, project_id: str, impact: int) -> str:

        if not self.__find_user(username):
            return f"User {username} not found"

        if not self.__find_project(project_id):
            return f"Project {project_id} not found"

        self.__cursor.execute("""INSERT INTO developer_project (developer, project, impact)VALUES (?, ?, ?)""",
                              (username, project_id, impact))
        self.__connection.commit()
        return f"User {username} added to project {project_id}"

    def delete_user(self, username: str) -> str:

        if not self.__find_user(username):
            return f"User {username} not found"
        self.__cursor.execute("""DELETE FROM developer WHERE developer.username = ?""", [username])
        self.__cursor.execute("""DELETE FROM developer_project WHERE developer = ?""", [username])
        self.__connection.commit()
        return f"User {username} removed"

    def delete_user_from_project(self, username: str, project_id: str) -> str:

        if not self.__find_user(username):
            return f"User {username} not found"

        if not self.__find_project(project_id):
            return f"Project {project_id} not found"

        self.__cursor.execute("""DELETE FROM developer_project WHERE developer = ? AND
                                                                        project = ?""", (username, project_id))
        self.__connection.commit()
        return f"User {username} removed from {project_id} project"

    def ger_users_from_project(self, project_id: str) -> str:

        if not self.__find_project(project_id):
            return f"Project {project_id} not found"

        self.__cursor.execute("""SELECT developer FROM developer_project WHERE project = ?""", [project_id])
        users = self.__cursor.fetchall()
        response = "".join([user[0] + "\n" for user in users])
        response = f"Users in the project {project_id}:\n{response}"
        return response

    # internal methods:
    def __find_user(self, username: str) -> bool:

        self.__cursor.execute("""SELECT * FROM developer WHERE developer.username = ?""", [username])
        if len(self.__cursor.fetchall()) == 0:
            return False
        else:
            return True

    def __find_project(self, project_id: str) -> bool:

        self.__cursor.execute("""SELECT * FROM project WHERE project.project_id = ?""", [project_id])
        if len(self.__cursor.fetchall()) == 0:
            return False
        else:
            return True

    def process(self, msg: list) -> str:
        if msg[1] == "create_new_user":
            return self.create_new_user(msg[2], msg[3])
        elif msg[1] == "add_user_to_project":
            return self.add_user_to_project(msg[2], msg[3], int(msg[4]))
        elif msg[1] == "delete_user":
            return self.delete_user(msg[2])
        elif msg[1] == "delete_user_from_project":
            return self.delete_user_from_project(msg[2], msg[3])
        elif msg[1] == "ger_users_from_project":
            return self.ger_users_from_project(msg[2])
        else:
            return "request error"


class Main:
    def __init__(self, chat_server: str, channel_names: list):
        self.__rocket = RocketChat(settings.ROCKET_USERNAME, settings.ROCKET_PASSWORD, server_url=settings.ROCKET_URL)
        self.__reader = RocketChatReader(chat_server, channel_names)
        self.__db_api = DBApi()

    def start(self) -> None:
        self.__reader.connect()
        while True:
            request = self.__reader.get_messages_queue().get()
            message = request.get_message().split(" ")
            if message[0] == "$bot_api":
                response = self.__db_api.process(message)
                self.__rocket.chat_post_message(response, room_id=request.get_channel_id(), alias='BOT NOTIFICATION')

from utils.response import response
from utils.queue import QueueCreate

from starlette.background import BackgroundTask

class Pug(object):
    def __init__(self, current_league):
        self.current_league = current_league

    async def create(self, players: dict, maps: dict, team_names: dict):
        """ Creates pug lobby, if creates correct returns details on pug.
                - players 
                    {
                        "options": {
                            "type": "random"      / "elo"       / "given",
                            "param": None        / ASC OR DESC / {"capt_1": index, "capt_2": index}
                            "selection": "ABBAABBA" / "ABBABABA" / "ABABABAB",
                            "assiged_teams": True / False
                        },
                        "list": {
                            "user_id": None / 1 / 2
                        },
                    }
                - maps 
                    {
                        "options": {
                            "type": "vetos" / "random" / "vote" / "given (just uses the 1st index of the list)",
                            "selection": "ABBAABBA" / "ABBABABA" / "ABABABAB",
                        },
                        "list": [list of full map names],
                    }
                - team_names
                    {
                        "team_1": "Max 13 characters",
                        "team_2": "",
                    }
        """

        queue_allowed = await self.current_league.queue_allowed()
        if not queue_allowed.error:
            in_memory_cache = self.current_league.obj.in_memory_cache
            
            # Once this queue is inserted into the database or it fails
            # -1 is removed from in_memory_cache.started_queues for this
            # league ID.
            if in_memory_cache.started_queues.get(self.current_league.league_id):
                in_memory_cache.started_queues[self.current_league.league_id] += 1
            else:
                in_memory_cache.started_queues[self.current_league.league_id] = 1

            if not players.get("options") or type(players["options"]) != dict \
                 or not players["options"].get("type") or not players.get("list") \
                     or type(players["list"]) != dict \
                        or not players["options"].get("assiged_teams") \
                            or not players["options"].get("selection") \
                                or not players["options"].get("param"):

                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                return response(error="Players payload formatted incorrectly")

            if len(maps) < 1 or not maps.get("options") \
                or type(maps["options"]) != dict or not maps["options"].get("type") \
                    or not maps["options"].get("selection") or not maps.get("list") \
                        or type(maps["list"]) != list:

                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                return response(error="Maps payload formatted incorrectly")

            if not self.current_league.obj.config.pug["selection_types"].get(players["options"]["selection"]) \
                or not self.current_league.obj.config.pug["selection_types"].get(maps["options"]["selection"]):

                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                return response(error="Invaild selection type")

            len_players = len(players["list"])
            if (len_players % 2) == 1 or len_players < 2 and len_players > 10:

                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                return response(error="Odd amout of players or players is above 2 or below 10")

            available_server = await self.current_league.obj.get_server()
            if available_server.error:

                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                return available_server

            in_memory_cache.temp_server_blacklist.append(available_server.data)

            if not team_names.get("team_1") or not team_names.get("team_2") \
                or type(team_names["team_1"]) != str or type(team_names["team_2"]) != str:
                
                team_names = {
                    "team_1": "Team 1",
                    "team_2": "Team 2",
                }

            queue = QueueCreate(players=players, maps=maps, team_names=team_names,
                                server_id=available_server.data,
                                league_id=self.current_league.league_id,
                                region=self.current_league.region)

            # Ensures valid user IDs are given
            # If errors returns response return with
            # data of incorrect user ids.
            players_validate = await self.current_league.obj.players.validate_many(user_ids=queue.players_list)
            if players_validate.error:
                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                in_memory_cache.temp_server_blacklist.remove(available_server.data)
                
                return players_validate

            if players["options"]["type"] == "random":
                 assign_random = queue.assign_random()

                # If none isn't returned
                # something has errored.
                 if assign_random:
                     in_memory_cache.started_queues[self.current_league.league_id] -= 1
                     in_memory_cache.temp_server_blacklist.remove(available_server.data)
                
                     return assign_random

            elif players["options"]["type"] == "elo" or players["options"]["type"] == "given":
                if not players["options"].get("param"):

                    in_memory_cache.started_queues[self.current_league.league_id] -= 1
                    in_memory_cache.temp_server_blacklist.remove(available_server.data)

                    return response(error="Param is required for type {}".format(players["options"]["type"]))

                if players["options"]["type"] == "elo":
                    players_elo = await self.current_league.obj.players.fetch_many(user_ids=queue.players_list, include_stats=True)

                    if not players_elo.error:
                        assign_elo = queue.assign_elo(players_elo)
                        if assign_elo:

                            in_memory_cache.started_queues[self.current_league.league_id] -= 1
                            in_memory_cache.temp_server_blacklist.remove(available_server.data)

                            return assign_elo
                    else:
                        in_memory_cache.started_queues[self.current_league.league_id] -= 1
                        in_memory_cache.temp_server_blacklist.remove(available_server.data)

                        return response(error="Something went wrong during elo fetch")
                else:
                    if type(players["options"]["param"]) != dict or not players["options"]["param"].get("capt_1") \
                        or not players["options"]["param"].get("capt_2") or type(players["options"]["param"]["capt_1"]) != int \
                            or type(players["options"]["param"]["capt_2"]) != int:

                        in_memory_cache.started_queues[self.current_league.league_id] -= 1
                        in_memory_cache.temp_server_blacklist.remove(available_server.data)

                        return response(error="Param payload formatted incorrectly")

                    if players["options"]["param"]["capt_1"] > len_players - 1 or \
                         players["options"]["param"]["capt_2"] > len_players - 1:

                         in_memory_cache.started_queues[self.current_league.league_id] -= 1
                         in_memory_cache.temp_server_blacklist.remove(available_server.data)

                         return response(error="Index is not within range")

                    assign_given = queue.assign_given(players["options"]["param"]["capt_1"], players["options"]["param"]["capt_2"])
                    if assign_given:
                        in_memory_cache.started_queues[self.current_league.league_id] -= 1
                        in_memory_cache.temp_server_blacklist.remove(available_server.data)

                        return assign_given
            else:
                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                in_memory_cache.temp_server_blacklist.remove(available_server.data)

                return response(error="{} isn't a valid type".format(players["options"]["type"]))

            queue_create = queue.create()
            # If none isn't returned
            # something has errored.
            if queue_create:
                in_memory_cache.started_queues[self.current_league.league_id] -= 1
                in_memory_cache.temp_server_blacklist.remove(available_server.data)

                return queue_create

            query = """INSERT INTO scoreboard_total (match_id, league_id, 
                                                     status, server_id, 
                                                     region, team_1_name,
                                                     team_2_name) 
                                            VALUES  (:match_id, :league_id, 
                                                     :status, :server_id, 
                                                     :region, :team_1_name,
                                                     :team_2_name)"""
            await self.current_league.obj.database.execute(query=query, values=queue.data["details"])

            query = """INSERT INTO scoreboard (match_id, user_id, captain, team) 
                                       VALUES (:match_id, :user_id, :captain, :team)"""
            await self.current_league.obj.database.execute_many(query=query, values=queue.insert)

            # Removing a queue from out temp cache.
            in_memory_cache.started_queues[self.current_league.league_id] -= 1
            # Removing server ID from temp server blacklist
            in_memory_cache.temp_server_blacklist.remove(available_server.data)

            # Server startup push into a task to run in the backgroud.
            server_task = BackgroundTask(self.current_league.obj.sessions.dactyl.client(server_id=available_server.data).start)

            return response(backgroud=server_task, data=queue.data)
        else:
            return response(error="Over queue limit")
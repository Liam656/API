from utils.response import response

from models.player import PlayerModel


class Players(object):
    def __init__(self, current_league, user_ids: list):
        self.current_league = current_league

        self.values = {
            "user_ids": user_ids,
            "region": current_league.region,
        }

    async def fetch(self, include_stats=False):
        """ Selects given players. """

        values = dict(self.values)

        if include_stats:
            query = """SELECT IFNULL(statistics.elo, 0) AS elo,
                              IFNULL(statistics.kills, 0) AS kills,
                              IFNULL(statistics.deaths, 0) AS deaths,
                              IFNULL(statistics.assists, 0) AS assists,
                              IFNULL(statistics.shots, 0) AS shots,
                              IFNULL(statistics.hits, 0) AS hits,
                              IFNULL(statistics.damage, 0) AS damage,
                              IFNULL(statistics.headshots, 0) AS headshots,
                              IFNULL(statistics.roundswon, 0) AS roundswon,
                              IFNULL(statistics.roundslost, 0) AS roundslost,
                              IFNULL(statistics.wins, 0) AS wins,
                              IFNULL(statistics.ties, 0) AS ties,
                              IFNULL(statistics.losses, 0) AS losses,
                              users.discord_id, users.name,
                              users.pfp, users.user_id,
                              users.steam_id, users.joined
                    FROM users
                        LEFT JOIN statistics
                                ON users.user_id = statistics.user_id
                                   AND statistics.league_id = :league_id
                    WHERE users.region = :region
                          AND users.user_id IN :user_ids
                    ORDER BY statistics.elo DESC"""

            values["league_id"] = self.current_league.league_id
        else:
            query = """SELECT discord_id, name, pfp, user_id, steam_id, joined
                       FROM users WHERE region = :region
                                        AND user_id IN :user_ids"""

        rows_formatted = []
        rows_formatted_append = rows_formatted.append
        async for row in self.current_league.obj\
                .database.iterate(query=query, values=values):

            player = PlayerModel(row)

            if include_stats:
                rows_formatted_append(player.full)
            else:
                rows_formatted_append(player.minimal)

        return response(data=rows_formatted)

    async def validate(self):
        """ Validates given users & returns data of users who aren't valid. """

        user_ids = list(self.values["user_ids"])
        user_ids_remove = user_ids.remove

        query = """SELECT user_id FROM users
                   WHERE user_id IN :user_ids AND region = :region"""

        async for row in self.current_league.obj.database.iterate(
                query=query,
                values=self.values):
            user_ids_remove(row["user_id"])

        if len(user_ids) == 0:
            return response(data="Valid user IDs")
        else:
            return response(data=user_ids, error="Invalid user IDs")

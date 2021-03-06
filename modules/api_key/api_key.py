import secrets

from utils.response import response

from modules.api_key.interact import Interact


class ApiKey(object):
    def __init__(self, current_league):
        self.current_league = current_league

    def interact(self, api_key):
        """ Object for interacting with a
            API key.
        """

        return Interact(current_league=self.current_league,
                        api_key=api_key)

    async def paths(self):
        """ Gets all paths current league can access. """

        query = """SELECT DISTINCT api_paths.path
                   FROM api_permissions
                        INNER JOIN api_paths
                            ON api_permissions.path_id = api_paths.path_id
                   WHERE api_permissions.league_id = :league_id"""

        values = {"league_id": self.current_league.league_id, }

        rows_formatted = []
        rows_formatted_append = rows_formatted.append
        async for row in self.current_league.obj.database.iterate(
                query=query, values=values):
            rows_formatted_append(row["path"])

        return response(data=rows_formatted)

    async def generate(self, user_id, access_level: int, active: bool = True):
        """ Generates API key """

        user_validate = await self.current_league.obj.validate_user(
            user_id=user_id
        )

        if not user_validate:
            return response(data="Invalid user")

        if active:
            active = 1
        else:
            active = 0

        query = """INSERT INTO api_keys (
                       user_id,
                       `key`,
                       league_id,
                       access_level,
                       active
                    ) VALUES (
                       :user_id,
                       :key,
                       :league_id,
                       :access_level,
                       :active
                    )"""

        values = {
            "user_id": user_id,
            "key": secrets.token_urlsafe(24),
            "league_id": self.current_league.league_id,
            "access_level": access_level,
            "active": active,
        }

        await self.current_league.obj.database.execute(
            query=query,
            values=values
        )

        return response(data=True)

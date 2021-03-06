from starlette.endpoints import HTTPEndpoint

from webargs import fields
from webargs_starlette import use_args

from utils.responder import responder


class PlayersList(HTTPEndpoint):
    @use_args({"limit": fields.Integer(missing=25, min=1, max=50),
               "offset": fields.Integer(missing=25, min=1, max=50),
               "search": fields.String(),
               "desc": fields.Bool(missing=True), })
    async def get(self, request, args):
        """ List players. """

        return responder.render(
            await request.state.league.list(**args).players()
        )


class MatchesList(HTTPEndpoint):
    @use_args({"limit": fields.Integer(missing=25, min=1, max=50),
               "offset": fields.Integer(missing=25, min=1, max=50),
               "search": fields.String(),
               "desc": fields.Bool(missing=True), })
    async def get(self, request, args):
        """ Gets list of matches. """

        return responder.render(
            await request.state.league.list(**args).matches()
        )

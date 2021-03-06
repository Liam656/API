from starlette.middleware.base import BaseHTTPMiddleware

from datetime import datetime, timedelta


class APIKeyValidation(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path not in self.obj.config.auth_bypass:
            if request.query_params.get("api_key") \
                and request.query_params.get("league_id") \
                    and request.query_params.get("region"):
                api_key = request.query_params["api_key"]
                league_id = request.query_params["league_id"]

                if self.obj.config.master_key != api_key:
                    api_key_request = [api_key, league_id, request.url.path]

                    if api_key_request not in self.obj.in_memory_cache.api_key:
                        validate = await self.obj.api.validate(
                            api_key=api_key,
                            league_id=league_id,
                            request_path=request.url.path
                        )

                        self.obj.in_memory_cache.api_key_requests[api_key] = {
                            "date": datetime.now()
                            + timedelta(
                                seconds=self.obj.config.cache["max_age"]
                            ),
                        }

                        if not validate:
                            return self.obj.api.unauthorized()
                        else:
                            self.obj.in_memory_cache.api_key.append(
                                api_key_request
                            )
                    else:
                        if len(self.obj.in_memory_cache.api_key_requests) > \
                                self.obj.config.cache["max_amount"]:
                            # Clears whole cache if total
                            # amount of cached items is above cache_max_amount.

                            self.obj.in_memory_cache.api_key_requests = {}
                            self.obj.in_memory_cache.api_key = {}
                        elif datetime.now() >= \
                                self.obj.in_memory_cache. \
                                api_key_requests[api_key]["date"]:

                            # Clears api auth cache after x amount of seconds.
                            self.obj.in_memory_cache.api_key.remove(
                                api_key_request
                            )
                            self.obj.in_memory_cache.api_key_requests.pop(
                                api_key
                            )

                request.state.league = self.obj.league(
                    league_id=league_id,
                    region=request.query_params["region"].lower()
                )
            else:
                return self.obj.api.unauthorized()

        # If it passes all our validation process the request.
        response = await call_next(request)
        return response

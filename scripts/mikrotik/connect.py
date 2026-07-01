import routeros_api
import os

import routeros_api

from dotenv import load_dotenv

load_dotenv()

def get_mikrotik_api():

    connection = routeros_api.RouterOsApiPool(

        os.getenv("MIKROTIK_HOST"),

        username=os.getenv("MIKROTIK_USERNAME"),

        password=os.getenv("MIKROTIK_PASSWORD"),

        port=int(
            os.getenv(
                "MIKROTIK_PORT",
                "8728"
            )
        ),

        plaintext_login=(
            os.getenv(
                "MIKROTIK_PLAINTEXT_LOGIN",
                "True"
            ).lower() == "true"
        )
    )

    api = connection.get_api()

    return api, connection

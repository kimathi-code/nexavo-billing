import logging


# Initialize the logger
logger = logging.getLogger("mikrotik")

def disable_ppp_secret(username, api):
    logger.info(f"Initiating disable sequence for PPP secret: {username}")

    try:
        ppp_secret = api.get_resource('/ppp/secret')
        secret = ppp_secret.get(name=username)

        # Ensuring the list is not empty before accessing index 0
        if secret and len(secret) > 0:
            secret_id = secret[0]['id']
            ppp_secret.set(id=secret_id, disabled='yes')

            logger.info(f"Successfully disabled PPP secret for user: {username}")
            return True
        else:
            logger.warning(f"Disable failed: PPP secret not found for user: {username}")
            return False
    except Exception:
        logger.exception(f"Error disabling PPP secret for {username}")
        return False    


def enable_ppp_secret(username, api):
    logger.info(f"Initiating enable sequence for PPP secret: {username}")

    try:
        ppp_secret = api.get_resource('/ppp/secret')
        secret = ppp_secret.get(name=username)

        if secret and len(secret) > 0:
            secret_id = secret[0]['id']
            ppp_secret.set(id=secret_id, disabled='no')

            logger.info(f"Successfully enabled PPP secret for user: {username}")
            return True
        else:
            logger.warning(f"Enable failed: PPP secret not found for user: {username}")
            return False
    except Exception:
        logger.exception(f"Error enabling PPP secret for {username}")
        return False



def disconnect_active_session(username, api):
    logger.info(f"Attempting to disconnect active session for user: {username}")

    try:
        ppp_active = api.get_resource('/ppp/active')
        active = ppp_active.get(name=username)
        if active and len(active) > 0:
            active_id = active[0]['id']
            ppp_active.remove(id=active_id)

            logger.info(f"Active session disconnected for user: {username}")
            return True
        else:
            logger.warning(f"No active session found for user: {username}")
            return False
    except Exception:
        logger.exception(f"Error disconnecting active session for {username}")
        return False



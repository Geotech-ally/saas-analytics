import logging
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class LoginAnonThrottle(AnonRateThrottle):
    scope = "login"


class LoginBlockThrottle(UserRateThrottle):
    scope = "login_block"


class PasswordResetAnonThrottle(AnonRateThrottle):
    scope = "password_reset"


class PasswordResetBlockThrottle(UserRateThrottle):
    scope = "password_reset_block"

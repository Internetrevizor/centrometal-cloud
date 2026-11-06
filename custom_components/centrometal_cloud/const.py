DOMAIN = "centrometal_cloud"
WEB_BOILER_CLIENT = "web_boiler_client"
WEB_BOILER_SYSTEM = "web_boiler_system"

CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_RETRY_BASE_INTERVAL = "retry_base_interval"
CONF_RETRY_MAX_INTERVAL = "retry_max_interval"
# Whether entity names start with the product name ("PelTec II Lambda ...").
CONF_PRODUCT_PREFIX = "product_prefix"

DEFAULT_REFRESH_INTERVAL = 240
DEFAULT_RETRY_BASE_INTERVAL = 60
DEFAULT_RETRY_MAX_INTERVAL = 1800
DEFAULT_PRODUCT_PREFIX = True

# Kept as aliases in case anything external imports these names directly.
WEB_BOILER_LOGIN_RETRY_INTERVAL = DEFAULT_RETRY_BASE_INTERVAL
WEB_BOILER_REFRESH_INTERVAL = DEFAULT_REFRESH_INTERVAL

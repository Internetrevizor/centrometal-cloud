WEB_BOILER_WEBROOT = "https://www.web-boiler.com"

WEB_BOILER_STOMP_LOGIN_USERNAME = "appuser"
WEB_BOILER_STOMP_LOGIN_PASSCODE = "appuser"
WEB_BOILER_STOMP_URL = "wss://web-boiler.com:15671/ws"
# Since 14.11.2026 the portal refuses a subscription to "/topic/cm.inst.<type>.<serial>" (ACCESS_REFUSED - read
# access to exchange 'amq.topic'); its realtime data is on the "stomp" exchange.
WEB_BOILER_STOMP_DEVICE_TOPIC = "/exchange/stomp/cm.inst."
# Prefixes of the destination header of a realtime message: the current one, and the one before 14.11.2026.
WEB_BOILER_STOMP_DEVICE_DESTINATIONS = (WEB_BOILER_STOMP_DEVICE_TOPIC, "/topic/cm.inst.")

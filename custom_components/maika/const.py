"""Constants for the MAIKA integration."""

from __future__ import annotations

DOMAIN = "maika"
INTEGRATION_VERSION = "1.6.2"

APP_VERSION = "3.2.3"
APP_DEVICE_TYPE = "android"
APP_LANGUAGE = "vi-VN"
APP_TIMEZONE = "Asia/Ho_Chi_Minh"

USERS_BASE_URL = "https://users.iviet.com"
CHATBOT_BASE_URL = "https://chatbot.iviet.com"

CONF_PHONE_NUMBER = "phone_number"
CONF_PASSWORD = "password"
CONF_CLIENT_ID = "client_id"
CONF_SESSION_ID = "session_id"
CONF_LICENSE_KEY = "license_key"
CONF_LICENSE_SERVER_URL = "license_server_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_CLOUD_CAST = "enable_experimental_cloud_cast"
CONF_ENABLE_VOICE_COMMAND_SENSOR = "enable_voice_command_sensor"
CONF_VOICE_COMMAND_RULES = "voice_command_rules"
CONF_VOICE_SUCCESS_MEDIA_PLAYER_ENTITY_ID = "voice_success_media_player_entity_id"
CONF_VOICE_SUCCESS_AUDIO_URL = "voice_success_audio_url"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 3600
DEFAULT_VOICE_COMMAND_RULES = ""

WAKEWORD_SENSITIVITY_OPTIONS = ["low", "medium", "high"]
WAKEWORD_RESPONSE_OPTIONS = [
    "wakeword_response_silent",
    "wakeword_response_ringtone",
    "wakeword_response_default",
]

DEVICE_INFO_FIELDS = "current_playback,volume,latest_playlist,device_id,mute"

REST_UPDATE_FIELDS = {
    "address",
    "calling_name",
    "name",
    "tts_voice",
    "wakeword_response_type",
    "wakeword_sensitivity_level",
}

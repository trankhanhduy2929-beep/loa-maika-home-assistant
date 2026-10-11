"""Build-time licensing configuration for MAIKA."""

from __future__ import annotations

DEFAULT_LICENSE_SERVER_URL = "https://maika-license-server.trankhanhduy2929.workers.dev"
PORTAL_PUBLIC_URL = "https://maika-license-admin-vercel.vercel.app"
LICENSE_PORTAL_URL = f"{PORTAL_PUBLIC_URL}/portal" if PORTAL_PUBLIC_URL else ""
BUNDLED_VOICE_SUCCESS_AUDIO_URL = (
    f"{PORTAL_PUBLIC_URL}/mp3/maika.mp3" if PORTAL_PUBLIC_URL else ""
)
LICENSE_PUBLIC_KEY_B64 = "MCowBQYDK2VwAyEAEKRlfmrmFjPIWtusz/FVP0XwExzf1iVMgj5cnHlptPE="

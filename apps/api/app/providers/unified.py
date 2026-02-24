"""Unified provider — handles all free-tier generation APIs via config-driven dispatch.

Each provider is a method named `_call_{handler}` where `handler` comes from
the variant_config in the registry.  This replaces the 23 individual provider
files from Phases 3-10.
"""

import asyncio
import logging
import urllib.parse

from app.providers.base import AbstractProvider
from app.schemas.generate import GenerationResult

logger = logging.getLogger(__name__)


class UnifiedProvider(AbstractProvider):
    """Single provider class for all free-tier AI generation APIs."""

    model_id: str = "unified"
    media_type: str = "image"

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None,
        params: dict,
    ) -> GenerationResult:
        handler_name = self.variant_config.get("handler", "")
        handler = getattr(self, f"_call_{handler_name}", None)
        if handler is None:
            return self._error(f"Unknown handler: '{handler_name}'")
        try:
            return await handler(prompt, negative_prompt, params)
        except Exception as e:
            logger.exception("Provider %s failed", self.model_id)
            return self._error(f"Provider error: {e}")

    # ------------------------------------------------------------------
    # Pollinations.ai — zero auth, unlimited free images
    # GET https://image.pollinations.ai/prompt/{prompt}
    # ------------------------------------------------------------------
    async def _call_pollinations(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        encoded = urllib.parse.quote(prompt, safe="")
        width = params.get("width", 1024)
        height = params.get("height", 1024)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&nologo=true&seed={id(prompt) % 999999}"
        )
        # Pollinations returns the image directly at this URL — no API call needed.
        # We just validate the URL is reachable.
        async with self._http_client(timeout=60.0) as client:
            resp = await client.head(url)
            if resp.status_code >= 400:
                return self._error(f"Pollinations returned HTTP {resp.status_code}")
        return self._ok(url, {"width": width, "height": height, "provider": "pollinations"})

    # ------------------------------------------------------------------
    # Together AI — OpenAI-compatible, 3 months free FLUX
    # POST https://api.together.xyz/v1/images/generations
    # ------------------------------------------------------------------
    async def _call_together(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        model = self.variant_config.get("model", "black-forest-labs/FLUX.1-schnell-Free")
        async with self._http_client(timeout=90.0) as client:
            resp = await client.post(
                "https://api.together.xyz/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "width": params.get("width", 1024),
                    "height": params.get("height", 1024),
                    "n": 1,
                },
            )
            if resp.status_code == 401:
                return self._error("Authentication failed. Check your Together AI API key.")
            if resp.status_code >= 400:
                return self._error(f"Together API error ({resp.status_code}): {resp.text}")
            data = resp.json()
        images = data.get("data", [])
        if not images:
            return self._error("Together AI returned no images.")
        img_url = images[0].get("url") or images[0].get("b64_json")
        if not img_url:
            return self._error("Together AI returned empty image data.")
        if images[0].get("b64_json"):
            img_url = f"data:image/png;base64,{img_url}"
        return self._ok(img_url, {"model": model, "provider": "together"})

    # ------------------------------------------------------------------
    # Google Gemini / Imagen — free tier ~500 images/day
    # POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateImages
    # ------------------------------------------------------------------
    async def _call_gemini(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        model = self.variant_config.get("model", "imagen-3.0-generate-002")
        base_url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/{model}:predict?key={self.api_key}"
        )
        ratio = params.get("aspect_ratio", "1:1")
        async with self._http_client(timeout=60.0) as client:
            resp = await client.post(
                base_url,
                headers={"Content-Type": "application/json"},
                json={
                    "instances": [{"prompt": prompt}],
                    "parameters": {
                        "sampleCount": 1,
                        "aspectRatio": ratio,
                    },
                },
            )
            if resp.status_code in (401, 403):
                return self._error("Authentication failed. Check your Google API key.")
            if resp.status_code >= 400:
                return self._error(f"Gemini API error ({resp.status_code}): {resp.text}")
            data = resp.json()
        preds = data.get("predictions", [])
        if not preds:
            return self._error("Gemini returned no predictions.")
        b64 = preds[0].get("bytesBase64Encoded", "")
        mime = preds[0].get("mimeType", "image/png")
        if not b64:
            return self._error("Gemini returned empty image data.")
        url = f"data:{mime};base64,{b64}"
        return self._ok(url, {"aspect_ratio": ratio, "provider": "gemini"})

    # ------------------------------------------------------------------
    # Cloudflare Workers AI — 100K requests/day free
    # POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/...
    # ------------------------------------------------------------------
    async def _call_cloudflare(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        account_id = self.variant_config.get("account_id", "")
        cf_model = self.variant_config.get(
            "model", "@cf/stabilityai/stable-diffusion-xl-base-1.0"
        )
        if not account_id:
            return self._error("Cloudflare account_id not configured.")
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{cf_model}"
        async with self._http_client(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"prompt": prompt},
            )
            if resp.status_code in (401, 403):
                return self._error("Authentication failed. Check your Cloudflare API token.")
            if resp.status_code >= 400:
                return self._error(f"Cloudflare API error ({resp.status_code}): {resp.text}")
            # Cloudflare returns raw image bytes
            import base64
            b64 = base64.b64encode(resp.content).decode()
        return self._ok(
            f"data:image/png;base64,{b64}",
            {"model": cf_model, "provider": "cloudflare"},
        )

    # ------------------------------------------------------------------
    # xAI / Grok Imagine — OpenAI-compatible, $25 free credits
    # POST https://api.x.ai/v1/images/generations
    # ------------------------------------------------------------------
    async def _call_grok(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        model = self.variant_config.get("model", "grok-2-image")
        async with self._http_client(timeout=90.0) as client:
            resp = await client.post(
                "https://api.x.ai/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "n": 1,
                },
            )
            if resp.status_code == 401:
                return self._error("Authentication failed. Check your xAI API key.")
            if resp.status_code >= 400:
                return self._error(f"Grok API error ({resp.status_code}): {resp.text}")
            data = resp.json()
        images = data.get("data", [])
        if not images:
            return self._error("Grok returned no images.")
        img_url = images[0].get("url", "")
        if not img_url:
            return self._error("Grok returned empty image data.")
        return self._ok(img_url, {"model": model, "provider": "xai"})

    # ------------------------------------------------------------------
    # Hugging Face Inference API — free tier with monthly credits
    # POST https://router.huggingface.co/hf-inference/models/{model_id}
    # ------------------------------------------------------------------
    async def _call_huggingface(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        hf_model = self.variant_config.get(
            "model", "stabilityai/stable-diffusion-xl-base-1.0"
        )
        url = f"https://router.huggingface.co/hf-inference/models/{hf_model}"
        async with self._http_client(timeout=120.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": prompt},
            )
            if resp.status_code in (401, 403):
                return self._error("Authentication failed. Check your Hugging Face API key.")
            if resp.status_code == 503:
                return self._error("Model is loading on Hugging Face. Please try again in ~30s.")
            if resp.status_code >= 400:
                return self._error(f"HuggingFace API error ({resp.status_code}): {resp.text}")
            import base64
            b64 = base64.b64encode(resp.content).decode()
        return self._ok(
            f"data:image/png;base64,{b64}",
            {"model": hf_model, "provider": "huggingface"},
        )

    # ------------------------------------------------------------------
    # DeepAI — simple REST, free rate-limited
    # POST https://api.deepai.org/api/text2img
    # ------------------------------------------------------------------
    async def _call_deepai(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        async with self._http_client(timeout=60.0) as client:
            resp = await client.post(
                "https://api.deepai.org/api/text2img",
                headers={"api-key": self.api_key},
                data={"text": prompt},
            )
            if resp.status_code in (401, 403):
                return self._error("Authentication failed. Check your DeepAI API key.")
            if resp.status_code >= 400:
                return self._error(f"DeepAI API error ({resp.status_code}): {resp.text}")
            data = resp.json()
        img_url = data.get("output_url", "")
        if not img_url:
            return self._error("DeepAI returned no image URL.")
        return self._ok(img_url, {"provider": "deepai"})

    # ------------------------------------------------------------------
    # Replicate — create prediction → poll (keep for FLUX / video models)
    # POST https://api.replicate.com/v1/predictions
    # ------------------------------------------------------------------
    async def _call_replicate(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        owner_model = self.variant_config.get("owner_model", "")
        if not owner_model:
            return self._error("Missing owner_model in variant_config.")
        input_data: dict = {"prompt": prompt}
        if neg:
            input_data["negative_prompt"] = neg
        if self.media_type == "video":
            input_data["duration"] = params.get("duration_sec", 5)

        async with self._http_client(timeout=180.0) as client:
            # Create prediction
            resp = await client.post(
                "https://api.replicate.com/v1/models/" + owner_model + "/predictions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "wait=60",
                },
                json={"input": input_data},
            )
            if resp.status_code == 401:
                return self._error("Authentication failed. Check your Replicate API key.")
            if resp.status_code >= 400:
                return self._error(f"Replicate API error ({resp.status_code}): {resp.text}")
            data = resp.json()

            # If already completed
            if data.get("status") == "succeeded":
                output = data.get("output")
                url = output if isinstance(output, str) else (output[0] if isinstance(output, list) and output else "")
                if url:
                    return self._ok(url, {"prediction_id": data.get("id"), "provider": "replicate"})

            # Poll if still processing
            poll_url = data.get("urls", {}).get("get", "")
            if not poll_url:
                return self._error("Replicate: no poll URL returned.")

            for _ in range(30):  # max ~5 min with 10s sleeps
                await asyncio.sleep(10)
                poll_resp = await client.get(
                    poll_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                poll_data = poll_resp.json()
                status = poll_data.get("status", "")
                if status == "succeeded":
                    output = poll_data.get("output")
                    url = output if isinstance(output, str) else (output[0] if isinstance(output, list) and output else "")
                    if url:
                        return self._ok(url, {"prediction_id": data.get("id"), "provider": "replicate"})
                    return self._error("Replicate succeeded but returned no output URL.")
                if status in ("failed", "canceled"):
                    return self._error(f"Replicate prediction {status}: {poll_data.get('error', 'unknown')}")

        return self._error("Replicate prediction timed out.")

    # ------------------------------------------------------------------
    # Fal.ai — queue-based, 100 credits/month free
    # POST https://queue.fal.run/{model_id}
    # ------------------------------------------------------------------
    async def _call_fal(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        fal_model = self.variant_config.get("fal_model", "")
        if not fal_model:
            return self._error("Missing fal_model in variant_config.")
        input_data: dict = {"prompt": prompt}
        if self.media_type == "video":
            input_data["duration"] = params.get("duration_sec", 5)

        submit_url = f"https://queue.fal.run/{fal_model}"
        async with self._http_client(timeout=180.0) as client:
            resp = await client.post(
                submit_url,
                headers={
                    "Authorization": f"Key {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=input_data,
            )
            if resp.status_code in (401, 403):
                return self._error("Authentication failed. Check your Fal.ai API key.")
            if resp.status_code >= 400:
                return self._error(f"Fal.ai API error ({resp.status_code}): {resp.text}")
            data = resp.json()

            request_id = data.get("request_id", "")
            if not request_id:
                return self._error("Fal.ai returned no request_id.")

            # Poll status
            status_url = f"{submit_url}/requests/{request_id}/status"
            result_url = f"{submit_url}/requests/{request_id}"

            for _ in range(36):  # max ~6 min
                await asyncio.sleep(10)
                status_resp = await client.get(
                    status_url,
                    headers={"Authorization": f"Key {self.api_key}"},
                )
                status_data = status_resp.json()
                if status_data.get("status") == "COMPLETED":
                    res_resp = await client.get(
                        result_url,
                        headers={"Authorization": f"Key {self.api_key}"},
                    )
                    res_data = res_resp.json()
                    # Images
                    if "images" in res_data and res_data["images"]:
                        return self._ok(
                            res_data["images"][0].get("url", ""),
                            {"provider": "fal", "request_id": request_id},
                        )
                    # Video
                    if "video" in res_data and res_data["video"]:
                        return self._ok(
                            res_data["video"].get("url", ""),
                            {"provider": "fal", "request_id": request_id},
                        )
                    return self._error("Fal.ai completed but returned no media.")
                if status_data.get("status") == "FAILED":
                    return self._error(f"Fal.ai generation failed: {status_data}")

        return self._error("Fal.ai generation timed out.")

    # ------------------------------------------------------------------
    # ElevenLabs — TTS/audio, 10K chars/month free
    # POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
    # ------------------------------------------------------------------
    async def _call_elevenlabs(
        self, prompt: str, neg: str | None, params: dict
    ) -> GenerationResult:
        voice_id = self.variant_config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Rachel default
        model_id = self.variant_config.get("model", "eleven_multilingual_v2")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        async with self._http_client(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": prompt,
                    "model_id": model_id,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
                },
            )
            if resp.status_code in (401, 403):
                return self._error("Authentication failed. Check your ElevenLabs API key.")
            if resp.status_code >= 400:
                return self._error(f"ElevenLabs API error ({resp.status_code}): {resp.text}")
            import base64
            b64 = base64.b64encode(resp.content).decode()
        return self._ok(
            f"data:audio/mpeg;base64,{b64}",
            {"voice_id": voice_id, "provider": "elevenlabs"},
        )

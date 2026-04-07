import google.generativeai as genai
import os
from dotenv import load_dotenv
from langfuse_helper import start_langfuse_observation


load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')


def _safe_usage_details(response):
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return None

    usage_map = {}
    for field in ("prompt_token_count", "candidates_token_count", "total_token_count"):
        value = getattr(usage, field, None)
        if value is not None:
            usage_map[field] = value
    return usage_map or None


# General query to Gemini
def query_gemini(prompt, temperature=0.4, top_p=0.2, return_metadata=False):
    generation_config = {"temperature": temperature, "top_p": top_p}
    request_metadata = {
        "provider": "google-generativeai",
        "safety_profile": "block_only_high",
    }

    with start_langfuse_observation(
        name="gemini-generate-content",
        as_type="generation",
        input_data=prompt,
        metadata=request_metadata,
        model="gemini-2.5-flash",
        model_parameters=generation_config,
    ) as generation:
        result = {
            "ok": False,
            "text": "",
            "model": "gemini-2.5-flash",
            "temperature": temperature,
            "top_p": top_p,
            "usage_details": None,
            "error": None,
        }

        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "block_only_high"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "block_only_high"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "block_only_high"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "block_only_high"},
                ]
            )
            result["text"] = response.text.strip()
            result["ok"] = True
            result["usage_details"] = _safe_usage_details(response)

            generation.update(
                output=result["text"],
                usage_details=result["usage_details"],
            )
        except Exception as e:
            result["error"] = str(e)
            result["text"] = f"❌ Error: {e}"
            generation.update(
                output=result["text"],
                level="ERROR",
                status_message=result["error"],
            )

        if return_metadata:
            return result

        return result["text"]
